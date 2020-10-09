import dataclasses
import functools
from dataclasses import dataclass
from typing import List

from reiz.edgeql.base import *
from reiz.edgeql.expr import *
from reiz.edgeql.stmt import *


@dataclass(unsafe_hash=True)
class OptimizerState:
    context: List[EdgeQLObject] = field(default_factory=list)


def visit(node, state):
    if isinstance(node, EdgeQLObject):
        node = generic_visit(node, state)
        return optimize_edgeql(node, state)
    else:
        return node


def generic_visit(node, state):
    if state:
        state.context.append(node)
    else:
        state = OptimizerState([node])

    replacements = {}
    for field, value in vars(node).items():
        if isinstance(value, EdgeQLObject):
            if value is (replacement := visit(value, state)):
                continue
        elif isinstance(value, list):
            if value == (
                replacement := [visit(item, state) for item in value]
            ):
                continue
        else:
            continue

        replacements[field] = replacement
    state.context.pop()

    if replacements:
        return dataclasses.replace(node, **replacements)
    else:
        return node


@functools.singledispatch
def optimize_edgeql(node, state=None):
    return generic_visit(node, state)


@optimize_edgeql.register(EdgeQLFilter)
def optimize_filter(node, state):
    op = node.operator

    if isinstance(node.value, EdgeQLNot):
        node = dataclasses.replace(
            node, operator=op.negate(), value=node.value.value
        )

    if isinstance(node.value, EdgeQLSet):
        eql_set = node.value

        positives, negatives = [], []
        for item in eql_set.items:
            if isinstance(item, EdgeQLNot):
                negatives.append(item.value)
            else:
                positives.append(item)

        if negatives and positives:
            # Since the type is now changed, this object
            # can no longer participate optimizations, so
            # return early.
            return EdgeQLFilterChain(
                dataclasses.replace(node, value=EdgeQLSet(positives)),
                dataclasses.replace(
                    node, value=EdgeQLSet(negatives), op=op.negate()
                ),
            )
        elif negatives:
            node = dataclasses.replace(
                node, operator=op.negate(), value=EdgeQLSet(negatives)
            )

    return node


@optimize_edgeql.register(EdgeQLSelect)
def optimize_select(node, state=None):
    node = generic_visit(node, state)

    filters = None
    for query, operator in unpack_filters(node.filters):
        if (
            isinstance(query, EdgeQLFilter)
            and isinstance(query.key, EdgeQLFilterKey)
            and isinstance(query.value, EdgeQLSelect)
            and query.value.is_bare()
        ):
            query = dataclasses.replace(
                query,
                value=protected_name(query.value.name, prefix=True),
                operator=EdgeQLComparisonOperator.IDENTICAL,
            )
        filters = merge_filters(filters, query, operator)
    node = dataclasses.replace(node, filters=filters)
    return node
