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
