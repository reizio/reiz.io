import ast
import functools

from reiz.db.schema import ATOMIC_TYPES, ENUM_TYPES
from reiz.reizql.nodes import (
    ReizQLConstant,
    ReizQLList,
    ReizQLLogicalOperation,
    ReizQLLogicOperator,
    ReizQLMatch,
    ReizQLMatchEnum,
    ReizQLSet,
)


class ReizQLSyntaxError(Exception):
    @property
    def message(self):
        return self.args[0]

    @property
    def position(self):
        if len(self.args) < 3:
            return None
        else:
            lineno, col_offset, end_lineno, end_col_offset = self.args[1:5]
            return {
                "lineno": lineno,
                "col_offset": col_offset,
                "end_lineno": end_lineno,
                "end_col_offset": end_col_offset,
            }

    @classmethod
    def from_node(cls, node, message):
        return cls(
            message,
            node.lineno,
            node.col_offset,
            node.end_lineno,
            node.end_col_offset,
        )


def ensure(condition, node, message="Invalid syntax"):
    if not condition:
        raise ReizQLSyntaxError.from_node(node, message)


@functools.singledispatch
def parse(node):
    raise ReizQLSyntaxError.from_node(node, "Invalid syntax")


@parse.register(ast.Call)
def parse_call(node):
    ensure(isinstance(node.func, ast.Name), node)

    name = node.func.id
    ensure(hasattr(ast, node.func.id), node, f"Unknown matcher: {name!r}")

    origin = getattr(ast, name)
    if issubclass(origin, ENUM_TYPES):
        return ReizQLMatchEnum(origin.__base__.__name__, name)
    else:
        query = {}

        for index, arg in enumerate(node.args):
            ensure(
                index < len(node._fields),
                node,
                f"Too many positional arguments for {name!r}",
            )
            query[origin._fields[index]] = parse(arg)

        for arg in node.keywords:
            ensure(
                arg.arg not in node.args,
                node,
                f"{arg.arg} specified with both positional and keyword arg",
            )
            query[arg.arg] = parse(arg.value)

        return ReizQLMatch(name, query)


@parse.register(ast.BinOp)
def parse_binop(node):
    if isinstance(node.op, ast.BitOr):
        operator = ReizQLLogicOperator.OR
    else:
        raise ReizQLSyntaxError.from_node(
            node.op, f"Unknown logical operation: {type(node.op).__name__}"
        )

    return ReizQLLogicalOperation(
        left=parse(node.left),
        right=parse(node.right),
        operator=operator,
    )


@parse.register(ast.Constant)
def parse_constant(node):
    if type(node.value) is int:
        value = repr(node.value)
    else:
        value = repr(str(node.value))
    return ReizQLConstant(repr(str(node.value)))


@parse.register(ast.List)
def parse_list(node):
    ensure(
        all(isinstance(item, ast.Call) for item in node.elts),
        node,
        "A list may only contain matchers, not atoms",
    )
    return ReizQLList([parse(item) for item in node.elts])


@parse.register(ast.Set)
def parse_set(node):
    return ReizQLSet([parse(item) for item in node.elts])


def parse_query(source):
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ReizQLSyntaxError(exc.args[0])
    ensure(len(tree.body) == 1, tree)
    ensure(isinstance(tree.body[0], ast.Expr), tree.body[0])
    ensure(isinstance(tree.body[0].value, ast.Call), tree.body[0].value)
    return parse(tree.body[0].value)


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
    options.source.close()


if __name__ == "__main__":
    main()