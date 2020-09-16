"""
ReizQL - Query language for chad people

-> Name('foo') => SELECT ast::Name FILTER .py_id = 'foo';
-> Name('foo' | 'bar') => SELECT ast::Name FILTER .py_id = 'foo' OR .py_id = 'bar;
-> Name(ctx=Load()) => SELECT ast::Name FILTER .ctx = <ast::expr_context>"Load";
-> Call(Name('print')) => SELECT ast::Call FILTER .func = (SELECT ast::Name FILTER .py_id = 'print');
"""

import ast
from dataclasses import dataclass, field
from typing import Dict, Tuple, Union

ReizQLObjectKind = Union["ReizQLObject", str, int]


class ReizQLObject:
    ...


class ReizQLSyntaxError(Exception):
    ...


@dataclass
class Node(ReizQLObject):
    name: str
    filters: Dict[str, ReizQLObjectKind] = field(default_factory=dict)


@dataclass
class Or(ReizQLObject):
    left: ReizQLObjectKind
    right: ReizQLObjectKind


# FIX-ME(medium): annotate errors with line/col info
def ensure(condition, message="Invalid syntax"):
    if not condition:
        raise ReizQLSyntaxError(message)


# FIX-ME(post-production): support variables
def convert(node: ast.AST) -> ReizQLObjectKind:
    if isinstance(node, ast.Call):
        return generate_query(node)
    elif isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.BitOr):
            generator = Or
        else:
            raise ReizQLSyntaxError(
                f"Unknown logical operation: {type(node.op).__name__}"
            )
        return Or(convert(node.left), convert(node.right))
    elif isinstance(node, ast.Constant):
        if type(node.value) is int:
            return node.value
        else:
            return str(repr(node.value))
    else:
        raise ReizQLSyntaxError(f"Unexpected node: {node!r}")


def generate_query(node: ast.Call) -> Node:
    ensure(isinstance(node.func, ast.Name))

    query = Node(node.func.id)
    if not hasattr(ast, query.name):
        raise ReizQLSyntaxError(
            f"Unexpected recognized AST node: {query.name}"
        )

    origin = getattr(ast, query.name)
    for index, arg in enumerate(node.args):
        if index > len(origin._fields):
            raise ReizQLSyntaxError(
                f"Too many positional arguments for {query.name}"
            )
        query.filters[origin._fields[index]] = convert(arg)

    # FIX-ME(low): maybe warn if overwriting an argument's value?
    for arg in node.keywords:
        query.filters[arg.arg] = convert(arg.value)

    return query


def parse_query(source: str) -> Node:
    tree = ast.parse(source)
    # FIX-ME(production): work on messages
    ensure(len(tree.body) == 1)
    ensure(isinstance(tree.body[0], ast.Expr))
    ensure(isinstance(tree.body[0].value, ast.Call))
    return convert(tree.body[0].value)
