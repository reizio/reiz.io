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
    ...


def ensure(condition, message="Invalid syntax"):
    if not condition:
        raise ReizQLSyntaxError(message)


def convert(node):
    if isinstance(node, ast.Call):
        ensure(isinstance(node.func, ast.Name))

        name = node.func.id
        ensure(hasattr(ast, node.func.id), f"Unknown matcher: {name!r}")

        origin = getattr(ast, name)
        origin_type = type(node)

        if isinstance(origin, ENUM_TYPES):
            return ReizQLMatchEnum(name, origin_type.__base__.__name__)
        else:
            query = {}

            for index, arg in enumerate(node.args):
                ensure(
                    index < len(node._fields),
                    f"Too many positional arguments for {name!r}",
                )
                query[origin._fields[index]] = convert(arg)

            for arg in node.keywords:
                ensure(
                    arg.arg not in node.args,
                    f"{arg.arg} specified with both positional and keyword arg",
                )
                query[arg.arg] = convert(arg.value)

            return ReizQLMatch(name, query)
    elif isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.BitOr):
            operator = ReizQLLogicOperator.OR
        else:
            raise ReizQLSyntaxError(
                f"Unknown logical operation: {type(node.op).__name__}"
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
            value = str(repr(node.value))
        return ReizQLConstant(value)
    elif isinstance(node, ast.List):
        ensure(
            all(isinstance(item, ast.Call) for item in node.elts),
            "A list may only contain matchers, not atoms",
        )
        return ReizQLList([convert(item) for item in node.elts])
    elif isinstance(node, ast.Set):
        return ReizQLSet([convert(item) for item in node.elts])
    else:
        raise ReizQLSyntaxError(f"Unexpected node: {node!r}")


def parse_query(source):
    tree = ast.parse(source)
    ensure(len(tree.body) == 1)
    ensure(isinstance(tree.body[0], ast.Expr))
    ensure(isinstance(tree.body[0].value, ast.Call))
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
