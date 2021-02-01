from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any, Dict, List, Optional

from reiz.ir import IR
from reiz.reizql.compiler.analysis import Scope
from reiz.reizql.compiler.field_db import FIELD_DB
from reiz.reizql.parser import ReizQLSyntaxError


@dataclass
class CompilerState:
    match: str
    depth: int = 0

    field: Optional[str] = None
    scope: Scope = dataclass_field(default_factory=Scope)
    properties: Dict[str, Any] = dataclass_field(default_factory=dict)
    parents: List[CompilerState] = dataclass_field(
        default_factory=list, repr=False
    )

    freeze = deepcopy

    @classmethod
    def from_parent(cls, name, parent):
        return cls(
            name,
            depth=parent.depth + 1,
            scope=parent.scope,
            parents=parent.parents + [parent],
            properties=parent.properties,
        )

    @classmethod
    def set_codegen(cls, codegen):
        def _codegen(self, node):
            return codegen(node, self)

        cls.codegen = _codegen
        return codegen

    @contextmanager
    def new_scope(self):
        try:
            self.scope = Scope.from_parent(self.scope)
            yield
        finally:
            self.scope = self.scope.exit()

    @contextmanager
    def temp_pointer(self, pointer):
        _old_pointer = self.field
        try:
            self.field = pointer
            yield
        finally:
            self.field = _old_pointer

    @contextmanager
    def temp_flag(self, flag, value=True):
        _preserved_value = self.is_flag_set(flag)
        try:
            self.set_flag(flag, value)
            yield
        finally:
            self.set_flag(flag, _preserved_value)

    def set_flag(self, flag, value=True):
        self.properties[flag] = value

    def is_flag_set(self, flag, default=False):
        return self.properties.get(flag, default)

    # Just an implementation detail that they both share
    # the same internal structure.
    get_property = is_flag_set
    set_property = set_flag
    temp_property = temp_flag

    def compile(self, key, value):
        with self.temp_pointer(key):
            return self.codegen(value)

    def compute_path(self):
        base = None
        for parent in self.get_ordered_parents():
            if base is None:
                if self.can_raw_name_access:
                    base = parent.pointer
                else:
                    base = IR.attribute(None, parent.pointer)
            else:
                base = IR.attribute(
                    IR.typed(base, parent.match), parent.pointer
                )
        return base

    def get_ordered_parents(self):
        parents = self.parents + [self]
        enumeration_start = self.get_property("enumeration start depth")
        if enumeration_start is None:
            return parents

        for index, parent in enumerate(parents):
            if parent.depth == enumeration_start:
                break
        else:
            raise ReizQLSyntaxError(
                "compiler check failed: no enumeration start block found!"
            )
        return parents[index:]

    def ensure(self, node, condition):
        if not condition:
            raise ReizQLSyntaxError(f"compiler check failed for: {node!r}")

    def as_unique_ref(self, prefix):
        return

    @property
    def is_root(self):
        return self.depth == 0

    @property
    def can_raw_name_access(self):
        return self.is_flag_set("in for loop")

    @property
    def pointer(self):
        return IR.wrap(self.field, with_prefix=False)

    @property
    def field_info(self):
        return FIELD_DB[self.match][self.field]
