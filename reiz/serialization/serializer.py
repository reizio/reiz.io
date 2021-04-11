import ast
from dataclasses import field
from functools import singledispatch

from reiz.ir import IR, Schema
from reiz.serialization.transformers import iter_properties


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
            IR.attribute(None, "name"), IR.literal(node.name), "="
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
        reference = apply_ast(node, context)
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


def apply_ast(node, context):
    with context.enter_node(node):
        insertions = {
            field: serialize(value, context)
            for field, value in iter_properties(node)
            if value is not None
        }

    query = IR.insert(node.kind_name, insertions)
    return context.connection.query_one(IR.construct(query))
