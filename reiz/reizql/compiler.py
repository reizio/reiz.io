import functools
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional

from reiz.db.schema import protected_name
from reiz.edgeql import *
from reiz.reizql.nodes import (
    ReizQLBuiltin,
    ReizQLConstant,
    ReizQLList,
    ReizQLLogicalOperation,
    ReizQLLogicOperator,
    ReizQLMatch,
    ReizQLMatchEnum,
    ReizQLNot,
    ReizQLSet,
)
from reiz.reizql.parser import ReizQLSyntaxError

__DEFAULT_FOR_TARGET = "__KEY"


@dataclass(unsafe_hash=True)
class SelectState:
    name: str
    pointer: Optional[str] = None
    assignments: Dict[str, EdgeQLObject] = field(default_factory=dict)


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

    params = {"filters": query}
    if state.assignments:
        params["with_block"] = EdgeQLWithBlock(state.assignments)
    return EdgeQLSelect(state.name, **params)


@compile_edgeql.register(ReizQLMatchEnum)
def convert_match_enum(node, state):
    return EdgeQLCast(protected_name(node.base, prefix=True), repr(node.name))


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


def generate_typechecked_query(filters, base):
    base_query = None
    for query, operator in unpack_filters(filters):
        assert isinstance(query.key, EdgeQLFilterKey)
        key = EdgeQLAttribute(base, query.key.name)

        current_query = None
        if isinstance(query.value, EdgeQLPreparedQuery):
            current_query = replace(query, key=key)
        elif isinstance(query.value, EdgeQLSelect):
            model = protected_name(query.value.name, prefix=True)
            verifier = EdgeQLVerify(key, EdgeQLVerifyOperator.IS, model)
            if query.value.filters:
                current_query = generate_typechecked_query(
                    query.value.filters, verifier
                )
            else:
                current_query = EdgeQLFilter(
                    EdgeQLAttribute(base, query.key.name),
                    model,
                    EdgeQLComparisonOperator.IDENTICAL,
                )
        else:
            raise ReizQLSyntaxError("Unsupported syntax")

        base_query = merge_filters(base_query, current_query, operator)

    return base_query


def convert_any_all(node, state):
    if len(node.args) != 1 or node.keywords:
        raise ReizQLSyntaxError(
            f"Parameter mismatch for built-in function: {node.name!r}"
        )

    check = compile_edgeql(*node.args, state)
    negated = isinstance(check, EdgeQLNot)
    if negated:
        check = check.value

    if isinstance(check, EdgeQLSelect) and check.filters:
        operator = EdgeQLComparisonOperator.EQUALS
    elif isinstance(check, EdgeQLSelect) and not check.filters:
        check = protected_name(check.name, prefix=True)
        operator = EdgeQLComparisonOperator.IDENTICAL
    else:
        raise ReizQLSyntaxError(
            "Unsupported operation passed into built-in function"
        )

    if negated:
        operator = operator.negate()

    return EdgeQLFilter(
        EdgeQLCall(
            node.name.lower(),
            [EdgeQLFilter(EdgeQLFilterKey(state.pointer), check, operator)],
        ),
        EdgeQLPreparedQuery("True"),
    )


@compile_edgeql.register(ReizQLBuiltin)
def convert_builtin(node, state):
    if node.name in ("ANY", "ALL"):
        return convert_any_all(node, state)


@compile_edgeql.register(ReizQLNot)
def convert_negatation(node, state):
    return EdgeQLNot(compile_edgeql(node.value, state))


@compile_edgeql.register(ReizQLList)
def convert_list(node, state):
    object_verifier = EdgeQLFilter(
        EdgeQLCall("count", [EdgeQLFilterKey(state.pointer)]), len(node.items)
    )
    if len(node.items) == 0:
        return object_verifier

    assignments = {}
    select_filters = None
    for index, item in enumerate(node.items):
        assert isinstance(item, ReizQLMatch)
        selection = EdgeQLSelect(
            EdgeQLFilterKey(state.pointer),
            ordered=EdgeQLProperty("index"),
            offset=index,
            limit=1,
        )
        filters = convert_match(item).filters

        # If there are no value queries, only type-check
        if filters is None:
            select_filters = merge_filters(
                select_filters,
                EdgeQLFilter(
                    selection,
                    protected_name(item.name, prefix=True),
                    EdgeQLComparisonOperator.IDENTICAL,
                ),
            )
        else:
            assignments[f"__item_{index}"] = EdgeQLVerify(
                selection,
                EdgeQLVerifyOperator.IS,
                protected_name(item.name, prefix=True),
            )
            select_filters = merge_filters(
                select_filters,
                generate_typechecked_query(filters, f"__item_{index}"),
            )

    if assignments:
        with_block = EdgeQLWithBlock(assignments)
    else:
        with_block = None

    value_verifier = EdgeQLSelect(
        select_filters,
        with_block=with_block,
    )
    return EdgeQLFilterChain(
        object_verifier,
        value_verifier,
    )


@compile_edgeql.register(ReizQLConstant)
def convert_atomic(node, state):
    if (
        state.name == "Dict"
        and state.pointer == "keys"
        and str(node.value) == repr(str(None))
    ):
        return compile_edgeql(ReizQLMatch("Sentinel"))
    else:
        return EdgeQLPreparedQuery(str(node.value))
