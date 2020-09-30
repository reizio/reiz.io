#!/usr/bin/env python

import ast
import functools
import random
from argparse import ArgumentParser
from collections import defaultdict, namedtuple
from pathlib import Path

import pyasdl

NODE_DB = defaultdict(dict)


def unparse(value):
    if isinstance(value, Node):
        return value.unparse()
    elif isinstance(value, list):
        return [unparse(item) for item in value]
    elif value is None:
        return value
    else:
        raise ValueError(f"Unexpected value: {value}")


class Node(namedtuple("_Node", "kind fields")):
    def unparse(self):
        base = self.kind.__name__
        base += "("
        base += ", ".join(
            f"{key}={unparse(value)}" for key, value in self.fields.items()
        )
        base += ")"
        return base

    def __bool__(self):
        return bool(self.fields)


def load_asdl_map(source):
    tree = pyasdl.parse(source)
    for node_type in tree.body:
        ast_node_type = getattr(ast, node_type.name)

        if isinstance(node_type.value, pyasdl.Sum):
            for constructor in node_type.value.types:
                if not hasattr(ast, constructor.name):
                    continue
                ast_constructor_type = getattr(ast, constructor.name)
                NODE_DB[ast_node_type][ast_constructor_type] = (
                    constructor.fields or []
                )
        else:
            ...  # FIX-ME(medium): awaiting support for position-less nodes.


def random_subclasses(kind, number):
    options = tuple(NODE_DB[kind].keys())
    if len(options) == 0:
        options = (kind,)
    yield from random.choices(options, k=number)


def random_subclass(kind):
    return next(random_subclasses(kind, 1))


def generate_node(node_type, level=0):
    try:
        node_fields = NODE_DB[node_type.__base__][node_type]
    except KeyError:
        node_fields = ()

    fields = {}
    if level >= random.randint(level, 5):
        return Node(node_type, fields)
    else:
        level += 1
        fetch = functools.partial(generate_node, level=level)

    for field in node_fields:
        if not (base := getattr(ast, field.kind, None)):
            continue

        if field.qualifier is pyasdl.FieldQualifier.SEQUENCE:
            result = [
                node
                for sub_node_type in random_subclasses(
                    base, random.randint(0, 4)
                )
                if (node := fetch(sub_node_type))
            ]
        elif (
            field.qualifier is pyasdl.FieldQualifier.OPTIONAL
            and random.randint(0, 4) == 2
        ):
            # FIX-ME(high): handle optionals in ReizQL
            fields[field.name] = None
        else:
            result = generate_node(random_subclass(base), level=level)
        fields[field.name] = result

    return Node(node_type, fields)


def main():
    parser = ArgumentParser()
    parser.add_argument("asdl_file", type=Path)
    options = parser.parse_args()
    load_asdl_map(options.asdl_file.read_text())
    print(unparse(generate_node(random_subclass(ast.expr))))


if __name__ == "__main__":
    main()
