import ast

from reiz.edgeql.schema import ATOMIC_TYPES, ENUM_TYPES, MODULE_ANNOTATED_TYPES

BASIC_TYPES = ENUM_TYPES + ATOMIC_TYPES


def iter_attributes(node):
    for attribute in node._attributes:
        if hasattr(node, attribute):
            yield attribute, getattr(node, attribute)


def iter_properties(node):
    yield from ast.iter_fields(node)
    yield from iter_attributes(node)


def alter_ast(node, alter_type, value):
    if alter_type not in ("_fields", "_attributes"):
        raise ValueError(
            f"Invalid alter_type value for alter_ast: {alter_type}"
        )
    original = getattr(node, alter_type)
    setattr(node, alter_type, original + (value,))


def annotate_ast_types(node_type, base=None):
    for sub_node_type in node_type.__subclasses__():
        sub_node_type.kind_name = sub_node_type.__name__
        sub_node_type.base_name = base or sub_node_type.kind_name
        sub_node_type.is_enum = issubclass(sub_node_type, ENUM_TYPES)
        annotate_ast_types(sub_node_type, base=sub_node_type.kind_name)


class Sentinel(ast.expr):
    """Represents double-asterisk at dict-unpackings"""

    _fields = ()

    lineno = 0
    end_lineno = 0

    col_offset = 0
    end_col_offset = 0


class project(ast.AST):
    _fields = ("name", "git_source", "git_revision")


ast.Sentinel = Sentinel
ast.project = project
alter_ast(ast.Module, "_fields", "filename")
alter_ast(ast.Module, "_fields", "project")
alter_ast(ast.slice, "_attributes", "sentinel")
for sum_type in MODULE_ANNOTATED_TYPES:
    alter_ast(sum_type, "_attributes", "_module")


@object.__new__
class QLAst(ast.NodeTransformer):
    """
    Takes the raw AST generated from 3.8 Python
    parser, and post-processes it according to
    fit it into the EdgeQL format
    """

    def visit(self, node):
        result = super().visit(node)

        # Allow visiting of sum types with the transformed
        # nodes. For an example if a Slice() transformer,
        # visit_slice will be called with the new value.
        if (base := infer_base(node)) is not type(node):
            if visitor := getattr(self, f"visit_{base.__name__}", None):
                result = visitor(result)

        # If we define a custom visitor, ensure all child
        # nodes are visited afterwards.
        if hasattr(self, f"visit_{type(node).__name__}"):
            self.generic_visit(node)
        return result

    def visit_slice(self, node):
        node.sentinel = Sentinel()
        return node

    def visit_decorated(self, node):
        if len(node.decorator_list) >= 1:
            first_decorator = node.decorator_list[0]
            node.lineno = first_decorator.lineno
            node.col_offset = first_decorator.col_offset - 1  # '@'
        return node

    visit_FunctionDef = visit_decorated
    visit_AsyncFunctionDef = visit_decorated
    visit_ClassDef = visit_decorated

    def visit_Constant(self, node):
        node.value = repr(node.value)
        return node


def infer_base(node):
    """
    If node belongs to a sum type, return the base type,
    if not, return its original type
    """

    node_type = type(node)
    if node_type.__base__ is ast.AST:
        return node_type
    else:
        return node_type.__base__


def prepare_ast(tree):
    tree = QLAst.visit(tree)
    return tree


annotate_ast_types(ast.AST)
