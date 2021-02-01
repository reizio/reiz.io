import ast
import json
import textwrap
from dataclasses import dataclass, field
from typing import List, Optional

import pyasdl
from pyasdl import FieldQualifier

from reiz.schema.builders.base import BaseSchemaGenerator
from reiz.schema.edgeql import EQLSchema as Schema
from reiz.utilities import ReizEnum

INDENT = " " * 4


class ModelConstraint(str, ReizEnum):
    SCALAR = "scalar"
    ABSTRACT = "abstract"


class FieldConstraint(str, ReizEnum):
    MULTI = "multi"
    REQUIRED = "required"


@dataclass
class Field:
    name: str
    kind: str
    constraint: Optional[FieldConstraint] = None
    is_property: bool = False
    is_unique: bool = False

    def construct(self):
        source = []
        if self.constraint:
            source.append(self.constraint)
        source.append("property" if self.is_property else "link")
        source.append(Schema.wrap(self.name, with_prefix=False))
        source.append("->")
        source.append(Schema.wrap(self.kind, with_prefix=False))

        declaration = " ".join(source)
        if self.is_ordered_sequence or self.is_unique:
            declaration += f" {{\n{INDENT * 2}"
            if self.is_ordered_sequence:
                declaration += Field(
                    "index", "int64", is_property=True
                ).construct()
            elif self.is_unique:
                declaration += "constraint exclusive;"
            declaration += f"\n{INDENT}}}"

        return declaration + ";"

    @property
    def is_ordered_sequence(self):
        return (
            self.constraint is FieldConstraint.MULTI
        ) and not self.is_property


@dataclass
class Model:
    model: str
    fields: List[Field] = field(default_factory=list)
    constraint: Optional[ModelConstraint] = None
    extending: List[str] = field(default_factory=list)

    @classmethod
    def enum(cls, name, members):
        # We can't directly use ident-based enums since
        # some are the members (like And, Or) are keywords
        base = "enum"
        base += "<"
        base += ", ".join(repr(member) for member in members)
        base += ">"
        return cls(name, constraint=ModelConstraint.SCALAR, extending=[base])

    def construct(self):
        source = []

        line = f"type {Schema.wrap(self.model, with_prefix=False)}"
        if self.constraint:
            line = f"{self.constraint} {line}"
        if self.extending:
            line += " extending "
            line += ", ".join(self.extending)
        line += " {"

        source.append(line)
        source.extend(INDENT + field.construct() for field in self.fields)
        if len(source) >= 2:
            source.append("}")
        else:
            source[-1] += "}"
        return "\n".join(source)


class EQLSchemaGenerator(pyasdl.ASDLVisitor, BaseSchemaGenerator):

    TYPE_MAP = {
        "int": "int64",
        "string": "str",
        "constant": "str",
        "identifier": "str",
    }

    QUALIFIER_MAP = {
        None: FieldConstraint.REQUIRED,
        FieldQualifier.SEQUENCE: FieldConstraint.MULTI,
    }

    def __init__(self, schema):
        self.schema = schema
        self.enum_types = schema.setdefault("enum_types", [])
        self.module_types = schema.setdefault("module_annotated_types", [])

    def visit_Module(self, node):
        yield Model(self.BASE_TYPE, constraint=ModelConstraint.ABSTRACT)

        definitions = []
        for definition in node.body:
            definitions.extend(self.visit(definition))
        yield from self.fix_references(definitions)

    def fix_references(self, definitions):
        for definition in definitions:
            for field in definition.fields:
                if field.kind == "Module":
                    self.module_types.append(definition.model)
                if field.kind in self.enum_types:
                    field.is_property = True
                if (
                    f"{definition.model}.{field.name}"
                    in self.schema["unique_fields"]
                ):
                    field.is_unique = True

            yield definition

    def visit_Type(self, node):
        yield from self.visit(node.value, name=node.name)

    def visit_Product(self, node, name):
        yield Model(
            name,
            fields=self.visit_all(node.fields)
            + self.visit_all(node.attributes),
        )

    def visit_Sum(self, node, name):
        if pyasdl.is_simple_sum(node):
            self.enum_types.append(name)
            yield Model.enum(
                name, members=[constructor.name for constructor in node.types]
            )
        else:
            yield Model(
                name, self.visit_all(node.attributes), ModelConstraint.ABSTRACT
            )
            yield from self.visit_all(node.types, base=name)

    def visit_Constructor(self, node, base):
        return Model(
            node.name,
            self.visit_all(node.fields),
            extending=[base, self.BASE_TYPE],
        )

    def visit_Field(self, node):
        is_property = False
        if kind := self.TYPE_MAP.get(node.kind):
            is_property = True

        return Field(
            node.name,
            kind or node.kind,
            self.QUALIFIER_MAP.get(node.qualifier),
            is_property=is_property,
        )


def generate_schema(input_file, output_file, schema_file):
    with open(input_file) as stream:
        source = stream.read()

    schema = {}
    for comment in pyasdl.fetch_comments(source):
        tag, _, value = comment.strip().partition(": ")
        if tag in BaseSchemaGenerator.SCHEMA_FIELDS:
            schema[tag] = ast.literal_eval(value)

    tree = pyasdl.parse(source)
    schema_generator = EQLSchemaGenerator(schema)
    declarations = "\n".join(
        definition.construct() for definition in schema_generator.visit(tree)
    )
    with open(output_file, "w") as stream:
        stream.write("START MIGRATION TO {\n")
        stream.write(f"{INDENT}module ast {{\n")
        stream.write(textwrap.indent(declarations, INDENT * 2))
        stream.write(f"\n{INDENT}}}")
        stream.write("\n};\n")

    schema["enum_types"] = schema_generator.enum_types
    # Check whether all fields are satisified for the
    # schema_file, and raise a SchemaError if there are
    # missing fields
    with open(schema_file, "w") as stream:
        json.dump(schema, stream)
