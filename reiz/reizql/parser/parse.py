import ast
import functools

from reiz.ir import IR
from reiz.reizql.parser import ReizQLSyntaxError, grammar

BUILTIN_FUNCTIONS = ("ALL", "ANY", "LEN", "I")
POSITION_ATTRIBUTES = frozenset(
    ("lineno", "col_offset", "end_lineno", "end_col_offset")
)


def ensure(condition, node=None, message="Invalid syntax"):
    if not condition:
        if node is None:
            raise ReizQLSyntaxError(message)
        else:
            raise ReizQLSyntaxError.from_node(node, message)


@functools.lru_cache
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
            return grammar.Builtin(
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

        if issubclass(origin, IR.schema.enum_types):
            return grammar.MatchEnum(origin.__base__.__name__, name)
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

            return grammar.Match(name, query, positional=positional)

    @parse.register(ast.BinOp)
    def parse_binop(self, node):
        if isinstance(node.op, ast.BitOr):
            operator = grammar.LogicOperator.OR
        elif isinstance(node.op, ast.BitAnd):
            operator = grammar.LogicOperator.AND
        else:
            raise ReizQLSyntaxError.from_node(
                node.op, f"Unknown logical operation: {type(node.op).__name__}"
            )

        return grammar.LogicalOperation(
            left=self.parse(node.left),
            right=self.parse(node.right),
            operator=operator,
        )

    @parse.register(ast.Constant)
    def parse_constant(self, node):
        if node.value is Ellipsis:
            return grammar.Ignore
        elif node.value is None:
            return grammar.Cease
        else:
            return grammar.Constant(node.value)

    @parse.register(ast.List)
    def parse_list(self, node):
        return grammar.List([self.parse(item) for item in node.elts])

    @parse.register(ast.UnaryOp)
    def parse_unary(self, node):
        if isinstance(node.op, ast.Not):
            return grammar.Not(self.parse(node.operand))
        elif isinstance(node.op, ast.Invert):
            ensure(isinstance(node.operand, ast.Name))
            return grammar.Ref(node.operand.id)
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
        return grammar.Expand

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
        return grammar.MatchString(original_source)


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

    ensure(isinstance(root_node, grammar.Match), tree.body[0])
    ensure(root_node.positional, tree.body[0])
    return root_node
