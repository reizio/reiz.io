#!/usr/bin/env python

import json
from argparse import ArgumentParser, FileType
from collections import defaultdict

import pyasdl


class FieldDBGenerator(pyasdl.ASDLVisitor):
    def visit_Module(self, node):
        layout = defaultdict(dict)
        for definition in node.body:
            self.visit(definition.value, definition.name, layout)
        return layout

    def visit_Product(self, node, name, layout):
        for field, value in self.visit_all(node.fields + node.attributes):
            layout[name][field] = value

    def visit_Sum(self, node, name, layout):
        for attr, value in self.visit_all(node.attributes):
            layout[attr] = value
        self.visit_all(node.types, layout)

    def visit_Constructor(self, node, layout):
        layout[node.name] = dict(self.visit_all(node.fields or ()))

    def visit_Field(self, node):
        qualifier = "REQUIRED"
        if node.qualifier is pyasdl.FieldQualifier.SEQUENCE:
            qualifier = "SEQUENCE"
        elif node.qualifier is pyasdl.FieldQualifier.OPTIONAL:
            qualifier = None
        return node.name, (node.kind, qualifier)


def main():
    parser = ArgumentParser()
    parser.add_argument("file", type=FileType())

    options = parser.parse_args()
    with options.file as source:
        tree = pyasdl.parse(source.read())

    visitor = FieldDBGenerator()
    layout = visitor.visit(tree)
    print(json.dumps(layout, indent=4))


if __name__ == "__main__":
    main()
