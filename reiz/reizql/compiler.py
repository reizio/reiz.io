import functools

from reiz.edgeql import *
from reiz.reizql.nodes import (
    ReizQLConstant,
    ReizQLLogicalOperation,
    ReizQLLogicOperator,
    ReizQLMatch,
    ReizQLMatchEnum,
    ReizQLSet,
)


@functools.singledispatch
def compile_edgeql(obj, field=None):
    raise ReizQLSyntaxError(f"Unexpected query object: {obj!r}")


@compile_edgeql.register(ReizQLMatch)
def convert_match(node, field=None):
    query = None
    for key, value in node.filters.items():
        field = protected_name(key, prefix=False)
        conversion = compile_edgeql(value, field)
        if not isinstance(conversion, EdgeQLFilterType):
            conversion = EdgeQLFilter(EdgeQLFilterKey(field), conversion)

        if query is None:
            query = conversion
        else:
            query = EdgeQLFilterChain(query, conversion)

    return EdgeQLSelect(node.name, filters=query)


@compile_edgeql.register(ReizQLMatchEnum)
def convert_match_enum(node, field=None):
    return EdgeQLCast(node.base, repr(node.name))


@compile_edgeql.register(ReizQLLogicalOperation)
def convert_logical_operation(node, field):
    left = compile_edgeql(node.left, field)
    right = compile_edgeql(node.right, field)

    if not isinstance(left, EdgeQLFilterChain):
        left = EdgeQLFilter(EdgeQLFilterKey(field), left)
    if not isinstance(right, EdgeQLFilterChain):
        right = EdgeQLFilter(EdgeQLFilterKey(field), right)
    return EdgeQLFilterChain(left, right, compile_edgeql(node.operator, field))


@compile_edgeql.register(ReizQLLogicOperator)
def convert_logical_operator(node, field=None):
    if node is ReizQLLogicOperator.OR:
        return EdgeQLLogicOperator.OR


@compile_edgeql.register(ReizQLSet)
def convert_set(node, field):
    return EdgeQLSet([compile_edgeql(item, field) for item in node.items])


@compile_edgeql.register(ReizQLConstant)
def convert_atomic(node, field=None):
    return EdgeQLPreparedQuery(node.value)
