from reiz.edgeql.base import *
from reiz.edgeql.expr import *
from reiz.edgeql.optimizer import optimize_edgeql
from reiz.edgeql.stmt import *


def as_edgeql(tree):
    tree = optimize_edgeql(tree)
    return construct(tree, top_level=True)
