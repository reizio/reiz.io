from __future__ import annotations

from dataclasses import dataclass
from enum import auto

from reiz.edgeql.base import (
    EdgeQLExpression,
    EdgeQLPseudo,
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
    OR = auto()
    AND = auto()

    def construct(self):
        return self.name


@EdgeQLExpression.register
class EdgeQLComparisonOperator(ReizEnum):
    EQUALS = "="
    CONTAINS = "IN"
    IDENTICAL = "IS"
    NOT_EQUALS = "!="
    NOT_CONTAINS = "NOT IN"
    NOT_IDENTICAL = "IS NOT"
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="

    def construct(self):
        return self.value

    def negate(self):
        if self.name in {"GT", "LT", "GTE", "LTE"}:
            return _NEGATIVE_COMPARISON_OPERATORS[self]
        elif self.name.startswith("NOT_"):
            return getattr(self, self.name[4:])
        else:
            return getattr(self, f"NOT_{self.name}")


_NEGATIVE_COMPARISON_OPERATORS = {
    EdgeQLComparisonOperator.GT: EdgeQLComparisonOperator.LTE,
    EdgeQLComparisonOperator.LT: EdgeQLComparisonOperator.GTE,
    EdgeQLComparisonOperator.GTE: EdgeQLComparisonOperator.LT,
    EdgeQLComparisonOperator.LTE: EdgeQLComparisonOperator.GT,
}


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
        return self.PREFIX + construct(self.name)


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
    name: str

    def construct(self):
        return construct(self.base) + "." + self.name


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


@dataclass(unsafe_hash=True)
class EdgeQLSubscript(EdgeQLExpression):
    value: EdgeQLObject
    index: int

    def construct(self):
        return construct(self.value) + "[" + str(self.index) + "]"


@dataclass(unsafe_hash=True)
class EdgeQLNot(EdgeQLPseudo):
    value: EdgeQLObject

    def construct(self):
        return "not " + construct(self.value)


@dataclass(unsafe_hash=True)
class EdgeQLGroup(EdgeQLPseudo):
    value: EdgeQLObject

    def construct(self):
        return "(" + construct(self.value) + ")"
