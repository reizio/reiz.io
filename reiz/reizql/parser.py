import ast
import functools

from reiz.edgeql.schema import ENUM_TYPES
from reiz.reizql.nodes import (
    ReizQLBuiltin,
    ReizQLConstant,
    ReizQLExpand,
    ReizQLIgnore,
    ReizQLList,
    ReizQLLogicalOperation,
    ReizQLLogicOperator,
    ReizQLMatch,
    ReizQLMatchEnum,
    ReizQLMatchString,
    ReizQLNone,
    ReizQLNot,
    ReizQLRef,
)

BUILTIN_FUNCTIONS = ("ALL", "ANY", "LEN", "ATTR")
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
            return {}
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


class Parser:
    def __init__(self, source):
        self.source = source

    @functools.singledispatchmethod
    def parse(self, node):
        raise ReizQLSyntaxError.from_node(node, "Invalid syntax")

    @parse.register(ast.Call)
    def parse_call(self, node):
        ensure(isinstance(node.func, ast.Name), node)

        name = node.func.id
        ensure(
            is_valid_matcher(node.func.id), node, f"Unknown matcher: {name!r}"
        )

        if name in BUILTIN_FUNCTIONS:
            return ReizQLBuiltin(
                name,
                [self.parse(arg) for arg in node.args],
                {
                    keyword.arg: self.parse(keyword.value)
                    for keyword in node.keywords
                },
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
                query[origin._fields[index]] = self.parse(arg)

            for arg in node.keywords:
                ensure(
                    arg.arg not in node.args,
                    node,
                    f"{arg.arg} specified with both positional and keyword arg",
                )
                query[arg.arg] = self.parse(arg.value)

            return ReizQLMatch(name, query, positional=positional)

    @parse.register(ast.BinOp)
    def parse_binop(self, node):
        if isinstance(node.op, ast.BitOr):
            operator = ReizQLLogicOperator.OR
        elif isinstance(node.op, ast.BitAnd):
            operator = ReizQLLogicOperator.AND
        else:
            raise ReizQLSyntaxError.from_node(
                node.op, f"Unknown logical operation: {type(node.op).__name__}"
            )

        return ReizQLLogicalOperation(
            left=self.parse(node.left),
            right=self.parse(node.right),
            operator=operator,
        )

    @parse.register(ast.Constant)
    def parse_constant(self, node):
        if node.value is Ellipsis:
            return ReizQLIgnore
        elif node.value is None:
            return ReizQLNone
        else:
            return ReizQLConstant(repr(node.value))

    @parse.register(ast.List)
    def parse_list(self, node):
        return ReizQLList([self.parse(item) for item in node.elts])

    @parse.register(ast.UnaryOp)
    def parse_unary(self, node):
        operand = self.parse(node.operand)
        if isinstance(node.op, ast.Not):
            return ReizQLNot(operand)
        elif isinstance(node.op, ast.Invert):
            ensure(isinstance(operand, ReizQLRef))
            return operand
        else:
            raise ReizQLSyntaxError.from_node(node, "unknown unary operator")

    @parse.register(ast.Starred)
    def parse_starred(self, node):
        ensure(
            (
                isinstance(node.value, ast.Constant)
                and node.value.value is Ellipsis
            ),
            node,
        )
        return ReizQLExpand

    @parse.register(ast.Name)
    def parse_name(self, node):
        return ReizQLRef(node.id)

    @parse.register(ast.JoinedStr)
    def parse_match_string(self, node):
        raw_source = ast.get_source_segment(self.source, node)
        assert raw_source.startswith("f")

        original_source = ast.literal_eval(raw_source[1:])
        ensure(
            len(original_source) > 0,
            node,
            "Empty match strings are not allowed",
        )
        return ReizQLMatchString(ReizQLConstant(repr(original_source)))


def parse_query(source):
    if isinstance(source, bytes):
        source = source.decode()

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ReizQLSyntaxError(exc.args[0])

    ensure(len(tree.body) == 1)
    ensure(isinstance(tree.body[0], ast.Expr), tree.body[0])
    ensure(isinstance(tree.body[0].value, ast.Call), tree.body[0].value)

    parser = Parser(source)
    root_node = parser.parse(tree.body[0].value)

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
