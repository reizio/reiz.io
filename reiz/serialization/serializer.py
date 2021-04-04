from __future__ import annotations

import ast
import tokenize
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import cached_property, singledispatch

from reiz.config import config
from reiz.database import DatabaseConnection, get_new_connection
from reiz.ir import IR, Schema
from reiz.serialization.cache import Cache
from reiz.serialization.transformers import iter_properties, prepare_ast
from reiz.utilities import guarded, logger


class Insertion(Enum):
    CACHED = auto()
    SKIPPED = auto()
    INSERTED = auto()


@dataclass
class SerializationContext:
    path: Path
    project: ast.project
    connection: DatabaseConnection
    fast_mode: bool = False

    stack: List[ast.AST] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    reference_pool: List[UUID4] = field(default_factory=list)

    def new_reference(self, reference):
        self.reference_pool.append(reference)

    def get_tree(self):
        with tokenize.open(self.path) as stream:
            source = stream.read()

        if self.fast_mode and len(source) > 80 * 80:
            return None

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

    def is_cached(self, cache):
        return self.rel_filename in cache.files

    def add_cache(self, cache):
        cache.files.add(self.rel_filename)


@singledispatch
def serialize(value, context):
    message = f"Unexpected object for serialization: {value!r} ({type(value)})"
    if context.flows_from:
        message += f" (flowing from {context.flows_from})"
    raise ValueError(message)


@serialize.register(ast.project)
def serialize_project(node, context):
    return IR.select(
        node.kind_name,
        filters=IR.filter(
            IR.attribute(None, "name"), IR.literal(context.project.name), "="
        ),
        limit=1,
    )


@serialize.register(ast.AST)
def serialize_ast(node, context):
    if node.is_enum:
        # <ast::op>'Add'
        return IR.enum_member(node.base_name, node.kind_name)
    else:
        # (INSERT ast::BinOp {.left := ..., ...})
        reference = insert(node, context)
        context.new_reference(reference.id)

        # (SELECT ast::expr FILTER .id = ... LIMIT 1)
        return IR.select(
            node.base_name, filters=IR.object_ref(reference), limit=1
        )


_BASIC_SET_TYPES = Schema.enum_types + (int, str, tuple)


@serialize.register(list)
def serialize_sequence(sequence, context):
    ir_set = IR.set([serialize(value, context) for value in sequence])

    if all(isinstance(item, _BASIC_SET_TYPES) for item in sequence):
        # {1, 2, 3} / {<ast::op>'Add', <ast::op>'Sub', ...}
        return ir_set
    else:
        # Inserting a sequence of AST objects would require special
        # attention to calculate the index property.
        target = IR.name("item")
        scope = IR.namespace({"items": ir_set})
        loop = IR.loop(
            target,
            IR.call("enumerate", [IR.name("items")]),
            IR.select(
                IR.attribute(target, 1),
                selections=[
                    IR.assign(IR.property("index"), IR.attribute(target, 0))
                ],
            ),
        )
        return IR.add_namespace(scope, loop)


@serialize.register(tuple)
def serialize_tuple(sequence, context):
    return IR.tuple([serialize(value, context) for value in sequence])


@serialize.register(str)
@serialize.register(int)
def serialize_string(value, context):
    return IR.literal(value)


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

    query = IR.insert(node.kind_name, insertions)
    return context.connection.query_one(IR.construct(query))


@guarded
def insert_file(context, cache):
    if context.is_cached(cache):
        return Insertion.CACHED

    if not (tree := context.get_tree()):
        return Insertion.SKIPPED

    with context.connection.transaction():
        module = insert(tree, context)
        module_select = IR.select(
            tree.kind_name, filters=IR.object_ref(module), limit=1
        )

        update_filter = IR.filter(
            IR.attribute(None, "id"),
            IR.call(
                "array_unpack", [IR.cast("array<uuid>", IR.variable("ids"))]
            ),
            "IN",
        )
        for base_type in Schema.module_annotated_types:
            update = IR.update(
                base_type.kind_name,
                filters=update_filter,
                assignments={"_module": module_select},
            )
            context.connection.query(
                IR.construct(update), ids=context.reference_pool
            )

    logger.info("%r has been inserted successfully", context.rel_filename)
    return Insertion.INSERTED


def insert_project(instance, *, cache=None, limit=None, fast=False):
    project = instance.as_ast()

    with get_new_connection() as connection:
        if cache is None:
            cache = Cache()
            cache.sync(connection)

        if project.name not in cache.projects:
            project_context = SerializationContext(None, project, connection)
            insert(project, project_context)
            cache.projects.add(project.name)

        total_inserted = 0
        project_path = config.data.clean_directory / project.name
        for file in project_path.glob("**/*.py"):
            if limit is not None and total_inserted >= limit:
                break

            file_context = SerializationContext(
                file, project, connection, fast
            )
            if insert_file(file_context, cache) is Insertion.INSERTED:
                total_inserted += 1
                file_context.add_cache(cache)

    return total_inserted
