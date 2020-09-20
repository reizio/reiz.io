import ast

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
        raise ReizQLSyntaxError.from_node(message, node)


def convert(node):
    if isinstance(node, ast.Call):
        ensure(isinstance(node.func, ast.Name), node)

        name = node.func.id
        ensure(hasattr(ast, node.func.id), node, f"Unknown matcher: {name!r}")

        origin = getattr(ast, name)
        origin_type = type(node)

        if isinstance(origin, ENUM_TYPES):
            return ReizQLMatchEnum(name, origin_type.__base__.__name__)
        else:
            query = {}

            for index, arg in enumerate(node.args):
                ensure(
                    index < len(node._fields),
                    node,
                    f"Too many positional arguments for {name!r}",
                )
                query[origin._fields[index]] = convert(arg)

            for arg in node.keywords:
                ensure(
                    arg.arg not in node.args,
                    node,
                    f"{arg.arg} specified with both positional and keyword arg",
                )
                query[arg.arg] = convert(arg.value)

            return ReizQLMatch(name, query)
    elif isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.BitOr):
            operator = ReizQLLogicOperator.OR
        else:
            raise ReizQLSyntaxError.from_node(
                node.op, f"Unknown logical operation: {type(node.op).__name__}"
            )

        return ReizQLLogicalOperation(
            left=convert(node.left),
            right=convert(node.right),
            operator=operator,
        )
    elif isinstance(node, ast.Constant):
        if type(node.value) is int:
            value = node.value
        else:
            value = repr(repr(node.value))
        return ReizQLConstant(value)
    elif isinstance(node, ast.List):
        ensure(
            all(isinstance(item, ast.Call) for item in node.elts),
            node,
            "A list may only contain matchers, not atoms",
        )
        return ReizQLList([convert(item) for item in node.elts])
    elif isinstance(node, ast.Set):
        return ReizQLSet([convert(item) for item in node.elts])
    else:
        raise ReizQLSyntaxError.from_node(node, "Invalid syntax")


def parse_query(source):
    tree = ast.parse(source)
    ensure(len(tree.body) == 1, tree)
    ensure(isinstance(tree.body[0], ast.Expr), tree.body[0])
    ensure(isinstance(tree.body[0].value, ast.Call), tree.body[0].value)
    return convert(tree.body[0].value)


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
