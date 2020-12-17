from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

from reiz.edgeql.base import (
    EdgeQLExpression,
    EdgeQLObject,
    EdgeQLStatement,
    construct,
    construct_sequence,
    protected_construct,
    with_parens,
)
from reiz.edgeql.expr import (
    EdgeQLComparisonOperator,
    EdgeQLFilterKey,
    EdgeQLLogicOperator,
    EdgeQLVerifyOperator,
)
from reiz.edgeql.schema import protected_name


class EdgeQLComponent(EdgeQLObject):
    ...


EdgeQLFilterT = Union["EdgeQLFilter", "EdgeQLFilterChain"]


@dataclass(unsafe_hash=True)
class EdgeQLSelector(EdgeQLComponent):
    selector: str
    inner_selections: List[EdgeQLSelector] = field(default_factory=list)

    def construct(self):
        selector = self.selector
        if self.inner_selections:
            selector += ": "
            selector += with_parens(
                ", ".join(construct_sequence(self.inner_selections)),
                combo="{}",
            )
        return selector


@dataclass(unsafe_hash=True)
class EdgeQLUnion(EdgeQLComponent):
    left: EdgeQLObject
    right: EdgeQLObject

    def construct(self):
        return construct(self.left) + " UNION " + construct(self.right)

    @classmethod
    def from_seq(cls, items):
        union = None
        for item in items:
            if union is None:
                union = item
            else:
                union = cls(union, item)
        return union


@dataclass(unsafe_hash=True)
class EdgeQLFilter(EdgeQLComponent):
    key: EdgeQLExpression
    value: EdgeQLObject
    operator: EdgeQLComparisonOperator = EdgeQLComparisonOperator.EQUALS

    def construct(self):
        key = construct(self.key)
        value = construct(self.value)
        operator = construct(self.operator)
        return key + " " + operator + " " + value


@dataclass(unsafe_hash=True)
class EdgeQLFilterChain(EdgeQLComponent):
    left: EdgeQLFilterT
    right: EdgeQLFilterT
    operator: EdgeQLLogicOperator = EdgeQLLogicOperator.AND

    def construct(self):
        left = construct(self.left)
        right = construct(self.right)
        operator = construct(self.operator)
        return left + " " + operator + " " + right


EdgeQLFilterType = (EdgeQLFilter, EdgeQLFilterChain)
_FILTER_EXPR_MARK = "_returns_bool"


def as_edgeql_filter_expr(expr):
    setattr(expr, _FILTER_EXPR_MARK, True)
    return expr


def is_edgeql_filter_expr(expr):
    if isinstance(expr, EdgeQLFilterType):
        return True
    else:
        return getattr(expr, _FILTER_EXPR_MARK, False)


def make_filter(**kwargs):
    query = None
    for key, value in kwargs.items():
        construction = EdgeQLFilter(EdgeQLFilterKey(key), value)
        if query is None:
            query = construction
        else:
            query = EdgeQLFilterChain(query, construction)
    return query


def unpack_filters(filters, operator=None):
    if filters is None:
        yield from ()
    elif isinstance(filters, EdgeQLSelect):
        yield filters, operator
    elif isinstance(filters, EdgeQLFilter):
        yield filters, operator
    else:
        yield from unpack_filters(filters.left, filters.operator)
        yield from unpack_filters(filters.right, filters.operator)


def merge_filters(left_filter, right_filter, operator=EdgeQLLogicOperator.AND):
    if left_filter is None:
        return right_filter
    else:
        return EdgeQLFilterChain(left_filter, right_filter, operator)


@dataclass(unsafe_hash=True)
class EdgeQLVerify(EdgeQLComponent):
    query: EdgeQLObject
    argument: EdgeQLObject
    operator: EdgeQLVerifyOperator = EdgeQLVerifyOperator.IS

    def construct(self):
        query = construct(self.query)
        check = construct(self.operator) + " " + construct(self.argument)
        return query + with_parens(check, combo="[]")


@dataclass(unsafe_hash=True)
class EdgeQLCoalesce(EdgeQLStatement):
    value: EdgeQLObject
    option: EdgeQLObject

    def construct(self):
        return construct(self.value) + " ?? " + construct(self.option)


@dataclass(unsafe_hash=True)
class EdgeQLWithBlock(EdgeQLStatement):
    assignments: Dict[str, EdgeQLObject] = field(default_factory=dict)

    def construct(self):
        query = "WITH"
        if not self.assignments:
            raise ValueError("Empty WITH blocks are not allowed!")
        query += " " + ", ".join(
            f"{assignment} := {construct(value)}"
            for assignment, value in self.assignments.items()
        )
        return query


@dataclass(unsafe_hash=True)
class EdgeQLInsert(EdgeQLStatement):
    name: str
    fields: Dict[str, EdgeQLObject] = field(default_factory=dict)

    def construct(self):
        query = "INSERT"
        query += " " + protected_name(self.name)
        if self.fields:
            query += " " + with_parens(
                ", ".join(
                    f"{protected_name(key, prefix=False)} := {construct(value)}"
                    for key, value in self.fields.items()
                ),
                combo="{}",
            )
        return query


@dataclass(unsafe_hash=True)
class EdgeQLSelect(EdgeQLStatement):
    name: EdgeQLObject = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    ordered: Optional[EdgeQLObject] = None
    filters: Optional[EdgeQLFilterT] = None
    selections: Sequence[EdgeQLSelector] = field(default_factory=list)
    with_block: Optional[EdgeQLWithBlock] = None

    def is_bare(self, *parameters):
        data = {keyword: getattr(self, keyword) for keyword in parameters}
        for keyword in parameters:
            if keyword == "name" and not isinstance(self.name, str):
                return False
        else:
            return self == self.__class__(**data)

    def construct(self):
        if self.with_block:
            query = construct(self.with_block, top_level=True) + " SELECT"
        else:
            query = "SELECT"

        query += " " + protected_construct(self.name)
        if self.selections:
            query += with_parens(
                ", ".join(construct_sequence(self.selections)), combo="{}"
            )
        if self.filters is not None:
            query += f" FILTER {construct(self.filters)}"
        if self.ordered is not None:
            query += f" ORDER BY {construct(self.ordered)}"
        if self.offset is not None:
            query += f" OFFSET {self.offset}"
        if self.limit is not None:
            query += f" LIMIT {self.limit}"
        return query


@dataclass(unsafe_hash=True)
class EdgeQLUpdate(EdgeQLStatement):
    name: str
    filters: Optional[EdgeQLFilterT] = None
    assigns: Dict[str, EdgeQLObject] = field(default_factory=dict)

    def construct(self):
        query = "UPDATE"
        query += " " + protected_name(self.name)
        if self.filters is not None:
            query += f" FILTER {construct(self.filters)}"
        query += " SET"
        query += " " + with_parens(
            ", ".join(
                f"{protected_name(key, prefix=False)} := {construct(value)}"
                for key, value in self.assigns.items()
            ),
            combo="{}",
        )
        return query


@dataclass(unsafe_hash=True)
class EdgeQLFor(EdgeQLStatement):
    target: EdgeQLObject
    iterator: EdgeQLObject
    generator: EdgeQLObject

    def construct(self):
        query = "FOR "
        query += construct(self.target)
        query += " IN "
        query += construct(self.iterator)
        query += " UNION "
        query += construct(self.generator)
        return query


@dataclass(unsafe_hash=True)
class EdgeQLReizCustomList(EdgeQLStatement):
    items: EdgeQLSet

    # FIX-ME(low): Maybe refactor this to it's own components
    def construct(self):
        query = "WITH"
        query += " __items := "
        query += construct(self.items)
        query += ", "
        query += "FOR __item IN {enumerate(__items)} "
        query += "UNION (SELECT __item.1 { @index := __item.0 })"
        return query
