import textwrap
from argparse import ArgumentParser
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

import pyasdl

from reiz.db.schema import protected_name

DEFAULT_INDENT = " " * 4
EDGEQL_BASICS = {
    "int": "int64",
    "string": "str",
    "identifier": "str",
    "constant": "str",
}

UNIQUE_FIELDS = ["filename"]


class FieldConstraint(Enum):
    MULTI = "multi"
    REQUIRED = "required"


class ModelConstraint(Enum):
    SCALAR = "scalar"
    ABSTRACT = "abstract"


@dataclass
class QLField:
    name: str
    qualifier: str
    constraint: Optional[FieldConstraint]
    is_property: Optional[bool] = None
    is_unique: Optional[bool] = None

    def __post_init__(self):
        if self.is_property is None:
            self.is_property = self.qualifier in EDGEQL_BASICS
        if self.is_unique is None:
            self.is_unique = self.name in UNIQUE_FIELDS

    def __str__(self):
        properties = []
        if self.constraint is not None:
            properties.append(self.constraint.value)

        if self.is_property:
            properties.append("property")
        else:
            properties.append("link")

        properties.append(protected_name(self.name, prefix=False))
        properties.append("->")
        properties.append(self.type)
        if self.is_unique:
            properties.append("{")
            properties.append("\n" + DEFAULT_INDENT * 2 + "constraint")
            properties.append("exclusive;")
            properties.append("\n" + DEFAULT_INDENT + "}")
        return " ".join(properties) + ";"

    @property
    def type(self):
        if self.qualifier in EDGEQL_BASICS:
            return EDGEQL_BASICS[self.qualifier]
        else:
            return protected_name(self.qualifier, prefix=False)


@dataclass
class QLModel:
    name: str
    fields: List[QLField] = field(default_factory=list)
    extending: Optional[str] = None
    constraint: Optional[ModelConstraint] = None

    def __str__(self):
        lines = []
        lines.append(f"type {protected_name(self.name, prefix=False)}")
        if self.constraint is not None:
            lines[-1] = self.constraint.value + " " + lines[-1]
        if self.extending is not None:
            lines[-1] += " extending " + self.extending
            if "enum" not in self.extending:
                lines[-1] += ", AST"

        lines[-1] += " " + "{"
        lines.extend(DEFAULT_INDENT + str(field) for field in self.fields)
        if len(lines) == 1:
            lines[-1] += "}"
        else:
            lines.append("}")
        return "\n".join(lines)


def is_simple(sum_t: pyasdl.Sum) -> bool:
    for constructor in sum_t.types:
        if constructor.fields is not None:
            return False
    else:
        return True


def as_enum(names):
    return "enum" + "<" + ", ".join(repr(name) for name in names) + ">"


class GraphQLGenerator(pyasdl.ASDLVisitor):
    def visit_Module(self, node):
        self.enums = set()
        definitions = [QLModel("AST", constraint=ModelConstraint.ABSTRACT)]
        for definition in node.body:
            definitions.extend(self.visit(definition))
        yield from self.fix_references(definitions)

    def fix_references(self, definitions):
        for definition in definitions:
            for field in definition.fields:
                if field.qualifier in self.enums:
                    field.is_property = True
            yield definition

    def visit_Type(self, node):
        # FIX-ME: attributes are ignored, need a better way
        # for storing location information
        yield from self.visit(node.value, name=node.name)

    def visit_Product(self, node, name):
        yield QLModel(
            name, self.visit_all(node.fields) + self.visit_all(node.attributes)
        )

    def visit_Sum(self, node, name):
        constructor_names = [constructor.name for constructor in node.types]
        if is_simple(node):
            self.enums.add(name)
            yield QLModel(
                name,
                constraint=ModelConstraint.SCALAR,
                extending=as_enum(
                    constructor.name for constructor in node.types
                ),
            )
        else:
            yield QLModel(
                name,
                self.visit_all(node.attributes),
                constraint=ModelConstraint.ABSTRACT,
            )
            yield from self.visit_all(node.types, extending=name)

    def visit_Constructor(self, node, extending):
        return QLModel(
            node.name, self.visit_all(node.fields or ()), extending=extending
        )

    def visit_Field(self, node):
        qualifier = FieldConstraint.REQUIRED
        if node.qualifier is pyasdl.FieldQualifier.SEQUENCE:
            qualifier = FieldConstraint.MULTI
        elif node.qualifier is pyasdl.FieldQualifier.OPTIONAL:
            qualifier = None
        return QLField(node.name, node.kind, qualifier)


def main():
    parser = ArgumentParser()
    parser.add_argument("file", type=Path)

    options = parser.parse_args()
    with open(options.file) as source:
        tree = pyasdl.parse(source.read())

    visitor = GraphQLGenerator()
    print("START MIGRATION TO {")
    print(DEFAULT_INDENT + "module ast {")
    for ql_type in visitor.visit(tree):
        print(textwrap.indent(str(ql_type), DEFAULT_INDENT * 2))
    print(DEFAULT_INDENT + "}")
    print("};")


if __name__ == "__main__":
    main()
