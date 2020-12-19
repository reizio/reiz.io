from __future__ import annotations

import uuid
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from functools import singledispatch
from types import SimpleNamespace
from typing import Any, ClassVar, Dict, List, Optional

from reiz.edgeql import *
from reiz.edgeql.schema import protected_name
from reiz.reizql.nodes import *
from reiz.reizql.parser import ReizQLSyntaxError

_COMPILER_WORKAROUND_FOR_TARGET = "_singleton"


@dataclass(unsafe_hash=True)
class CompilerState:
    match: str
    depth: int = 0
    pointer: Optional[str] = None
    parents: List[CompilerState] = field(default_factory=list, repr=False)

    # hand properties store data (like 'enumeration start depth')
    properties: Dict[str, Any] = field(default_factory=dict)
    definitions: Dict[str, CompilerState] = field(default_factory=dict)

    freeze = deepcopy

    @classmethod
    def from_parent(cls, name, parent):
        return cls(
            name,
            depth=parent.depth + 1,
            parents=parent.parents + [parent],
            properties=parent.properties,
            definitions=parent.definitions,
        )

    @property
    def is_root(self):
        return self.depth == 0

    @contextmanager
    def temp_pointer(self, pointer):
        _old_pointer = self.pointer
        try:
            self.pointer = pointer
            yield
        finally:
            self.pointer = _old_pointer

    @contextmanager
    def temp_flag(self, flag, value=True):
        _preserved_value = self.is_flag_set(flag)
        try:
            self.set_flag(flag, value)
            yield
        finally:
            self.set_flag(flag, _preserved_value)

    def set_flag(self, flag, value=True):
        self.properties[flag] = value

    def is_flag_set(self, flag, default=False):
        return self.properties.get(flag, default)

    # Just an implementation detail that they both share
    # the same internal structure.
    get_property = is_flag_set
    set_property = set_flag
    temp_property = temp_flag

    def compile(self, key, value):
        self.pointer = protected_name(key, prefix=False)
        if query := codegen(value, self):
            return self.as_query(query)

    def as_query(self, query):
        if not is_edgeql_filter_expr(real_object(query)):
            query = EdgeQLFilter(generate_type_checked_key(self), query)
        return query

    def get_ordered_parents(self):
        parents = self.parents + [self]
        enumeration_start = self.get_property("enumeration start depth")
        if enumeration_start is None:
            return parents

        for index, parent in enumerate(parents):
            if parent.depth == enumeration_start:
                break
        else:
            raise ValueError(
                "Compiler check failed: no enumeration start block found!"
            )
        return parents[index:]

    def as_unique_ref(self, prefix):
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    @property
    def can_raw_name_access(self):
        return self.is_flag_set("in for loop")


def generate_type_checked_key(state):
    base = None
    for parent in state.get_ordered_parents():
        if base is None:
            if state.can_raw_name_access:
                base = parent.pointer
            else:
                base = EdgeQLFilterKey(parent.pointer)
        else:
            base = EdgeQLAttribute(
                type_check(base, parent.match), parent.pointer
            )
    return base


def type_check(key, expected_type, inline=True):
    if inline:
        constructor = EdgeQLVerify
        operator = EdgeQLVerifyOperator.IS
    else:
        constructor = EdgeQLFilter
        operator = EdgeQLComparisonOperator.IDENTICAL
    return constructor(
        key, protected_name(expected_type, prefix=True), operator
    )


@singledispatch
def codegen(node, state):
    raise ValueError(f"Unknown node: {type(node).__name__}")


@codegen.register(ReizQLMatch)
def compile_matcher(node, state):
    if state is None:
        state = CompilerState(node.name)
    else:
        state = CompilerState.from_parent(node.name, state)

    filters = None
    for key, value in node.filters.items():
        if value is ReizQLIgnore:
            continue

        if right_filter := state.compile(key, value):
            filters = merge_filters(filters, right_filter)

    if state.is_root:
        return EdgeQLSelect(state.match, filters=filters)
    else:
        if filters is None:
            key = generate_type_checked_key(state.parents[-1])
            filters = type_check(key, state.match, inline=False)
        return filters


@codegen.register(ReizQLMatchEnum)
def convert_match_enum(node, state):
    return EdgeQLCast(protected_name(node.base, prefix=True), repr(node.name))


@codegen.register(ReizQLConstant)
def compile_constant(node, state):
    return EdgeQLPreparedQuery(str(node.value))


@codegen.register(ReizQLNot)
def compile_operator_flip(node, state):
    filters = state.as_query(codegen(node.value, state))
    return EdgeQLGroup(EdgeQLNot(EdgeQLGroup(filters)))


@codegen.register(ReizQLLogicalOperation)
def convert_logical_operation(node, state):
    left = state.as_query(codegen(node.left, state))
    right = state.as_query(codegen(node.right, state))
    return EdgeQLFilterChain(left, right, codegen(node.operator, state))


@codegen.register(ReizQLLogicOperator)
def convert_logical_operator(node, state):
    if node is ReizQLLogicOperator.OR:
        return EdgeQLLogicOperator.OR
    elif node is ReizQLLogicOperator.AND:
        return EdgeQLLogicOperator.AND


@codegen.register(ReizQLRef)
def compile_reference(node, state):
    if node.name in state.definitions:
        return generate_type_checked_key(state.definitions[node.name])
    else:
        state.definitions[node.name] = state.freeze()


@codegen.register(ReizQLList)
def compile_sequence(node, state):
    total_length = len(node.items)
    length_verifier = EdgeQLFilter(
        EdgeQLCall("count", [generate_type_checked_key(state)]),
        total_length,
    )
    if total_length == 0 or all(  # Empty list
        item in (ReizQLIgnore, ReizQLExpand) for item in node.items
    ):  # Length matching
        return length_verifier

    if total := node.items.count(ReizQLExpand):
        if total > 1:
            raise ReizQLSyntaxError(
                "Can't use multiple expansion macros in one sequence"
            )
        length_verifier.value -= total
        length_verifier.operator = EdgeQLComparisonOperator.GTE

    array_ref = state.as_unique_ref("_sequence")

    # If we are in a nested list search (e.g: Call(args=[Call(args=[Name()])]))
    # we can't directly use `ORDER BY @index` since the EdgeDB can't quite infer
    # which @index are we talking about.
    if state.is_flag_set("in for loop"):
        original_matcher = generate_type_checked_key(state.parents[-1])
        type_checked_sequence = EdgeQLAttribute(
            type_check(
                EdgeQLName(_COMPILER_WORKAROUND_FOR_TARGET), state.match
            ),
            state.pointer,
        )
        unpacked_list = EdgeQLFor(
            _COMPILER_WORKAROUND_FOR_TARGET,
            EdgeQLSet([original_matcher]),
            EdgeQLSelect(
                type_checked_sequence,
                ordered=EdgeQLProperty("index"),
            ),
        )
    else:
        unpacked_list = EdgeQLSelect(
            generate_type_checked_key(state), ordered=EdgeQLProperty("index")
        )

    unpacked_array = EdgeQLCall("array_agg", [unpacked_list])
    scope = EdgeQLWithBlock({array_ref: unpacked_array})

    expansion_seen = False
    with state.temp_flag("in for loop"), state.temp_property(
        "enumeration start depth", state.depth
    ):
        filters = None
        for position, matcher in enumerate(node.items):
            if matcher is ReizQLIgnore:
                continue
            elif matcher is ReizQLExpand:
                expansion_seen = True
                continue
            elif not isinstance(matcher, ReizQLMatch):
                # FIX-ME(high): support for logical operations + enums
                # Call(args = [Name('bruh') | Attribute(attr='moment')])
                raise ReizQLSyntaxError(
                    "A list may only contain matchers, not atoms"
                )

            if expansion_seen:
                position = -(total_length - position)

            with state.temp_pointer(
                EdgeQLSubscript(EdgeQLName(array_ref), position)
            ):
                filters = merge_filters(filters, codegen(matcher, state))

        assert filters is not None
        object_verifier = EdgeQLSelect(filters, with_block=scope)

    return merge_filters(length_verifier, object_verifier)


@dataclass
class Signature:
    name: str
    func: Callable
    params: List[str] = field(default_factory=set)
    defaults: Dict[str, Any] = field(default_factory=list)

    _FUNCTIONS: ClassVar[Dict[str, Callable]] = {}

    @classmethod
    def register(cls, name, *args, **kwargs):
        def wrapper(func):
            cls._FUNCTIONS[name] = cls(name, func, *args, **kwargs)
            return func

        return wrapper

    def codegen(self, node, state):
        return self.func(node, state, self.bind(node))

    def bind(self, node):
        bound_args = {}
        params = self.params.copy()
        for argument in node.args:
            if len(params) == 0:
                raise ReizQLSyntaxError(
                    f"{self.name!r} got too many positional arguments"
                )
            bound_args[params.pop(0)] = argument

        for keyword, value in node.keywords.items():
            if keyword not in params:
                raise ReizQLSyntaxError(
                    f"{self.name!r} got an unexpected keyword argument {keyword!r}"
                )
            params.remove(keyword)
            bound_args[keyword] = value

        for param in params.copy():
            if param not in self.defaults:
                raise ReizQLSyntaxError(
                    f"{self.name!r} requires {param!r} argument"
                )
            bound_args[param] = self.defaults[param]

        return SimpleNamespace(**bound_args)


def builtin_type_error(func, expected):
    raise ReizQLSyntaxError(f"{func!r} expects {expected}")


@Signature.register("ALL", ["value"])
@Signature.register("ANY", ["value"])
def convert_all_any(node, state, arguments):
    query = construct(codegen(arguments.value, state))
    return as_edgeql_filter_expr(EdgeQLCall(node.name.lower(), [query]))


@Signature.register("LEN", ["min", "max"], {"min": None, "max": None})
def convert_length(node, state, arguments):
    if arguments.min is None and arguments.max is None:
        raise ReizQLSyntaxError("'LEN' requires at least 1 argument")

    count = EdgeQLCall("count", [generate_type_checked_key(state)])
    filters = None
    for value, operator in [
        (arguments.min, EdgeQLComparisonOperator.GTE),
        (arguments.max, EdgeQLComparisonOperator.LTE),
    ]:
        if value is None:
            continue

        if not (isinstance(value, ReizQLConstant) and value.value.isdigit()):
            builtin_type_error("LEN", "integers")

        try:
            value = str(int(value.value))
        except ValueError:
            builtin_type_error("LEN", "integers")

        filters = merge_filters(
            filters, EdgeQLFilter(count, EdgeQLPreparedQuery(value), operator)
        )

    assert filters is not None
    return filters


@Signature.register("ATTR", ["attr"])
def convert_attr(node, state, arguments):
    if not isinstance(arguments.attr, ReizQLRef):
        raise ReizQLSyntaxError(
            f"'ATTR' expected a reference, got {type(arguments.attr).__name__}"
        )

    with state.temp_pointer(arguments.attr.name):
        return generate_type_checked_key(state)


@codegen.register(ReizQLBuiltin)
def convert_call(node, state):
    signature = Signature._FUNCTIONS.get(node.name)
    if signature is None:
        raise ValueError("Compiler check failed: unknown builtin function!")

    return signature.codegen(node, state)


@codegen.register(type(ReizQLNone))
def convert_none(node, state):
    return EdgeQLNot(
        as_edgeql_filter_expr(EdgeQLExists(generate_type_checked_key(state)))
    )


def compile_edgeql(node):
    return codegen(node, None)
