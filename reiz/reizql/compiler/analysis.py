from __future__ import annotations

from dataclasses import dataclass, field
from typing import Counter, Dict, List

from reiz.reizql.parser import ReizQLSyntaxError


@dataclass
class Scope:
    # - 3 kinds of scopes:
    #   - $CUR   (current scope)
    #   - $PAR^n (nth parent's scope)
    #   - $TOP   (initial parent's scope)
    #
    # - Each list matcher creates their own scope. Until a list matcher is seen,
    #   everything belongs to the $CUR.
    #
    # - The parent can't access to any of their children's scope
    #
    # - $CUR can reach up to $TOP, in a linear way. So if $CUR's parent ($PAR^1)
    #   has 2 children (one being $CUR), the $CUR can not their sibling's scope but
    #   can access any symbol defined in between $PAR^n..$TOP.
    #
    # Examples:
    # FunctionDef(
    #       ~name,                              <= name.1
    #       decorator_list = [
    #           Name(~foo),                     <= foo.1
    #           Name(~foo),                     <= foo.1
    #       ],
    #       body = [
    #           Name(~foo),                     <= foo.2
    #           Attribute(Name(~foo)),          <= foo.2
    #           Return(Call(Name(~name)))       <= name.1
    #       ]
    #  )

    parents: List[Scope] = field(default_factory=list)
    definitions: Dict[str, CompilerState] = field(default_factory=dict)
    reference_counts: Counter[str] = field(default_factory=Counter)

    @classmethod
    def from_parent(cls, parent):
        return cls(parents=parent.parents + [parent])

    def lookup(self, name):
        for scope in reversed(self.parents + [self]):
            if state := scope.definitions.get(name):
                scope.reference(name)
                return state
        else:
            return None

    def reference(self, name):
        self.reference_counts[name] += 1

    def define(self, name, state):
        self.definitions[name] = state.freeze()

    def exit(self):
        for definition in self.definitions:
            if self.reference_counts[definition] < 1:
                raise ReizQLSyntaxError(f"Unused reference: {definition!r}")

        if len(self.parents) >= 1:
            return self.parents[-1]
