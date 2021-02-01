from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List

from reiz.ir import IR
from reiz.reizql.parser import grammar

if TYPE_CHECKING:
    BuiltinFunctionType = Callable[
        [grammar.Expression, CompilerState, SimpleNamespace], IR
    ]


@dataclass
class Signature:
    name: str
    func: BuiltinFunctionType
    params: List[str] = field(default_factory=set)
    defaults: Dict[str, Any] = field(default_factory=list)

    _FUNCTIONS: ClassVar[Dict[str, BuiltinFunctionType]] = {}

    @classmethod
    def register(cls, name, *args, **kwargs):
        def wrapper(func):
            cls._FUNCTIONS[name] = cls(name, func, *args, **kwargs)
            return func

        return wrapper

    @classmethod
    def get_function(cls, name):
        return cls._FUNCTIONS.get(name)

    def codegen(self, node, state):
        return self.func(node, state, self.bind(node, state))

    def bind(self, node, state):
        bound_args = {}
        params = self.params.copy()
        for argument in node.args:
            state.ensure(node, params)
            bound_args[params.pop(0)] = argument

        for keyword, value in node.keywords.items():
            state.ensure(node, keyword in params)
            params.remove(keyword)
            bound_args[keyword] = value

        for param in params.copy():
            state.ensure(node, param in self.defaults)
            bound_args[param] = self.defaults[param]

        return SimpleNamespace(**bound_args)


@Signature.register("I", ["match_str"])
def convert_intensive(node, state, arguments):
    match_str = arguments.match_str
    state.ensure(node, isinstance(match_str, grammar.MatchString))
    return IR.filter(
        state.compute_path(), IR.literal(match_str.value), "ILIKE"
    )


@Signature.register("ALL", ["value"])
@Signature.register("ANY", ["value"])
def convert_all_any(node, state, arguments):
    return IR.call(node.name.lower(), [state.codegen(arguments.value)])


@Signature.register("LEN", ["min", "max"], {"min": None, "max": None})
def convert_length(node, state, arguments):
    state.ensure(node, any((arguments.min, arguments.max)))

    count = IR.call("count", [state.compute_path()])
    filters = None
    for value, operator in [
        (arguments.min, IR.as_operator(">=")),
        (arguments.max, IR.as_operator("<=")),
    ]:
        if value is None:
            continue

        state.ensure(value, isinstance(value, grammar.Constant))
        state.ensure(value, isinstance(value.value, int))
        filters = IR.combine_filters(
            filters, IR.filter(count, IR.literal(value.value), operator)
        )

    assert filters is not None
    return filters
