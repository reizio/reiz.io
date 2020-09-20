import ast

from reiz.db.schema import MODULE_ANNOTATED_TYPES


def iter_attributes(node):
    for attribute in node._attributes:
        if hasattr(node, attribute):
            yield attribute, getattr(node, attribute)


def alter_ast(node, alter_type, value):
    if alter_type not in ("_fields", "_attributes"):
        raise ValueError(
            f"Invalid alter_type value for alter_ast: {alter_type}"
        )
    original = getattr(node, alter_type)
    setattr(node, alter_type, original + (value,))


class Sentinel(ast.expr):
    """Represents double-asterisk at dict-unpackings"""

    _fields = ()

    lineno = 0
    end_lineno = 0

    col_offset = 0
    end_col_offset = 0


alter_ast(ast.Module, "_fields", "filename")
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
