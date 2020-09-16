from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union

from reiz.db.schema import protected_name

ATOMIC_TYPES = (int, str)
FilterKind = Union["FilterItem", "Filter"]


def with_parens(node, combo="()"):
    left, right = combo
    return f"{left}{node!s}{right}"


def cast(type_name, value):
    return f"<{type_name}>{value!r}"


def ref(obj):
    return cast("uuid", str(obj.id))


# FIX-ME(medium): ability to auto-construct
# all child QLObject-s, so we could avoid
# calling .construct() on every instance


class QLObject:
    ...


class QLLogicOperator(QLObject, Enum):
    IN = auto()
    OR = auto()
    AND = auto()


class QLCompareOperator(QLObject, Enum):
    EQUALS = "="
    CONTAINS = "in"

    def construct(self):
        return self.value


class QLStatement(QLObject):
    def prepare_arguments(self, arguments, operator="=", protected=False):
        body = []
        for key, value in arguments.items():
            if protected:
                key = protected_name(key, prefix=False)
            body.append(f"{key} {operator} {value}")
        return ", ".join(body)


# FIX-ME(low): Maybe use a **kwargs based system for filters
@dataclass(unsafe_hash=True)
class FilterItem(QLObject):
    key: str
    value: str
    operator: QLCompareOperator = QLCompareOperator.EQUALS

    def construct(self):
        return f".{self.key} {self.operator.construct()} {self.value}"


@dataclass(unsafe_hash=True)
class Filter(QLObject):
    left: FilterKind
    right: FilterKind
    operator: QLLogicOperator = QLLogicOperator.AND

    def construct(self):
        left, right = self.left.construct(), self.right.construct()
        return left + " " + self.operator.construct() + " " + right


@dataclass(unsafe_hash=True)
class Prepared(QLObject):
    value: str

    def construct(self):
        return self.value


@dataclass(unsafe_hash=True)
class Variable(QLObject):
    name: str

    def __repr__(self):
        return self.construct()

    def construct(self):
        return "$" + self.name


class Call(QLObject):
    def __init__(self, func: str, *args) -> None:
        self.func = func
        self.args = args

    def construct(self):
        return f"{self.func}(" + ", ".join(self.args) + ")"


@dataclass(unsafe_hash=True)
class Insert(QLStatement):
    name: str
    fields: Dict[str, Any] = field(default_factory=dict)

    def construct(self):
        query = "INSERT"
        query += " " + protected_name(self.name)
        if arguments := self.prepare_arguments(
            self.fields, operator=":=", protected=True
        ):
            query += " " + with_parens(arguments, combo="{}")
        return query


@dataclass(unsafe_hash=True)
class Select(QLStatement):
    name: str
    limit: Optional[int] = None
    filters: Optional[FilterKind] = None
    selections: List[str] = field(default_factory=list)

    def construct(self):
        query = "SELECT "
        query += protected_name(self.name)
        if self.selections:
            query += with_parens(", ".join(self.selections), combo="{}")
        if self.filters is not None:
            query += f" FILTER {self.filters.construct()}"
        if self.limit is not None:
            query += f" LIMIT {self.limit}"
        return query


@dataclass(unsafe_hash=True)
class Update(QLStatement):
    name: str
    assigns: Dict[str, str] = field(default_factory=dict)
    filters: Optional[FilterKind] = None

    def construct(self):
        query = "UPDATE"
        query += " " + protected_name(self.name)
        if self.filters is not None:
            query += f" FILTER {self.filters.construct()}"
        query += " SET "
        query += with_parens(
            self.prepare_arguments(self.assigns, operator=":="), combo="{}"
        )
        return query
