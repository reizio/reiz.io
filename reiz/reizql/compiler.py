from __future__ import annotations

import uuid
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from functools import singledispatch
from types import SimpleNamespace
from typing import Any, ClassVar, Counter, Dict, List, Optional

from reiz.ir import IR
from reiz.reizql.field_db import FIELD_DB
from reiz.reizql.nodes import *
from reiz.reizql.parser import ReizQLSyntaxError
from reiz.serialization.transformers import ast

_COMPILER_WORKAROUND_FOR_TARGET = "_singleton"


@dataclass
class Scope:
    # - 3 kinds of scopes:
    #   - $CUR   (current scope)
    #   - $PAR^n (nth parent's scope)
    #   - $TOP   (initial parent's scope)
    #
    # - Each list matcher creates their own scope. Until a list matcher is seen,
    #   everything belongs to the $CUR.
    #
    # - The parent can't access to any of their children's scope
    #
    # - $CUR can reach up to $TOP, in a linear way. So if $CUR's parent ($PAR^1)
    #   has 2 children (one being $CUR), the $CUR can not their sibling's scope but
    #   can access any symbol defined in between $PAR^n..$TOP.
    #
    # Examples:
    # FunctionDef(
    #       ~name,                              <= name.1
    #       decorator_list = [
    #           Name(~foo),                     <= foo.1
    #           Name(~foo),                     <= foo.1
    #       ],
    #       body = [
    #           Name(~foo),                     <= foo.2
    #           Attribute(Name(~foo)),          <= foo.2
    #           Return(Call(Name(~name)))       <= name.1
    #       ]
    #  )

    parents: List[Scope] = field(default_factory=list)
    definitions: Dict[str, CompilerState] = field(default_factory=dict)
    reference_counts: Counter[str] = field(default_factory=Counter)

    @classmethod
    def from_parent(cls, parent):
        return cls(parents=parent.parents + [parent])

    def lookup(self, name):
        for scope in reversed(self.parents + [self]):
            if state := scope.definitions.get(name):
                scope.reference(name)
                return state
        else:
            return None

    def reference(self, name):
        self.reference_counts[name] += 1

    def define(self, name, state):
        self.definitions[name] = state.freeze()

    def exit(self):
        for definition in self.definitions:
            if self.reference_counts[definition] < 1:
                raise ReizQLSyntaxError(f"Unused reference: {definition!r}")

        if len(self.parents) >= 1:
            return self.parents[-1]


@dataclass(unsafe_hash=True)
class CompilerState:
    match: str
    depth: int = 0

    scope: Scope = field(default_factory=Scope)
    properties: Dict[str, Any] = field(default_factory=dict)
    parents: List[CompilerState] = field(default_factory=list, repr=False)

    field: Optional[str] = None

    freeze = deepcopy

    @classmethod
    def from_parent(cls, name, parent):
        return cls(
            name,
            depth=parent.depth + 1,
            scope=parent.scope,
            parents=parent.parents + [parent],
            properties=parent.properties,
        )

    @property
    def is_root(self):
        return self.depth == 0

    @contextmanager
    def new_scope(self):
        try:
            self.scope = Scope.from_parent(self.scope)
            yield
        finally:
            self.scope = self.scope.exit()

    @contextmanager
    def temp_pointer(self, pointer):
        _old_pointer = self.field
        try:
            self.field = pointer
            yield
        finally:
            self.field = _old_pointer

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

    def compute_path(self):
        base = None
        for parent in self.get_ordered_parents():
            if base is None:
                if self.can_raw_name_access:
                    base = parent.pointer
                else:
                    base = IR.attribute(None, parent.pointer)
            else:
                base = IR.attribute(
                    IR.typed(base, parent.match), parent.pointer
                )
        return base

    def compile(self, key, value):
        with self.temp_pointer(key):
            return self.codegen(value)

    def codegen(self, node):
        return codegen(node, self)

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
        return IR.name(f"{prefix}_{uuid.uuid4().hex[:8]}")

    @property
    def can_raw_name_access(self):
        return self.is_flag_set("in for loop")

    @property
    def pointer(self):
        return IR.wrap(self.field, with_prefix=False)

    @property
    def field_info(self):
        return FIELD_DB[self.match][self.field]


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
            filters = IR.combine_filters(filters, right_filter)

    if state.is_root:
        state.scope.exit()
        return IR.select(state.match, filters=filters)

    if filters is None:
        filters = IR.filter(
            state.parents[-1].compute_path(), IR.wrap(state.match), "IS"
        )

    return filters


@codegen.register(ReizQLMatchEnum)
def convert_match_enum(node, state):
    expr = IR.enum_member(node.base, node.name)
    return IR.filter(state.compue_path(), expr, "=")


@codegen.register(ReizQLConstant)
def compile_constant(node, state):
    expr = IR.literal(node.value)
    return IR.filter(state.compute_path(), expr, "=")


@codegen.register(ReizQLMatchString)
def compile_match_string(node, state):
    expr = IR.literal(node.value)
    return IR.filter(state.compute_path(), expr, "LIKE")


@codegen.register(ReizQLNot)
def compile_operator_flip(node, state):
    return IR.negate(state.codegen(node.value))


@codegen.register(ReizQLLogicalOperation)
def convert_logical_operation(node, state):
    return IR.filter(
        state.codegen(node.left),
        state.codegen(node.right),
        state.codegen(node.operator),
    )


@codegen.register(ReizQLLogicOperator)
def convert_logical_operator(node, state):
    if node is ReizQLLogicOperator.OR:
        return IR.as_operator("OR")
    elif node is ReizQLLogicOperator.AND:
        return IR.as_operator("AND")


@codegen.register(ReizQLRef)
def compile_reference(node, state):
    obtained_type = state.field_info.type

    if pointer := state.scope.lookup(node.name):
        expected_type = pointer.field_info.type
        if expected_type is not obtained_type:
            raise ReizQLSyntaxError(
                f"{node.name} expects {expected_type.__name__!r} got {obtained_type.__name__!r}"
            )

        left = state.compute_path()
        right = pointer.compute_path()
        if issubclass(expected_type, ast.expr):
            left = IR.attribute(left, "tag")
            right = IR.attribute(right, "tag")
        return IR.filter(left, right, "=")
    else:
        if not issubclass(obtained_type, (str, int, ast.expr)):
            raise ReizQLSyntaxError(
                f"Can't reference to {obtained_type.__name__!r} type"
            )
        state.scope.define(node.name, state)


@codegen.register(ReizQLList)
def compile_sequence(node, state):
    total_length = len(node.items)
    length_verifier = IR.filter(
        IR.call("count", [state.compute_path()]), total_length, "="
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
        length_verifier = IR.filter(
            IR.call("count", [state.compute_path()]), total_length - 1, ">="
        )

    array_ref = state.as_unique_ref("_sequence")

    # If we are in a nested list search (e.g: Call(args=[Call(args=[Name()])]))
    # we can't directly use `ORDER BY @index` since the EdgeDB can't quite infer
    # which @index are we talking about.

    # a part of this section should go under the IRBuilder
    if state.is_flag_set("in for loop"):
        type_checked_sequence = IR.attribute(
            IR.typed(IR.name(_COMPILER_WORKAROUND_FOR_TARGET), state.match),
            state.pointer,
        )
        unpacked_list = IR.loop(
            IR.name(_COMPILER_WORKAROUND_FOR_TARGET),
            state.parents[-1].compute_path(),
            IR.select(type_checked_sequence, order=IR.property("index")),
        )
    else:
        unpacked_list = IR.select(
            state.compute_path(), order=IR.property("index")
        )

    unpacked_array = IR.call("array_agg", [unpacked_list])
    scope = IR.namespace({array_ref: unpacked_array})

    expansion_seen = False
    with state.temp_flag("in for loop"), state.temp_property(
        "enumeration start depth", state.depth
    ), state.new_scope():
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

            with state.temp_pointer(IR.subscript(array_ref, position)):
                filters = IR.combine_filters(filters, state.codegen(matcher))

        assert filters is not None
        object_verifier = IR.add_namespace(scope, IR.select(filters))

    return IR.combine_filters(length_verifier, object_verifier)


@codegen.register(type(ReizQLNone))
def convert_none(node, state):
    return IR.negate(IR.exists(state.compute_path()))


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


@Signature.register("I", ["match_str"])
def convert_intensive(node, state, arguments):
    match_str = arguments.match_str
    if not isinstance(arguments.match_str, ReizQLMatchString):
        raise ReizQLSyntaxError(f"I only accepts match strings")

    return IR.filter(
        state.compute_path(), IR.literal(match_str.value), "ILIKE"
    )


@Signature.register("ALL", ["value"])
@Signature.register("ANY", ["value"])
def convert_all_any(node, state, arguments):
    return IR.call(node.name.lower(), [state.codegen(arguments.value)])


@Signature.register("LEN", ["min", "max"], {"min": None, "max": None})
def convert_length(node, state, arguments):
    if arguments.min is None and arguments.max is None:
        raise ReizQLSyntaxError("'LEN' requires at least 1 argument")

    count = IR.call("count", [state.compute_path()])
    filters = None
    for value, operator in [
        (arguments.min, IR.as_operator(">=")),
        (arguments.max, IR.as_operator("<=")),
    ]:
        if value is None:
            continue

        if not (isinstance(value, ReizQLConstant) and value.value.isdigit()):
            builtin_type_error("LEN", "integers")

        try:
            value = str(int(value.value))
        except ValueError:
            builtin_type_error("LEN", "integers")

        filters = IR.combine_filters(
            filters, IR.filter(count, IR.literal(value), operator)
        )

    assert filters is not None
    return filters


@codegen.register(ReizQLBuiltin)
def convert_call(node, state):
    signature = Signature._FUNCTIONS.get(node.name)
    if signature is None:
        raise ValueError("Compiler check failed: unknown builtin function!")

    return signature.codegen(node, state)


def compile_to_ir(node):
    return codegen(node, None)
