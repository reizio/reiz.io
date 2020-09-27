import dataclasses
import functools

from reiz.edgeql.base import *
from reiz.edgeql.expr import *
from reiz.edgeql.stmt import *


@functools.singledispatch
def optimize(node):
    replacements = {}
    for field, value in dataclasses.asdict(node).items():
        if (
            isinstance(value, EdgeQLObject)
            and (replacement := optimize(node)) is not value
        ):
            replacement[field] = replacement

    if replacements:
        return node.replace(**replacements)
    else:
        return node
