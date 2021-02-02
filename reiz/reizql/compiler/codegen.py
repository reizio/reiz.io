from __future__ import annotations

from functools import singledispatch

from reiz.ir import IR
from reiz.reizql.compiler.functions import Signature
from reiz.reizql.compiler.state import CompilerState
from reiz.reizql.parser import grammar
from reiz.serialization.transformers import ast

_COMPILER_WORKAROUND_FOR_TARGET = "_singleton"


@CompilerState.set_codegen
@singledispatch
def codegen(node, state):
    raise ValueError(f"Unknown node: {type(node).__name__}")


@codegen.register(grammar.Match)
def compile_matcher(node, state):
    if state is None:
        state = CompilerState(node.name)
    else:
        state = CompilerState.from_parent(node.name, state)

    filters = None
    for key, value in node.filters.items():
        if value is grammar.Ignore:
            continue

        if right_filter := state.compile(key, value):
            filters = IR.combine_filters(filters, right_filter)

    if state.is_root:
        state.scope.exit()
        if state.variables:
            namespace = IR.namespace(state.variables)
            filters = IR.add_namespace(namespace, IR.select(filters))
        return IR.select(state.match, filters=filters)

    if filters is None:
        filters = IR.filter(
            state.parents[-1].compute_path(), IR.wrap(state.match), "IS"
        )

    return filters


@codegen.register(grammar.MatchEnum)
def convert_match_enum(node, state):
    expr = IR.enum_member(node.base, node.name)
    return IR.filter(state.compute_path(), expr, "=")


@codegen.register(grammar.Constant)
def compile_constant(node, state):
    expr = IR.literal(node.value)

    # Constants are represented as repr(obj) in the
    # serialization part, so we have to re-cast it.
    if state.match == "Constant":
        expr.value = repr(expr.value)

    return IR.filter(state.compute_path(), expr, "=")


@codegen.register(grammar.MatchString)
def compile_match_string(node, state):
    expr = IR.literal(node.value)
    return IR.filter(state.compute_path(), expr, "LIKE")


@codegen.register(grammar.Not)
def compile_operator_flip(node, state):
    return IR.negate(state.codegen(node.value))


@codegen.register(grammar.LogicalOperation)
def convert_logical_operation(node, state):
    return IR.filter(
        state.codegen(node.left),
        state.codegen(node.right),
        state.codegen(node.operator),
    )


@codegen.register(grammar.LogicOperator)
def convert_logical_operator(node, state):
    if node is grammar.LogicOperator.OR:
        return IR.as_operator("OR")
    elif node is grammar.LogicOperator.AND:
        return IR.as_operator("AND")


@codegen.register(grammar.Ref)
def compile_reference(node, state):
    obtained_type = state.field_info.type

    if pointer := state.scope.lookup(node.name):
        expected_type = pointer.field_info.type
        state.ensure(node, expected_type is obtained_type)

        left = state.compute_path()
        right = pointer.compute_path()

        if issubclass(expected_type, ast.expr):
            left = IR.attribute(left, "tag")
            right = IR.attribute(right, "tag")

        return IR.filter(left, right, "=")

    state.ensure(node, issubclass(obtained_type, (str, int, ast.expr)))
    state.scope.define(node.name, state.copy())


def aggregate_array(state):
    # If we are in a nested list search (e.g: Call(args=[Call(args=[Name()])]))
    # we can't directly use `ORDER BY @index` since the EdgeDB can't quite infer
    # which @index are we talking about.
    if state.is_flag_set("in for loop"):
        path = IR.attribute(
            IR.typed(IR.name(_COMPILER_WORKAROUND_FOR_TARGET), state.match),
            state.pointer,
        )
        body = IR.loop(
            IR.name(_COMPILER_WORKAROUND_FOR_TARGET),
            state.parents[-1].compute_path(),
            IR.select(path, order=IR.property("index")),
        )
    else:
        body = IR.select(state.compute_path(), order=IR.property("index"))

    return IR.call("array_agg", [body])


@codegen.register(grammar.List)
def compile_sequence(node, state):
    total_length = len(node.items)
    length_verifier = IR.filter(
        IR.call("count", [state.compute_path()]), total_length, "="
    )

    if total_length == 0 or all(
        item in (grammar.Ignore, grammar.Expand) for item in node.items
    ):
        return length_verifier

    if total := node.items.count(grammar.Expand):
        state.ensure(node, total == 1)
        length_verifier = IR.filter(
            IR.call("count", [state.compute_path()]), total_length - 1, ">="
        )

    array_ref = IR.new_reference("sequence")
    state.variables[array_ref] = aggregate_array(state)

    expansion_seen = False
    with state.temp_flag("in for loop"), state.temp_property(
        "enumeration start depth", state.depth
    ), state.new_scope():
        filters = None
        for position, matcher in enumerate(node.items):
            if matcher is grammar.Ignore:
                continue
            elif matcher is grammar.Expand:
                expansion_seen = True
                continue

            state.ensure(matcher, isinstance(matcher, grammar.Match))
            if expansion_seen:
                position = -(total_length - position)

            with state.temp_pointer(IR.subscript(array_ref, position)):
                filters = IR.combine_filters(filters, state.codegen(matcher))

    assert filters is not None
    return IR.combine_filters(length_verifier, filters)


@codegen.register(type(grammar.Cease))
def convert_none(node, state):
    return IR.negate(IR.exists(state.compute_path()))


@codegen.register(grammar.Builtin)
def convert_call(node, state):
    signature = Signature.get_function(node.name)
    state.ensure(node, signature is not None)
    return signature.codegen(node, state)


def compile_to_ir(node):
    return codegen(node, None)
