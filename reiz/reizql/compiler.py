from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from functools import singledispatch

from reiz.db.schema import protected_name
from reiz.edgeql import *
from reiz.reizql.nodes import *
from reiz.reizql.parser import ReizQLSyntaxError

_COMPILER_WORKAROUND_FOR_TARGET = "_singleton"


@dataclass(unsafe_hash=True)
class CompilerState:
    match: str
    depth: int = 0
    pointer: Optional[str] = None
    parents: List[CompilerState] = field(default_factory=list)

    # Properties is a general way to store states (e.g on_enumeration)
    # through all the blocks (inherited through parent to all children)
    _properties: Dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_parent(cls, name, parent):
        return cls(
            name,
            depth=parent.depth + 1,
            parents=parent.parents + [parent],
            _properties=parent._properties,
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
    def temp_property(self, prop, value=1):
        _preserved_value = self.get_property(prop)
        try:
            self.set_property(prop, value)
            yield
        finally:
            self.set_property(prop, _preserved_value)

    def get_property(self, prop, default=None):
        return self._properties.get(prop, default)

    def set_property(self, prop, value=1):
        self._properties[prop] = value

    def compile(self, key, value):
        self.pointer = protected_name(key, prefix=False)
        return self.as_query(codegen(value, self))

    def as_query(self, query):
        if not isinstance(real_object(query), EdgeQLFilterType):
            query = EdgeQLFilter(generate_type_checked_key(self), query)
        return query

    def get_ordered_parents(self):
        parents = self.parents + [self]
        enumeration_start = self.get_property("enumeration_start")
        if not enumeration_start:
            return parents

        for index, parent in enumerate(parents):
            if parent.depth == enumeration_start:
                break
        else:
            raise ValueError(
                "Compiler check failed: no enumeration start block found!"
            )
        return parents[index:]


def generate_type_checked_key(state):
    base = None
    for parent in state.get_ordered_parents():
        if base is None:
            if state.get_property("enumeration_start") is not None:
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
        filters = merge_filters(filters, state.compile(key, value))

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


@codegen.register(ReizQLAttr)
def convert_attr(node, state):
    with state.temp_pointer(node.attr):
        return generate_type_checked_key(state)


@codegen.register(ReizQLLogicalOperation)
def convert_logical_operation(node, state):
    left = state.as_query(codegen(node.left, state))
    right = state.as_query(codegen(node.right, state))
    return EdgeQLFilterChain(left, right, codegen(node.operator, state))


@codegen.register(ReizQLLogicOperator)
def convert_logical_operator(node, state):
    if node is ReizQLLogicOperator.OR:
        return EdgeQLLogicOperator.OR


@codegen.register(ReizQLList)
def compile_sequence(node, state):
    length_verifier = EdgeQLFilter(
        EdgeQLCall("count", [generate_type_checked_key(state)]),
        len(node.items),
    )
    if len(node.items) == 0 or all(
        item is ReizQLIgnore for item in node.items
    ):
        return length_verifier

    array_ref = f"_items_{id(state)}_{state.depth}"

    # If we are in a nested list search (e.g: Call(args=[Call(args=[Name()])]))
    # we can't directly use `ORDER BY @index` since the EdgeDB can't quite infer
    # which @index are we talking about:
    if state.get_property("enumeration_start") is not None:
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

    filters = None
    for position, matcher in enumerate(node.items):
        if matcher is ReizQLIgnore:
            continue
        elif not isinstance(matcher, ReizQLMatch):
            # FIX-ME(high): support for logical operations + enums
            # Call(args = [Name('bruh') | Attribute(attr='moment')])
            raise ReizQLSyntaxError(
                "A list may only contain matchers, not atoms"
            )

        with state.temp_pointer(
            EdgeQLSubscript(EdgeQLName(array_ref), position)
        ), state.temp_property("enumeration_start", state.depth):
            filters = merge_filters(filters, codegen(matcher, state))

    assert filters is not None
    object_verifier = EdgeQLSelect(filters, with_block=scope)

    return merge_filters(length_verifier, object_verifier)


def compile_edgeql(node):
    return codegen(node, None)
