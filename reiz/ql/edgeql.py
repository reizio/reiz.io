from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from reiz.db.schema import protected_name

ATOMIC_TYPES = (int, str)


def with_parens(node, combo="()"):
    left, right = combo
    return f"{left}{node!s}{right}"


def cast(type_name, value):
    return f"<{type_name}>{value!r}"


def ref(obj):
    return cast("uuid", str(obj.id))


class QLObject:
    ...


class QLStatement(QLObject):
    def prepare_arguments(
        self, arguments, operator="=", key_prefix=None, protected=False
    ):
        body = []
        for key, value in arguments.items():
            if protected:
                key = protected_name(key, prefix=False)
            body.append(f"{key} {operator} {value}")
            if key_prefix is not None:
                body[-1] = key_prefix + body[-1]
        return ", ".join(body)


@dataclass(frozen=True, unsafe_hash=True)
class Prepared(QLObject):
    value: str

    def construct(self):
        return self.value


@dataclass(frozen=True, unsafe_hash=True)
class QLStatementWithParameters(QLStatement):
    name: str
    fields: Dict[str, Any] = field(default_factory=dict)

    PARENS = "{}"
    OPERATOR = "="

    def construct(self):
        query = type(self).__name__.upper()
        query += " " + protected_name(self.name)
        if arguments := self.prepare_arguments(
            self.fields, operator=self.OPERATOR, protected=True
        ):
            query += " " + with_parens(arguments, self.PARENS)
        return query


@dataclass(frozen=True, unsafe_hash=True)
class Insert(QLStatementWithParameters):
    OPERATOR = ":="


@dataclass(frozen=True, unsafe_hash=True)
class Select(QLStatementWithParameters):
    limit: Optional[int] = None
    filters: Optional[Dict[str, Any]] = field(default_factory=dict)

    def construct(self):
        query = super().construct()
        if self.filters:
            args = self.prepare_arguments(self.filters, key_prefix=".")
            query += f" FILTER {with_parens(args)}"
        if self.limit is not None:
            query += f" LIMIT {self.limit}"
        return query


@dataclass(frozen=True, unsafe_hash=True)
class Update(QLStatement):
    name: str
    assigns: Dict[str, str] = field(default_factory=dict)
    filters: Optional[Dict[str, str]] = field(default_factory=dict)

    def construct(self):
        query = "UPDATE"
        query += " " + protected_name(self.name)
        if self.filters:
            query += " FILTER "
            filter_opts = (
                f".{key} = {value}" for key, value in self.filters.items()
            )
            query += " AND ".join(filter_opts)
        query += " SET "
        query += with_parens(
            self.prepare_arguments(self.assigns, operator=":="), combo="{}"
        )
        return query
