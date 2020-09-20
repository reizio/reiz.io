from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

from reiz.db.schema import protected_name
from reiz.edgeql.base import (
    EdgeQLExpression,
    EdgeQLObject,
    EdgeQLStatement,
    construct,
    construct_sequence,
    with_parens,
)
from reiz.edgeql.expr import (
    EdgeQLComparisonOperator,
    EdgeQLFilterKey,
    EdgeQLLogicOperator,
)


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


def make_filter(**kwargs):
    query = None
    for key, value in kwargs.items():
        construction = EdgeQLFilter(EdgeQLFilterKey(key), value)
        if query is None:
            query = construction
        else:
            query = EdgeQLFilterChain(query, construction)
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
    name: str
    limit: Optional[int] = None
    filters: Optional[EdgeQLFilterT] = None
    selections: Sequence[EdgeQLSelector] = field(default_factory=list)

    def construct(self):
        query = "SELECT "
        query += protected_name(self.name)
        if self.selections:
            query += with_parens(
                ", ".join(construct_sequence(self.selections)), combo="{}"
            )
        if self.filters is not None:
            query += f" FILTER {construct(self.filters)}"
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
