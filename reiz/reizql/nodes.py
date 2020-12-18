from abc import ABC
from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import Dict, List, Union

from reiz.utilities import ReizEnum


class ReizQLObject(ABC):
    ...


class ReizQLStatement(ReizQLObject):
    ...


class ReizQLExpression(ReizQLObject):
    ...


@object.__new__
@dataclass(unsafe_hash=True)
class ReizQLIgnore(ReizQLExpression):
    ...


@object.__new__
@dataclass(unsafe_hash=True)
class ReizQLExpand(ReizQLExpression):
    ...


@object.__new__
@dataclass(unsafe_hash=True)
class ReizQLNone(ReizQLExpression):
    ...


@ReizQLObject.register
class ReizQLLogicOperator(ReizEnum, IntEnum):
    OR = auto()
    AND = auto()


@dataclass(unsafe_hash=True)
class ReizQLMatch(ReizQLExpression):
    name: str
    filters: Dict[str, ReizQLExpression] = field(default_factory=dict)
    positional: bool = False


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


@dataclass(unsafe_hash=True)
class ReizQLNot(ReizQLExpression):
    value: ReizQLExpression


@dataclass(unsafe_hash=True)
class ReizQLRef(ReizQLExpression):
    name: str
