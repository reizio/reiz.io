import ast

from reiz.ir import Schema


def iter_attributes(node):
    for attribute in node._attributes:
        if hasattr(node, attribute):
            yield attribute, getattr(node, attribute)


def iter_properties(node):
    yield from ast.iter_fields(node)
    yield from iter_attributes(node)


def iter_children(node):
    for field, value in ast.iter_fields(node):
        if isinstance(value, ast.AST):
            yield field, value
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    yield field, item


def alter_ast(node, alter_type, value):
    if alter_type not in ("_fields", "_attributes"):
        raise ValueError(
            f"Invalid alter_type value for alter_ast: {alter_type}"
        )
    original = getattr(node, alter_type)
    setattr(node, alter_type, original + (value,))


def annotate_ast_types(node_type, base=None, last_id=0):
    for sub_node_type in node_type.__subclasses__():
        sub_node_type.kind_name = sub_node_type.__name__
        sub_node_type.base_name = base or sub_node_type.kind_name
        sub_node_type.is_enum = issubclass(sub_node_type, Schema.enum_types)
        sub_node_type.type_id = last_id
        last_id = annotate_ast_types(
            sub_node_type, base=sub_node_type.kind_name, last_id=last_id + 1
        )
    return last_id + 1


def calculate_node_tag(node):
    if hasattr(node, "tag"):
        return node.raw_tag
    elif node is None:
        return -1
    elif not isinstance(node, ast.AST):
        return node

    tag = [node.type_id]
    for field, value in ast.iter_fields(node):
        if field in Schema.tag_excluded_fields:
            continue

        if isinstance(value, ast.AST) or value is None:
            tag.append(calculate_node_tag(value))
        elif isinstance(value, list):
            tag.append(tuple(calculate_node_tag(item) for item in value))
        else:
            tag.append(value)

    node.raw_tag = tuple(tag)
    return node.raw_tag


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

for sum_type in Schema.module_annotated_types:
    alter_ast(sum_type, "_attributes", "_module")
    alter_ast(sum_type, "_attributes", "_tag")
    alter_ast(sum_type, "_attributes", "_parent_types")


class QLAst(ast.NodeTransformer):
    """
    Takes the raw AST generated from 3.8 Python
    parser, and post-processes it according to
    fit it into the EdgeQL format
    """

    def add_parents(self, tree):
        tree._parent = None
        tree._parent_field = None
        for parent in ast.walk(tree):
            for field, child in iter_children(parent):
                child._parent = parent
                child._parent_field = field

    def get_parents(self, node):
        while parent := node._parent:
            yield node._parent_field, parent
            node = parent

    def annotate(self, tree):
        self.add_parents(tree)

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

    def visit_annotated_base(self, node):
        calculate_node_tag(node)
        node._tag = hash(node.raw_tag)
        node._parent_types = list(
            {
                (parent.type_id, field)
                for field, parent in self.get_parents(node)
                if field is not None
            }
        )
        return node

    visit_expr = visit_annotated_base
    visit_stmt = visit_annotated_base
    visit_arg = visit_annotated_base

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
    visitor = QLAst()
    visitor.annotate(tree)
    return visitor.visit(tree)


annotate_ast_types(ast.AST)
