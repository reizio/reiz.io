import ast
import functools

from reiz.db.schema import ENUM_TYPES
from reiz.reizql.nodes import (
    ReizQLAttr,
    ReizQLBuiltin,
    ReizQLConstant,
    ReizQLExpand,
    ReizQLIgnore,
    ReizQLList,
    ReizQLLogicalOperation,
    ReizQLLogicOperator,
    ReizQLMatch,
    ReizQLMatchEnum,
    ReizQLNot,
    ReizQLSet,
)

BUILTIN_FUNCTIONS = ("ALL", "ANY", "LEN")
POSITION_ATTRIBUTES = frozenset(
    ("lineno", "col_offset", "end_lineno", "end_col_offset")
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


def ensure(condition, node=None, message="Invalid syntax"):
    if not condition:
        if node is None:
            raise ReizQLSyntaxError(message)
        else:
            raise ReizQLSyntaxError.from_node(node, message)


def is_valid_matcher(name):
    return hasattr(ast, name) or name in BUILTIN_FUNCTIONS


@functools.singledispatch
def parse(node):
    raise ReizQLSyntaxError.from_node(node, "Invalid syntax")


@parse.register(ast.Call)
def parse_call(node):
    ensure(isinstance(node.func, ast.Name), node)

    name = node.func.id
    ensure(is_valid_matcher(node.func.id), node, f"Unknown matcher: {name!r}")

    if name in BUILTIN_FUNCTIONS:
        return ReizQLBuiltin(
            name,
            [parse(arg) for arg in node.args],
            {keyword.arg: parse(keyword.value) for keyword in node.keywords},
        )

    origin = getattr(ast, name)
    if POSITION_ATTRIBUTES.issubset(origin._attributes):
        positional = True
    else:
        positional = False

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

        return ReizQLMatch(name, query, positional=positional)


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
    if node.value is Ellipsis:
        return ReizQLIgnore
    else:
        return ReizQLConstant(repr(node.value))


@parse.register(ast.List)
def parse_list(node):
    return ReizQLList([parse(item) for item in node.elts])


@parse.register(ast.Set)
def parse_set(node):
    return ReizQLSet([parse(item) for item in node.elts])


@parse.register(ast.UnaryOp)
def parse_unary(node):
    if isinstance(node.op, ast.Not):
        return ReizQLNot(parse(node.operand))
    elif isinstance(node.op, ast.Invert):
        ensure(isinstance(node.operand, ast.Name))
        return ReizQLAttr(node.operand.id)
    else:
        raise ReizQLSyntaxError.from_node(node, "unknown unary operator")


@parse.register(ast.Starred)
def parse_starred(node):
    ensure(
        (
            isinstance(node.value, ast.Constant)
            and node.value.value is Ellipsis
        ),
        node,
    )
    return ReizQLExpand


def parse_query(source):
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ReizQLSyntaxError(exc.args[0])
    ensure(len(tree.body) == 1)
    ensure(isinstance(tree.body[0], ast.Expr), tree.body[0])
    ensure(isinstance(tree.body[0].value, ast.Call), tree.body[0].value)
    root_node = parse(tree.body[0].value)
    ensure(isinstance(root_node, ReizQLMatch), tree.body[0])
    ensure(root_node.positional or root_node.name == "Module", tree.body[0])
    return root_node


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
