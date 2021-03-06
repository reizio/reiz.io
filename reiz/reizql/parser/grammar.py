import ast
import typing
from dataclasses import dataclass, field
from enum import auto

from reiz.utilities import ReizEnum, singleton


class RQL:
    ...


class Unit(RQL):
    ...


class Statement(RQL):
    ...


class Expression(RQL):
    ...


@singleton
class Ignore(Expression):
    ...


@singleton
class Expand(Expression):
    ...


@singleton
class Cease(Expression):
    ...


class LogicOperator(Unit, ReizEnum):
    OR = auto()
    AND = auto()


@dataclass
class Match(Expression):
    name: str
    bound_node: ast.AST = field(repr=False)

    filters: typing.Dict[str, Expression] = field(default_factory=dict)
    positional: bool = False


@dataclass
class Builtin(Expression):
    name: str
    args: typing.List[Expression]
    keywords: typing.Dict[str, Expression]


@dataclass
class MatchEnum(Expression):
    base: str
    name: str


@dataclass
class LogicalOperation(Expression):
    left: Expression
    right: Expression
    operator: LogicOperator


@dataclass
class List(Expression):
    items: typing.List[Expression]


@dataclass
class Set(Expression):
    items: typing.List[Expression]


@dataclass
class Constant(Expression):
    value: typing.Union[str, int]


@dataclass
class Not(Expression):
    value: Expression


@dataclass
class Ref(Expression):
    name: str


@dataclass
class MatchString(Expression):
    value: str
