from abc import ABC, abstractmethod
from dataclasses import dataclass


class EdgeQLObject(ABC):
    @abstractmethod
    def construct(self):
        ...


class EdgeQLStatement(EdgeQLObject):
    ...


class EdgeQLExpression(EdgeQLObject):
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


def construct_sequence(sequence):
    yield from map(construct, sequence)


def with_parens(value, combo="()"):
    left, right = combo
    return f"{left}{value}{right}"
