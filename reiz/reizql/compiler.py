import functools
from dataclasses import dataclass, field
from typing import Dict, Optional

from reiz.db.schema import protected_name
from reiz.edgeql import (
    EdgeQLAttribute,
    EdgeQLCall,
    EdgeQLCast,
    EdgeQLComparisonOperator,
    EdgeQLFilter,
    EdgeQLFilterChain,
    EdgeQLFilterKey,
    EdgeQLFilterType,
    EdgeQLFor,
    EdgeQLLogicOperator,
    EdgeQLName,
    EdgeQLNot,
    EdgeQLObject,
    EdgeQLPreparedQuery,
    EdgeQLProperty,
    EdgeQLSelect,
    EdgeQLSet,
    EdgeQLVerify,
    EdgeQLVerifyOperator,
    EdgeQLWithBlock,
    merge_filters,
    unpack_filters,
)
from reiz.reizql.nodes import (
    ReizQLBuiltin,
    ReizQLConstant,
    ReizQLIgnore,
    ReizQLList,
    ReizQLLogicalOperation,
    ReizQLLogicOperator,
    ReizQLMatch,
    ReizQLMatchEnum,
    ReizQLNot,
    ReizQLSet,
)
from reiz.reizql.parser import ReizQLSyntaxError
from reiz.utilities import logger

__DEFAULT_FOR_TARGET = "__KEY"


@dataclass(unsafe_hash=True)
class SelectState:
    name: str
    depth: int = 0
    pointer: Optional[str] = None
    assignments: Dict[str, EdgeQLObject] = field(default_factory=dict)


@functools.singledispatch
def compile_edgeql(obj, state):
    raise ReizQLSyntaxError(f"Unexpected query object: {obj!r}")


@compile_edgeql.register(ReizQLMatch)
def convert_match(node, state=None):
    query = None
    state = SelectState(node.name)
    for key, value in node.filters.items():
        state.pointer = protected_name(key, prefix=False)
        if value is ReizQLIgnore:
            continue

        conversion = compile_edgeql(value, state)

        if not isinstance(conversion, EdgeQLFilterType):
            conversion = EdgeQLFilter(
                EdgeQLFilterKey(state.pointer), conversion
            )

        query = merge_filters(query, conversion)

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


def generate_typechecked_query_item(query, base):
    rec_list = False
    if isinstance(query.key, EdgeQLCall) and isinstance(
        query.key.args[0], EdgeQLFilterKey
    ):
        name = query.key.args[0].name
        rec_list = True
    elif isinstance(query.key, EdgeQLFilterKey):
        name = query.key.name
    else:
        raise ReizQLSyntaxError(
            f"Unknown matcher type for list expression: {type(query).__name__}"
        )

    key = EdgeQLAttribute(base, name)

    if rec_list:
        query.key.args[0] = key
        return query
    elif isinstance(query.value, EdgeQLPreparedQuery):
        query.key = key
        return query
    elif isinstance(query.value, EdgeQLSelect):
        model = protected_name(query.value.name, prefix=True)
        verifier = EdgeQLVerify(key, EdgeQLVerifyOperator.IS, model)
        if query.value.filters:
            return generate_typechecked_query(query.value.filters, verifier)
        else:
            return EdgeQLFilter(
                EdgeQLAttribute(base, query.key.name),
                model,
                EdgeQLComparisonOperator.IDENTICAL,
            )
    else:
        raise ReizQLSyntaxError("Unsupported syntax")


def generate_typechecked_selection(selection, base):
    def replace_select(node):
        assert isinstance(node.name, EdgeQLFilterKey)
        node.name = EdgeQLAttribute(f"_tmp_singleton", node.name.name)
        return EdgeQLFor("_tmp_singleton", EdgeQLSet([base]), node)

    def replace_node(node):
        if isinstance(node, EdgeQLVerify):
            node.query = replace_select(node.query)
        elif isinstance(node, EdgeQLSelect):
            return replace_select(node)
        else:
            logger.warning("Unhandled type: %s", type(node).__name__)
        return node

    if selection.with_block:
        namespace = selection.with_block.assignments
        for key, node in namespace.copy().items():
            namespace[key] = replace_node(node)

    return selection


def generate_typechecked_query(filters, base):
    base_query = None
    for query, operator in unpack_filters(filters):
        if isinstance(query, EdgeQLSelect):
            current_query = generate_typechecked_selection(query, base)
        elif isinstance(query, EdgeQLFilter):
            current_query = generate_typechecked_query_item(query, base)
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
    if len(node.items) == 0 or all(
        item is ReizQLIgnore for item in node.items
    ):
        return object_verifier

    assignments = {}
    select_filters = None
    for index, item in enumerate(node.items):
        if item is ReizQLIgnore:
            continue
        elif not isinstance(item, ReizQLMatch):
            raise ReizQLSyntaxError(
                "A list may only contain matchers, not atoms"
            )

        selection = EdgeQLSelect(
            EdgeQLFilterKey(state.pointer),
            ordered=EdgeQLProperty("index"),
            offset=index,
            limit=1,
        )
        filters = convert_match(item).filters

        # If there are no value queries, only type-check
        name = f"__item_{index}_{id(filters)}"
        if filters is None:
            assignments[name] = selection
            select_filters = merge_filters(
                select_filters,
                EdgeQLFilter(
                    EdgeQLName(name),
                    protected_name(item.name, prefix=True),
                    EdgeQLComparisonOperator.IDENTICAL,
                ),
            )
        else:
            assignments[name] = EdgeQLVerify(
                selection,
                EdgeQLVerifyOperator.IS,
                protected_name(item.name, prefix=True),
            )
            select_filters = merge_filters(
                select_filters,
                generate_typechecked_query(filters, name),
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
