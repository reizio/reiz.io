from __future__ import annotations

import ast
import tokenize
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cached_property, singledispatch

from reiz.config import config
from reiz.database import get_new_connection
from reiz.edgeql import (
    EdgeQLCall,
    EdgeQLCast,
    EdgeQLComparisonOperator,
    EdgeQLFilter,
    EdgeQLFilterKey,
    EdgeQLInsert,
    EdgeQLPreparedQuery,
    EdgeQLReference,
    EdgeQLReizCustomList,
    EdgeQLSelect,
    EdgeQLSet,
    EdgeQLUpdate,
    EdgeQLVariable,
    as_edgeql,
    make_filter,
    protected_name,
)
from reiz.edgeql.prepared_queries import FETCH_FILES, FETCH_PROJECTS
from reiz.edgeql.schema import MODULE_ANNOTATED_TYPES, protected_name
from reiz.serialization.transformers import (
    BASIC_TYPES,
    iter_properties,
    prepare_ast,
)
from reiz.utilities import guarded, logger

FILE_CACHE = frozenset()
PROJECT_CACHE = frozenset()


def sync_global_cache(connection):
    global FILE_CACHE, PROJECT_CACHE

    query_set = connection.query(as_edgeql(FETCH_FILES))
    FILE_CACHE = frozenset(module.filename for module in query_set)

    query_set = connection.query(as_edgeql(FETCH_PROJECTS))
    PROJECT_CACHE = frozenset(project.name for project in query_set)


@dataclass
class SerializationContext:
    path: Path
    project: ast.project
    connection: EdgeDBConnection

    stack: List[ast.AST] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    reference_pool: List[UUID4] = field(default_factory=list)

    def new_reference(self, node):
        query_set = insert(node, self)
        self.reference_pool.append(query_set.id)
        return query_set

    def get_tree(self):
        with tokenize.open(self.path) as stream:
            source = stream.read()

        tree = prepare_ast(ast.parse(source))
        tree.project = self.project
        tree.filename = self.rel_filename
        return tree

    @contextmanager
    def enter_node(self, node):
        try:
            self.stack.append(node)
            yield
        finally:
            self.stack.pop()

    @property
    def flows_from(self):
        if len(self.stack) >= 1:
            return self.stack[-1]
        else:
            return None

    @cached_property
    def rel_filename(self):
        return str(self.path.relative_to(config.data.clean_directory))

    @cached_property
    def skip(self):
        return self.rel_filename in FILE_CACHE


@singledispatch
def serialize(value, context):
    message = f"Unexpected object for serialization: {value!r} ({type(value)})"
    if context.flows_from:
        message += f" (flowing from {context.flows_from})"
    raise ValueError(message)


@serialize.register(ast.project)
def serialize_project(node, context):
    return EdgeQLSelect(
        node.kind_name,
        filters=make_filter(
            name=EdgeQLPreparedQuery(repr(context.project.name))
        ),
        limit=1,
    )


@serialize.register(ast.AST)
def serialize_ast(node, context):
    if node.is_enum:
        # <ast::op>'Add'
        return EdgeQLCast(
            protected_name(node.base_name, prefix=True), repr(node.kind_name)
        )
    else:
        # (INSERT ast::BinOp {.left := ..., ...})
        reference = context.new_reference(node)
        # (SELECT ast::expr FILTER .id = ... LIMIT 1)
        return EdgeQLSelect(
            node.base_name,
            filters=make_filter(id=EdgeQLReference(reference)),
            limit=1,
        )


@serialize.register(list)
def serialize_sequence(sequence, context):
    edgeql_set = EdgeQLSet([serialize(value, context) for value in sequence])

    if all(isinstance(item, BASIC_TYPES) for item in sequence):
        # {1, 2, 3} / {<ast::op>'Add', <ast::op>'Sub', ...}
        return edgeql_set
    else:
        # Inserting a sequence of AST objects would require special
        # attention to calculate the index property.
        return EdgeQLReizCustomList(edgeql_set)


@serialize.register(str)
def serialize_string(value, context):
    return EdgeQLPreparedQuery(repr(value))


@serialize.register(int)
def serialize_integer(value, context):
    return EdgeQLPreparedQuery(value)


@serialize.register(type(None))
def serialize_sentinel(value, context):
    return serialize(ast.Sentinel(), context)


def insert(node, context):
    with context.enter_node(node):
        insertions = {
            field: serialize(value, context)
            for field, value in iter_properties(node)
            if value is not None
        }

    query = EdgeQLInsert(node.kind_name, insertions)
    return context.connection.query_one(as_edgeql(query))


@guarded
def insert_file(context):
    if context.skip:
        return None

    tree = context.get_tree()
    module = insert(tree, context)
    module_select = EdgeQLSelect(
        name=tree.kind_name,
        filters=make_filter(id=EdgeQLReference(module)),
        limit=1,
    )

    update_filter = EdgeQLFilter(
        EdgeQLFilterKey("id"),
        EdgeQLCall(
            "array_unpack",
            [EdgeQLCast("array<uuid>", EdgeQLVariable("ids"))],
        ),
        operator=EdgeQLComparisonOperator.CONTAINS,
    )
    for base in MODULE_ANNOTATED_TYPES:
        update = EdgeQLUpdate(
            base.kind_name,
            filters=update_filter,
            assigns={"_module": module_select},
        )
        context.connection.query(as_edgeql(update), ids=context.reference_pool)

    logger.info("%r has been inserted successfully", context.rel_filename)


def insert_project(instance):
    project = ast.project(
        instance.name, instance.git_source, instance.git_revision
    )

    with get_new_connection() as connection:
        sync_global_cache(connection)
        if project.name not in PROJECT_CACHE:
            project_context = SerializationContext(None, project, connection)
            insert(project, project_context)

        project_path = config.data.clean_directory / project.name
        for file in project_path.glob("**/*.py"):
            file_context = SerializationContext(file, project, connection)
            with file_context.connection.transaction():
                insert_file(file_context)
