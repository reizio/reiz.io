import functools
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from reiz.edgeql import *
from reiz.reizql.nodes import (
    ReizQLConstant,
    ReizQLList,
    ReizQLLogicalOperation,
    ReizQLLogicOperator,
    ReizQLMatch,
    ReizQLMatchEnum,
    ReizQLSet,
)


@dataclass(unsafe_hash=True)
class SelectState:
    name: str
    pointer: Optional[str] = None
    assignments: Dict[str, EdgeQLExpression] = field(default_factory=dict)


@functools.singledispatch
def compile_edgeql(obj, state):
    raise ReizQLSyntaxError(f"Unexpected query object: {obj!r}")


@compile_edgeql.register(ReizQLMatch)
def convert_match(node, state=None):
    query = None
    state = SelectState(node.name, None)
    for key, value in node.filters.items():
        state.pointer = protected_name(key, prefix=False)
        conversion = compile_edgeql(value, state)
        if not isinstance(conversion, EdgeQLFilterType):
            conversion = EdgeQLFilter(
                EdgeQLFilterKey(state.pointer), conversion
            )

        if query is None:
            query = conversion
        else:
            query = EdgeQLFilterChain(query, conversion)

    extras = {"filters": query}
    if state.assignments:
        extras["with_block"] = EdgeQLWithBlock(state.assignments)

    return EdgeQLSelect(state.name, **extras)


@compile_edgeql.register(ReizQLMatchEnum)
def convert_match_enum(node, state):
    return EdgeQLCast(node.base, repr(node.name))


@compile_edgeql.register(ReizQLLogicalOperation)
def convert_logical_operation(node, state):
    left = compile_edgeql(node.left, state)
    right = compile_edgeql(node.right, state)

    if not isinstance(left, EdgeQLFilterChain):
        left = EdgeQLFilter(EdgeQLFilterKey(state.pointer), left)
    if not isinstance(right, EdgeQLFilterChain):
        right = EdgeQLFilter(EdgeQLFilterKey(state.pointer), right)
    return EdgeQLFilterChain(left, right, compile_edgeql(node.operator, state))


@compile_edgeql.register(ReizQLLogicOperator)
def convert_logical_operator(node, state):
    if node is ReizQLLogicOperator.OR:
        return EdgeQLLogicOperator.OR


@compile_edgeql.register(ReizQLSet)
def convert_set(node, state):
    return EdgeQLSet([compile_edgeql(item, state) for item in node.items])


# FIX-ME(high): Unfortunately, due to the way we are doing, this action
# takes so long to compute, so we need to optimize this (awaiting response)
@compile_edgeql.register(ReizQLList)
def convert_list(node, state):
    if state.assignments.get("MOD_REF") is None:
        state.assignments["MOD_REF"] = (
            protected_name(state.name, prefix=True) + "._module"
        )

    filters = EdgeQLFilter(
        EdgeQLCall("count", [EdgeQLFilterKey(state.pointer)]), len(node.items)
    )
    if node.items:
        left_arr = EdgeQLCall(
            "array_agg",
            [EdgeQLCall("enumerate", [EdgeQLFilterKey(state.pointer)])],
        )
        right_arr_items = []
        for index, item in enumerate(node.items):
            selection = convert_match(item)
            module_filter = make_filter(_module="MOD_REF")
            if selection.filters:
                selection.filters = EdgeQLFilterChain(
                    module_filter, selection.filters
                )
            else:
                selection.filters = module_filter
            right_arr_items.append(EdgeQLTuple([index, selection]))
        right_arr = EdgeQLArray(right_arr_items)
        filters = EdgeQLFilterChain(filters, EdgeQLFilter(left_arr, right_arr))
    return filters


@compile_edgeql.register(ReizQLConstant)
def convert_atomic(node, state):
    return EdgeQLPreparedQuery(node.value)
