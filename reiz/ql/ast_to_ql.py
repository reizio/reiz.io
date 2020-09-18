import ast
import tokenize
from dataclasses import dataclass, field
from typing import List, Optional

from reiz.db.schema import ENUM_TYPES, protected_name
from reiz.ql.edgeql import (
    Call,
    FilterItem,
    Insert,
    Prepared,
    QLCompareOperator,
    Select,
    Update,
    Variable,
    cast,
    ref,
    with_parens,
)
from reiz.utilities import logger

# FIX-ME(low): extract all ast utilities into their own
# module.


MODULE_ANNOTATED_TYPES = (ast.expr, ast.stmt)


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
        if (base := self.infer_base(node)) is not type(node):
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

    @staticmethod
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


@dataclass
class QLState:
    from_parent: Optional[ast.AST] = None
    reference_pool: List[str] = field(default_factory=list)


def convert(connection, ql_state, obj):
    if isinstance(obj, ast.AST):
        if isinstance(obj, ENUM_TYPES):
            obj_type = type(obj)
            enum_type = obj_type.__base__

            obj_name = protected_name(obj_type.__name__, prefix=False)
            enum_name = protected_name(enum_type.__name__)
            return cast(enum_name, obj_name)
        else:
            db_obj = insert(connection, ql_state, obj)
            ql_state.reference_pool.append(db_obj.id)
            selection = Select(
                QLAst.infer_base(obj).__name__,
                limit=1,
                filters=FilterItem("id", ref(db_obj)),
            )
            return with_parens(selection.construct())
    elif isinstance(obj, list):
        items = (convert(connection, ql_state, value) for value in obj)
        return with_parens(", ".join(items), combo="{}")
    elif type(obj) is int:
        return obj
    elif isinstance(obj, str):
        return repr(obj)
    elif isinstance(obj, Prepared):
        return obj.value
    elif obj is None:
        return convert(connection, ql_state, Sentinel())
    else:
        message = f"Unexpected object: {obj!r}"
        if ql_state.from_parent is not None:
            message += f" flowing from {ql_state.from_parent}"
        raise ValueError(message + ".")


def insert(connection, ql_state, node):
    node_type = type(node).__name__
    insertions = {}
    ql_state.from_parent = node
    for field, value in (*ast.iter_fields(node), *iter_attributes(node)):
        if value is None:
            continue
        insertions[field] = convert(connection, ql_state, value)
    query = Insert(node_type, insertions).construct()
    logger.trace("Running query: %r", query)
    return connection.query_one(query)


# FIX-ME(high): consider partial insertion of very big
# module in order to avoid serialization bugs in EdgeDB.
# e.g: defining a limit of N(30?) items, and breaking the
# large lists up according to that limit and inserting
# in multiple batches.
def insert_file(connection, file):
    with tokenize.open(file) as file_p:
        source = file_p.read()
    tree = QLAst.visit(ast.parse(source))
    # FIX-ME(low): remove <rawdata>/<provider> prefix
    tree.filename = str(file)
    ql_state = QLState()
    with connection.transaction():
        module = insert(connection, ql_state, tree)
        module_select = with_parens(
            Select(
                "Module", limit=1, filters=FilterItem("id", ref(module))
            ).construct()
        )

        ids = Variable("ids")
        id_pool = cast("array<uuid>", ids)
        unpacked_id_pool = Call("array_unpack", id_pool).construct()
        update_filter = FilterItem(
            "id", unpacked_id_pool, operator=QLCompareOperator.CONTAINS
        )
        # FIX-ME(low): research about how to do this in a single query
        # instead of 3 seperate batches.
        for base in MODULE_ANNOTATED_TYPES:
            update = Update(
                base.__name__,
                filters=update_filter,
                assigns={"_module": module_select},
            ).construct()
            logger.trace("Running post-insert query: %r", update)
            connection.query(update, ids=ql_state.reference_pool)
