from __future__ import annotations

from dataclasses import dataclass, field
from typing import Counter, Dict, List, Tuple

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
    definitions: Dict[str, Tuple[Scope, CompilerState]] = field(
        default_factory=dict
    )
    reference_counts: Counter[str] = field(default_factory=Counter)

    @classmethod
    def from_parent(cls, parent):
        return cls(
            parents=parent.parents + [parent], definitions=parent.definitions
        )

    def lookup(self, name):
        if name not in self.definitions:
            return None

        scope, state = self.definitions[name]
        scope.reference(name)
        state.set_flag("linear access", scope not in self.parents + [self])
        return state

    def reference(self, name):
        self.reference_counts[name] += 1

    def define(self, name, state):
        self.definitions[name] = (self, state)

    def exit(self):
        if len(self.parents) >= 1:
            return self.parents[-1]
        else:
            self.verify()

    def verify(self):
        for definition, (scope, _) in self.definitions.items():
            if scope.reference_counts[definition] < 1:
                raise ReizQLSyntaxError(f"unused reference: {definition!r}")
