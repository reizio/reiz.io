import json
from collections import namedtuple

from reiz.serialization.transformers import ast
from reiz.utilities import STATIC_DIR, ReizEnum


class UnknownType:
    def __init__(self, kind):
        self.kind = kind


class Constraint(ReizEnum):
    REQUIRED = "REQUIRED"
    SEQUENCE = "SEQUENCE"


Field = namedtuple("Field", "name type constraint")


def unpack_fields(definition):
    for name, field_pack in definition.copy().items():
        if not isinstance(field_pack, list):
            continue

        kind, constraint = field_pack
        if constraint is not None:
            constraint = Constraint(constraint)

        if kind in ("string", "identifier"):
            kind = str
        elif kind == "int":
            kind = int
        elif hasattr(ast, kind):
            kind = getattr(ast, kind)
        else:
            kind = UnknownType(kind)

        definition[name] = Field(name, kind, constraint)
    return definition


with open(STATIC_DIR / "Python-reiz-fielddb.json") as stream:
    FIELD_DB = json.load(stream, object_hook=unpack_fields)
