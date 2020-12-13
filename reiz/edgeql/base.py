from abc import ABC, abstractmethod
from dataclasses import dataclass

from reiz.db.schema import protected_name


class EdgeQLObject(ABC):
    @abstractmethod
    def construct(self):
        ...


class EdgeQLStatement(EdgeQLObject):
    ...


class EdgeQLExpression(EdgeQLObject):
    ...


class EdgeQLPseudo(EdgeQLObject):
    ...


@dataclass(unsafe_hash=True)
class EdgeQLPreparedQuery(EdgeQLObject):
    value: str

    def construct(self):
        return self.value


def construct(value, top_level=False):
    if isinstance(value, EdgeQLObject):
        result = value.construct()
        if isinstance(value, EdgeQLStatement) and not top_level:
            return with_parens(result)
        else:
            return result
    else:
        return str(value)


def protected_construct(value):
    if isinstance(value, str):
        return protected_name(value)
    else:
        return construct(value)


def construct_sequence(sequence):
    yield from map(construct, sequence)


def with_parens(value, combo="()"):
    left, right = combo
    return f"{left}{value}{right}"


def real_object(obj):
    while isinstance(obj, EdgeQLPseudo):
        obj = obj.value
    return obj
