from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import List, Optional, Union

from reiz.ir.backends import base
from reiz.ir.builder import IRBuilder
from reiz.ir.optimizer import IROptimizer
from reiz.ir.printer import IRPrinter
from reiz.schema import ESDLSchema
from reiz.utilities import ReizEnum


class EQLPrinter(IRPrinter):
    def view(self, eql_node, *, no_parens=False, top_level=False):
        if isinstance(eql_node, (Expression, Unit)):
            eql_node.construct(self)
        elif isinstance(eql_node, Statement):
            with self.between("()", condition=not (no_parens or top_level)):
                with self.indented(condition=not (no_parens or top_level)):
                    self.newline()
                    eql_node.construct(self)
                    self.newline()
        else:
            self.write(str(eql_node))

    def sequence_view(
        self,
        sequence,
        delimiter=",",
        append=True,
        force_newline=False,
        **view_kwargs,
    ):
        if not sequence:
            return None

        with self.indented():
            sequence = tuple(sequence)
            available_range = len(sequence) - 1
            for pos, item in enumerate(sequence):
                first = pos == 0
                last = pos == available_range

                with self.enter_newlines(
                    condition=(force_newline or available_range > 0)
                ):
                    if not append and not first:
                        self.view(delimiter)
                    self.view(item, **view_kwargs)
                    if append and not last:
                        self.view(delimiter)


class EQL(base.IRObject): ...


class Unit(EQL, base.Unit): ...


class Statement(EQL, base.Statement):
    replace = replace


class Expression(EQL, base.Expression):
    replace = replace


class Operator(Unit, ReizEnum):
    def construct(self, state):
        state.write(self.value)


class UnaryOperator(Operator):
    NOT = "NOT"
    IDENTICAL = "IS"


# TO-DO(SERIOUS): OPERATOR PRECEDENCE ??
class Comparator(str, Operator):
    # Logical
    OR = "OR"
    AND = "AND"
    COALESCE = "??"

    # Values
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    EQUALS = "="
    NOT_EQUALS = "!="

    # Containers
    CONTAINS = "IN"
    NOT_CONTAINS = "NOT IN"

    # Types
    IDENTICAL = "IS"
    NOT_IDENTICAL = "IS NOT"

    # Strings
    LIKE = "LIKE"
    ILIKE = "ILIKE"
    NOT_LIKE = "NOT LIKE"
    NOT_ILIKE = "NOT ILIKE"

    # Bitwise
    BITWISE_OR = "|"


_COUNTER_OPERATORS = {
    Comparator.GT: Comparator.LTE,
    Comparator.LT: Comparator.GTE,
    Comparator.GTE: Comparator.LT,
    Comparator.LTE: Comparator.GT,
    Comparator.EQUALS: Comparator.NOT_EQUALS,
    Comparator.CONTAINS: Comparator.NOT_CONTAINS,
    Comparator.IDENTICAL: Comparator.NOT_IDENTICAL,
    Comparator.LIKE: Comparator.NOT_LIKE,
    Comparator.ILIKE: Comparator.NOT_ILIKE,
}
_COUNTER_OPERATORS.update(
    [(counter, original) for original, counter in _COUNTER_OPERATORS.items()]
)


@dataclass
class UnaryOperation(Expression):
    operand: EQL
    operator: UnaryOperator

    def construct(self, state):
        state.view(self.operator)
        state.write(" ")
        state.view(self.operand)


class ComplexExpression(Expression):
    def construct(self, state):
        elements = tuple(self.unpack())
        if len(elements) > 2:
            self._construct_complex(state)
        else:
            self._construct_simple(state)

    def construct_unpacked(self, state, delimiter):
        with state.between("()"):
            state.newline()
            state.sequence_view(
                self.unpack(), delimiter=delimiter, append=False
            )


@dataclass
class CompareOperation(ComplexExpression):
    left: Expression
    right: Expression
    operator: Comparator

    def unpack(self):
        for side in (self.left, self.right):
            if (
                isinstance(side, CompareOperation)
                and side.operator is Comparator.AND
            ):
                yield from side.unpack()
            else:
                yield side

    def is_simple(self):
        return all(
            not isinstance(side, CompareOperation)
            for side in (self.left, self.right)
        )

    def _construct_complex(self, state):
        self.construct_unpacked(state, Comparator.AND + " ")

    def _construct_simple(self, state):
        with state.between("()", condition=(self.operator is Comparator.OR)):
            state.view(self.left)
            with state.between("  "):
                state.view(self.operator)
            state.view(self.right)


@dataclass
class Union(ComplexExpression):
    left: Expression
    right: Expression

    def unpack(self):
        for side in (self.left, self.right):
            if isinstance(side, Union):
                yield from side.unpack()
            else:
                yield side

    def _construct_complex(self, state):
        self.construct_unpacked(state, "UNION ")

    def _construct_simple(self, state):
        state.view(self.left)
        state.write(" UNION ")
        state.view(self.right)


@dataclass
class _Container(Expression):
    items: List[EQL] = field(default_factory=list)

    def construct(self, state):
        with state.between(self.PARENS):
            state.sequence_view(self.items)


@dataclass
class Literal(Expression):
    value: str

    def construct(self, state):
        state.write(repr(self.value))


class Tuple(_Container):
    PARENS = "()"


class Array(_Container):
    PARENS = "[]"


class Set(_Container):
    PARENS = "{}"


@dataclass(unsafe_hash=True)
class Name(Expression):
    name: str

    def construct(self, state):
        state.write(self.name)


class _PrefixedName(Name):
    def construct(self, state):
        state.write(self.PREFIX + self.name)


class Variable(_PrefixedName):
    PREFIX = "$"


class Property(_PrefixedName):
    PREFIX = "@"


@dataclass
class Attribute(Expression):
    base: EQL
    attr: Union[str, int]

    def construct(self, state):
        state.view(self.base)
        state.write(".")
        state.write(str(self.attr))


@dataclass
class RootAttribute(Expression):
    attr: str

    def construct(self, state):
        state.write(".")
        state.write(self.attr)


@dataclass
class NamespaceAttribute(Expression):
    namespace: str
    attr: str

    def construct(self, state):
        state.write(self.namespace)
        state.write("::")
        state.write(self.attr)


@dataclass
class Subscript(Expression):
    item: EQL
    value: EQL

    def construct(self, state):
        state.view(self.item)
        with state.between("[]"):
            state.view(self.value)


@dataclass
class Call(Expression):
    func: EQL
    args: List[EQL]

    def construct(self, state):
        state.view(self.func)
        with state.between("()"):
            state.sequence_view(self.args)


@dataclass
class Cast(Expression):
    model: EQL
    item: EQL

    def construct(self, state):
        with state.between("<>"):
            state.view(self.model)
        state.view(self.item)


@dataclass
class Exists(Expression):
    value: EQL

    def construct(self, state):
        state.write("EXISTS ")
        state.view(self.value)


@dataclass
class Assign(Expression):
    target: EQL
    value: EQL

    def construct(self, state):
        state.view(self.target)
        state.write(" := ")
        state.view(self.value)


@dataclass
class Selection(Unit):
    selector: EQL
    selectors: List[Selection] = field(default_factory=list)

    def construct(self, state):
        state.view(self.selector)
        if self.selectors:
            state.write(": ")
            with state.between("{}"):
                state.sequence_view(self.selectors)


@dataclass
class With(Statement):
    body: List[EQL] = field(default_factory=list)

    def construct(self, state):
        state.write("WITH")
        state.sequence_view(self.body, force_newline=True)


@dataclass
class WrappedStatement(Statement):
    namespace: With
    statement: Statement

    def construct(self, state):
        state.view(self.namespace, no_parens=True)
        state.write("\n")
        state.view(self.statement, no_parens=True)


@dataclass
class Insert(Statement):
    model: EQL
    body: List[EQL] = field(default_factory=list)

    def construct(self, state):
        state.write("INSERT ")
        state.view(self.model)

        with state.between("{}", condition=self.body):
            state.sequence_view(self.body)


@dataclass
class Select(Statement):
    model: EQL
    limit: Optional[int] = None
    order: Optional[EQL] = None
    offset: Optional[int] = None
    filters: Expression = None
    selections: List[EQL] = field(default_factory=list)

    def construct(self, state):
        state.write("SELECT ")
        state.view(self.model)
        with state.between("{}", condition=self.selections):
            state.sequence_view(self.selections)

        if self.filters:
            state.newline()
            state.write("FILTER ")
            state.view(self.filters)

        if self.order:
            state.newline()
            state.write("ORDER BY ")
            state.view(self.order)

        if self.offset:
            state.newline()
            state.write("OFFSET ")
            state.view(self.offset)

        if self.limit:
            state.newline()
            state.write("LIMIT ")
            state.view(self.limit)


@dataclass
class Update(Statement):
    model: EQL
    filters: Expression = None
    body: List[EQL] = field(default_factory=list)

    def construct(self, state):
        state.write("UPDATE ")
        state.view(self.model)
        if self.filters:
            state.write(" FILTER ")
            state.view(self.filters)
        state.write(" SET ")
        with state.between("{}"):
            state.sequence_view(self.body, no_parens=True)


@dataclass
class For(Statement):
    target: EQL
    iterator: EQL
    body: EQL

    def construct(self, state):
        state.write("FOR ")
        state.view(self.target)
        state.write(" IN ")
        with state.between("{}"):
            state.view(self.iterator)
        state.newline()
        state.write("UNION ")
        state.view(self.body)


class EQLOptimizer(IROptimizer):
    @IROptimizer.optimization
    def optimize_negative_operators(self, node):
        # Optimize operators
        # ReizQL        => Constant(not 'x')
        # Unoptimized   => SELECT ast::Constant
        #                  FILTER NOT .value = "'x'"
        #
        # Optimized     => SELECT ast::Constant
        #                  FILTER .value != "'x'"
        self.ensure(isinstance(node.operand, CompareOperation))
        self.ensure(node.operand.is_simple())
        self.ensure(operator := _COUNTER_OPERATORS.get(node.operand.operator))
        return node.operand.replace(operator=operator)

    @IROptimizer.optimization
    def optimize_double_negatives(self, node):
        # Optimize away double negatives
        # ReizQL        => arg(annotation = not None)
        # Unoptimized   => SELECT ast::arg
        #                  FILTER NOT NOT EXISTS .annotation
        #
        # Optimized     => SELECT ast::arg
        #                  FILTER EXISTS .annotation

        self.ensure(isinstance(node.operand, UnaryOperation))
        self.ensure(node.operator is UnaryOperator.NOT)
        self.ensure(node.operand.operator is UnaryOperator.NOT)
        return node.operand.operand

    @IROptimizer.optimization
    def optimize_type_or(self, node):
        # Optimize away type-level ORs
        # ReizQL        => Return(Name() | Tuple())
        # Unoptimized   => SELECT ast::Return
        #                  FILTER .value IS ast::Name OR .value is ast::Tuple
        #
        # Optimized     => SELECT ast::Return
        #                  FILTER .value IS (ast::Name | ast::Tupel)

        self.ensure(node.operator is Comparator.OR)
        self.ensure(isinstance(node.left, CompareOperation))
        self.ensure(isinstance(node.right, CompareOperation))
        self.ensure(node.left.operator is Comparator.IDENTICAL)
        self.ensure(node.right.operator is Comparator.IDENTICAL)
        self.ensure(isinstance(node.left.right, NamespaceAttribute))
        self.ensure(isinstance(node.right.right, NamespaceAttribute))
        self.ensure(node.left.left == node.right.left)

        rhs = CompareOperation(
            node.left.right, node.right.right, Comparator.BITWISE_OR
        )
        return CompareOperation(node.left.left, rhs, Comparator.IDENTICAL)

    OPTIMIZATIONS = {
        UnaryOperation: [
            optimize_negative_operators,
            optimize_double_negatives,
        ],
        CompareOperation: [optimize_type_or],
    }


class EQLBuilder(IRBuilder, backend_name="EdgeQL"):
    schema = ESDLSchema
    printer = EQLPrinter
    optimizer = EQLOptimizer

    def wrap(self, key, with_prefix=True):
        if isinstance(key, str):
            key = self.schema.wrap(key, with_prefix=False)
            if with_prefix:
                # We don't know whether the key is request for an attribute access
                # or not, so we have to keep it as string. But in case of the prefix
                # is requested, this is definietly a type access, so we are safe to
                # wrap it as an IRObject.
                key = self.from_namespace(self.schema.NAMESPACE, key)
        return key

    def select(self, model, **kwargs):
        if isinstance(model, str):
            model = self.wrap(model, with_prefix=True)

        return Select(model, **kwargs)

    def typed(self, node, model):
        return Subscript(
            node, UnaryOperation(self.wrap(model), UnaryOperator.IDENTICAL)
        )

    def filter(self, left, right, operator):
        return CompareOperation(left, right, self.as_operator(operator))

    def unary_operation(self, operand, operator):
        return UnaryOperation(operand, self.as_operator(operator))

    def enum_member(self, base_type, member_type):
        return Cast(self.wrap(base_type), Literal(member_type))

    def as_operator(self, operator):
        if isinstance(operator, Operator):
            return operator

        for enum in (Comparator, UnaryOperator):
            try:
                return enum(operator)
            except ValueError:
                continue
        else:
            raise self._unsupported(f"operator {operator!r}")

    def object_ref(self, edge_object):
        obj_uuid = self.cast("uuid", self.literal(str(edge_object.id)))
        return self.filter(self.attribute(None, "id"), obj_uuid, "=")

    def as_assignments(self, assignments):
        return [
            self.assign(self.wrap(key, with_prefix=False), value)
            for key, value in assignments.items()
        ]

    def namespace(self, assignments):
        return With(self.as_assignments(assignments))

    def insert(self, model, assignments):
        return Insert(self.wrap(model), self.as_assignments(assignments))

    def update(self, model, filters=None, assignments=None):
        assignments = assignments or {}
        return Update(
            self.wrap(model), filters, self.as_assignments(assignments)
        )

    def attribute(self, base, attr):
        if base is None:
            return RootAttribute(attr)
        else:
            return Attribute(base, attr)

    def optional(self, node):
        if isinstance(node, self.subscript):
            node = self.call("array_get", [node.item, node.value])
        return node

    set = Set
    loop = For
    name = Name
    call = Call
    cast = Cast
    tuple = Tuple
    union = Union
    assign = Assign
    exists = Exists
    literal = Literal
    variable = Variable
    property = Property
    subscript = Subscript
    selection = Selection
    statement = Statement
    expression = Expression
    add_namespace = WrappedStatement
    from_namespace = NamespaceAttribute
