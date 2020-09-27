from abc import ABC
from dataclasses import dataclass, field
from enum import auto
from typing import Dict, List, Union

from reiz.utilities import ReizEnum


class ReizQLObject(ABC):
    ...


class ReizQLStatement(ReizQLObject):
    ...


class ReizQLExpression(ReizQLObject):
    ...


@ReizQLObject.register
class ReizQLLogicOperator(ReizEnum):
    OR = auto()


@dataclass(unsafe_hash=True)
class ReizQLMatch(ReizQLExpression):
    name: str
    filters: Dict[str, ReizQLExpression] = field(default_factory=dict)


@dataclass(unsafe_hash=True)
class ReizQLBuiltin(ReizQLExpression):
    name: str
    args: List[ReizQLExpression]
    keywords: Dict[str, ReizQLExpression]


@dataclass(unsafe_hash=True)
class ReizQLMatchEnum(ReizQLExpression):
    base: str
    name: str


@dataclass(unsafe_hash=True)
class ReizQLLogicalOperation(ReizQLExpression):
    left: ReizQLExpression
    right: ReizQLExpression
    operator: ReizQLLogicOperator


@dataclass(unsafe_hash=True)
class ReizQLList(ReizQLExpression):
    items: List[ReizQLExpression]


@dataclass(unsafe_hash=True)
class ReizQLSet(ReizQLExpression):
    items: List[ReizQLExpression]


@dataclass(unsafe_hash=True)
class ReizQLConstant(ReizQLExpression):
    value: Union[str, int]
