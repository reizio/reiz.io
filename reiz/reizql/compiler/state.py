from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List

from reiz.ir import IR
from reiz.reizql.compiler.analysis import Scope
from reiz.reizql.compiler.field_db import FIELD_DB
from reiz.reizql.parser import ReizQLSyntaxError


@dataclass
class CompilerState:
    match: str
    depth: int = 0

    pointer_stack: List[str] = field(default_factory=list)
    scope: Scope = field(default_factory=Scope)
    filters: List[IR.expression] = field(default_factory=list)
    variables: Dict[IR.name, IR.expression] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    parents: List[CompilerState] = field(default_factory=list, repr=False)

    copy = deepcopy

    @classmethod
    def from_parent(cls, name, parent):
        return cls(
            name,
            depth=parent.depth + 1,
            scope=parent.scope,
            parents=parent.parents + [parent],
            filters=parent.filters,
            variables=parent.variables,
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
        self.pointer_stack.append(pointer)
        try:
            yield
        finally:
            self.pointer_stack.pop()

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

    def compute_path(self, allow_missing=False):
        parent, *parents = self.get_ordered_parents()

        def get_pointer(state, allow_missing):
            pointer = state.pointer
            if allow_missing:
                pointer = IR.optional(pointer)
            return pointer

        base = get_pointer(parent, allow_missing)
        if not parent.is_flag_set("in for loop"):
            base = IR.attribute(None, base)

        for parent in parents:
            base = IR.typed(base, parent.match)
            base = IR.attribute(base, get_pointer(parent, allow_missing))

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

    def is_special(self, name):
        return name.startswith("__") and name.endswith("__")

    @property
    def is_root(self):
        return self.depth == 0

    @property
    def pointer(self):
        return IR.wrap(self.pointer_stack[-1], with_prefix=False)

    @property
    def field_info(self):
        assert not self.is_special(self.match)
        return FIELD_DB[self.match][self.pointer_stack[0]]
