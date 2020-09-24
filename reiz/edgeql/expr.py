from __future__ import annotations

from dataclasses import dataclass
from enum import auto

from reiz.db.schema import protected_name
from reiz.edgeql.base import (
    EdgeQLExpression,
    construct,
    construct_sequence,
    with_parens,
)
from reiz.utilities import ReizEnum


@EdgeQLExpression.register
class EdgeQLVerifyOperator(ReizEnum):
    IS = auto()

    def construct(self):
        return self.name


@EdgeQLExpression.register
class EdgeQLLogicOperator(ReizEnum):
    IN = auto()
    OR = auto()
    AND = auto()

    def construct(self):
        return self.name


@EdgeQLExpression.register
class EdgeQLComparisonOperator(ReizEnum):
    EQUALS = "="
    CONTAINS = "IN"
    NOT_EQUALS = "!="

    def construct(self):
        return self.value


@dataclass(unsafe_hash=True)
class EdgeQLContainer(EdgeQLExpression):

    items: List[EdgeQLObject]

    def construct(self):
        body = ", ".join(construct_sequence(self.items))
        return with_parens(body, combo=self.PARENS)


@dataclass(unsafe_hash=True)
class EdgeQLTuple(EdgeQLContainer):
    PARENS = "()"


@dataclass(unsafe_hash=True)
class EdgeQLArray(EdgeQLContainer):
    PARENS = "[]"


@dataclass(unsafe_hash=True)
class EdgeQLSet(EdgeQLContainer):
    PARENS = "{}"


@dataclass(unsafe_hash=True)
class EdgeQLName(EdgeQLExpression):
    name: str

    def construct(self):
        return self.name


class EdgeQLSpecialName(EdgeQLName):
    def construct(self):
        return self.PREFIX + self.name


@dataclass(unsafe_hash=True)
class EdgeQLVariable(EdgeQLSpecialName):
    PREFIX = "$"


@dataclass(unsafe_hash=True)
class EdgeQLFilterKey(EdgeQLSpecialName):
    PREFIX = "."


@dataclass(unsafe_hash=True)
class EdgeQLProperty(EdgeQLSpecialName):
    PREFIX = "@"


@dataclass(unsafe_hash=True)
class EdgeQLAttribute(EdgeQLExpression):
    base: EdgeQLObject
    attr: str

    def construct(self):
        return construct(self.base) + "." + self.attr


@dataclass(unsafe_hash=True)
class EdgeQLCall(EdgeQLExpression):
    func: str
    args: List[EdgeQLObject]

    def construct(self):
        body = ", ".join(construct_sequence(self.args))
        return self.func + with_parens(body)


@dataclass(unsafe_hash=True)
class EdgeQLCast(EdgeQLExpression):
    type: str
    value: EdgeQLObject

    def construct(self):
        return f"<{self.type}>{construct(self.value)}"


@dataclass(unsafe_hash=True)
class EdgeQLReference(EdgeQLExpression):
    value: Any

    def construct(self):
        return construct(EdgeQLCast("uuid", repr(str(self.value.id))))
