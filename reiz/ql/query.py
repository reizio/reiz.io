"""
ReizQL - Query language for chad people

-> Name('foo') => SELECT ast::Name FILTER .py_id = 'foo';
-> Name('foo' | 'bar') => SELECT ast::Name FILTER .py_id = 'foo' OR .py_id = 'bar;
-> Name(ctx=Load()) => SELECT ast::Name FILTER .ctx = <ast::expr_context>"Load";
-> Call(Name('print')) => SELECT ast::Call FILTER .func = (SELECT ast::Name FILTER .py_id = 'print');
-> Call(Name('print'), args=[Starred()]) => SELECT ast::Call FILTER .func = (SELECT ast::Name FILTER .py_id = 'print') AND .args = {(SELECT ast::Starred)};
"""

# Internals
#   - ReizQL is a python-subset, which compiles to the EdgeQL
#   - The aim is having a single expression matchers where people
#   - can query things without required to learn any other language.
#   ClassDef(
#      name = 'foo',
#      bases = any(
#          Name('int')
#     )
#   )


import ast
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Tuple, Union

from reiz.db.schema import ATOMIC_TYPES, ENUM_TYPES, protected_name
from reiz.ql.edgeql import (
    Filter,
    FilterItem,
    ListOf,
    Prepared,
    QLLogicOperator,
    Select,
    cast,
    with_parens,
)

ReizQLObjectKind = Union["ReizQLObject", str, int]


class ReizQLObject:
    ...


class QLLogical(ReizQLObject):
    ...


class ReizQLSyntaxError(Exception):
    ...


@dataclass
class QLNode(ReizQLObject):
    name: str
    filters: Dict[str, ReizQLObjectKind] = field(default_factory=dict)


@dataclass
class QLEnum(ReizQLObject):
    name: str
    base: str


@dataclass
class QLOr(QLLogical):
    left: ReizQLObjectKind
    right: ReizQLObjectKind


@dataclass
class QLList(ReizQLObject):
    items: List[ReizQLObject]


@dataclass
class QLAny(ReizQLObject):
    value: ReizQLObject


BUILTIN_FUNCTIONS = {"any": QLAny}

# FIX-ME(high): flatten in a way that, if we add more logical operators
# they don't get collapsed (x or y and z or q)
def flatten_logical_expression(
    expression: QLLogical,
) -> Iterator[ReizQLObject]:
    for item in (expression.left, expression.right):
        if isinstance(item, QLLogical):
            yield from flatten_logical_expression(item)
        else:
            yield item


# FIX-ME(medium): annotate errors with line/col info
def ensure(condition, message="Invalid syntax"):
    if not condition:
        raise ReizQLSyntaxError(message)


# FIX-ME(post-production): support variables
def convert(node: ast.AST) -> ReizQLObjectKind:
    if isinstance(node, ast.Call):
        ensure(isinstance(node.func, ast.Name))

        name = node.func.id
        if name in BUILTIN_FUNCTIONS:
            ensure(len(node.args) == 1)
            ensure(len(node.keywords) == 0)
            return BUILTIN_FUNCTIONS[name](convert(node.args[0]))
        else:
            return generate_query(node)
    elif isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.BitOr):
            generator = QLOr
        else:
            raise ReizQLSyntaxError(
                f"Unknown logical operation: {type(node.op).__name__}"
            )
        return generator(convert(node.left), convert(node.right))
    elif isinstance(node, ast.Constant):
        if type(node.value) is int:
            return node.value
        else:
            return str(repr(node.value))
    elif isinstance(node, ast.List):
        return QLList([convert(item) for item in node.elts])
    else:
        raise ReizQLSyntaxError(f"Unexpected node: {node!r}")


def generate_query(node: ast.Call) -> Union[QLNode, QLEnum]:
    name = node.func.id
    if not hasattr(ast, name):
        raise ReizQLSyntaxError(
            f"Unexpected recognized AST node: {query.name}"
        )

    origin = getattr(ast, name)
    if issubclass(origin, ENUM_TYPES):
        return QLEnum(name, origin.__base__)

    query = QLNode(name)
    for index, arg in enumerate(node.args):
        if index > len(origin._fields):
            raise ReizQLSyntaxError(
                f"Too many positional arguments for {name}"
            )
        query.filters[origin._fields[index]] = convert(arg)

    # FIX-ME(low): maybe warn if overwriting an argument's value?
    for arg in node.keywords:
        query.filters[arg.arg] = convert(arg.value)

    return query


def parse_query(source: str) -> QLNode:
    tree = ast.parse(source)
    # FIX-ME(production): work on messages
    ensure(len(tree.body) == 1)
    ensure(isinstance(tree.body[0], ast.Expr))
    ensure(isinstance(tree.body[0].value, ast.Call))
    # FIX-ME(medium): add a check whether it returned an Enum
    # or a Node.
    return convert(tree.body[0].value)


def convert_edgeql(obj, field=None):
    if isinstance(obj, QLEnum):
        # FIX-ME(low): is this protected_name(obj.name) required?
        return CastOf(obj.base, obj.name)
    elif isinstance(obj, QLNode):
        return generate_edgeql(obj)
    elif isinstance(obj, QLLogical):
        query = None
        for expression in flatten_logical_expression(obj):
            value = FilterItem(field, convert_edgeql(expression).construct())
            if query is None:
                query = value
            else:
                query = Filter(query, value, QLLogicOperator.OR)
        return query
    elif isinstance(obj, QLAny):
        return ListOf([convert_edgeql(obj.value)])
    elif isinstance(obj, ATOMIC_TYPES):
        return Prepared(obj)
    else:
        raise ReizQLSyntaxError(f"Unexpected query object: {obj!r}")


def generate_edgeql(node, selections=()):
    query = None
    for key, value in node.filters.items():
        key = protected_name(key, prefix=False)
        conversion = convert_edgeql(value, key)
        if not isinstance(conversion, (Filter, FilterItem)):
            conversion = FilterItem(key, conversion.construct())

        if query is None:
            query = conversion
        else:
            query = Filter(query, conversion)
    return Select(node.name, filters=query, selections=selections)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source",
        type=argparse.FileType(mode="rb"),
        nargs="?",
        default="-",
        help="the file to parse; defaults to stdin",
    )
    options = parser.parse_args()
    tree = parse_query(options.source.read())
    print(tree)
    print(generate_edgeql(tree).construct())


if __name__ == "__main__":
    main()
