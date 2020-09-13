import ast
import json
import random
import secrets
import sys
import tokenize
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

import edgedb

from reiz.utilities import logger, read_config

sys.setrecursionlimit(1000000)
DEF_DSN = "edgedb://edgedb@localhost/asttests"
ENUMERATIONS = (
    ast.expr_context,
    ast.boolop,
    ast.operator,
    ast.unaryop,
    ast.cmpop,
)
RESERVED_NAMES = frozenset(
    (
        "Module",
        "Delete",
        "For",
        "If",
        "With",
        "Raise",
        "Import",
        "module",
        "Global",
        "Set",
        "id",
    )
)
MODULE_CACHE = frozenset()


def protected_name(name, prefix=True):
    if name in RESERVED_NAMES:
        if name.istitle():
            name = "Py" + name
        else:
            name = "py_" + name

    if prefix:
        name = "ast::" + name
    return name


class Prepared(NamedTuple):
    value: str


class Insertion(NamedTuple):
    name: str
    fields: Dict[str, Any]

    def __str__(self):
        insertion = f"INSERT {self.name}"
        if self.fields:
            insertion += f" {{{','.join(f'{key} := {value}' for key, value in self.fields.items())}}}"
        return insertion


class Selection(NamedTuple):
    model: str
    filters: Dict[str, Any]
    limit: Optional[int] = 0

    def __str__(self):
        query = f"SELECT {self.model} FILTER {' ,'.join(f'.{key} = {value}' for key, value in self.filters.items())}"
        if self.limit is not None:
            query += f" LIMIT {self.limit}"
        return query


def with_parens(node, combo="()"):
    left, right = combo
    return f"{left}{node!s}{right}"


def infer_type(child):
    child_t = type(child)
    if child_t.__base__ is not ast.AST:
        return child_t.__base__
    else:
        return child_t


def convert(child, connection):
    if isinstance(child, ast.AST):
        if isinstance(child, ENUMERATIONS):
            return f"<{protected_name(type(child).__base__.__name__)}>'{protected_name(type(child).__name__, prefix=False)}'"
        else:
            return with_parens(
                Selection(
                    protected_name(infer_type(child).__name__),
                    {"id": "<uuid>" + repr(str(insert(child, connection).id))},
                    limit=1,
                )
            )
    elif isinstance(child, list):
        return with_parens(
            ", ".join(convert(value, connection) for value in child), "{}"
        )
    elif isinstance(child, (int, str)):
        return repr(child)
    elif isinstance(child, Prepared):
        return child.value
    elif child is None:
        return None
    else:
        raise ValueError(f"Unexpected type: {child}")


def get_attributes(node):
    def extra_attrs(node):
        if issubclass(type(node), ast.slice):
            return ["sentinel"]
        else:
            return []

    for attribute in (*node._attributes, *extra_attrs(node)):
        yield attribute, getattr(node, attribute, 0)


def insert(node, connection, **extras):
    name = protected_name(type(node).__name__)
    fields = {**extras, **dict(get_attributes(node))}
    for field, child in ast.iter_fields(node):
        # FIX-ME: no-any type, so get the repr of the value
        if field == "value" and isinstance(node, ast.Constant):
            child = str(child)
        # FIX-ME: {**d} doesn't work
        elif field == "keys" and isinstance(node, ast.Dict):
            child = [key for key in child if key is not None]

        if conversion := convert(child, connection):
            fields[protected_name(field, prefix=False)] = conversion
    query = str(Insertion(name, fields))
    return connection.query_one(query)


def inject_project(directory: Path, **db_opt):
    with closing(edgedb.connect(**db_opt)) as connection:
        for module in directory.glob("**/*.py"):
            if str(module) in MODULE_CACHE:
                logger.debug("file %s already inserted", module)
                continue
            try:
                with connection.transaction():
                    with tokenize.open(module) as file:
                        tree = ast.parse(file.read())
                    insert(tree, connection, filename=repr(str(module)))
                    logger.debug("file %s extraction completed", module)
            except:
                logger.exception("file %s couldn't inserted", module)

    return directory.name


def set_cache(**db_opts):
    global MODULE_CACHE
    with closing(edgedb.connect(**db_opts)) as connection:
        MODULE_CACHE = frozenset(
            module.filename
            for module in connection.query(
                f"SELECT {protected_name('Module')} {{ filename }}"
            )
        )
    return MODULE_CACHE


def multi_inject(data_dir, workers, **kwargs):
    initial_size = len(set_cache(**kwargs))
    projects = read_config(data_dir / "info.json")
    random.shuffle(projects)

    with ProcessPoolExecutor(max_workers=workers) as executor:
        bound_injector = partial(inject_project, **kwargs)
        for project in executor.map(
            bound_injector, map(data_dir.joinpath, projects)
        ):
            logger.debug("project %r inserted", project)

    current_size = len(set_cache(**kwargs))
    logger.info(
        "%d modules inserted (in total of %d)",
        initial_size - current_size,
        current_size,
    )


def single_inject(data_dir, workers, **db_opts):
    assert data_dir.is_file()
    with tokenize.open(data_dir) as file:
        tree = ast.parse(file.read())
    with closing(edgedb.connect(**db_opts)) as connection:
        _query_one = connection.query_one

        def query_one(query, *args, **kwargs):
            logger.debug("query: %r", query)
            return _query_one(query, *args, **kwargs)

        connection.query_one = query_one
        filename = data_dir.with_name(secrets.token_hex() + ".py")
        insert(tree, connection, filename=repr(str(filename)))


def main():
    parser = ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--single", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--dsn", type=str, default=DEF_DSN)
    options = vars(parser.parse_args())
    if options.pop("single"):
        injector = single_inject
    else:
        injector = multi_inject

    injector(**options)


if __name__ == "__main__":
    main()
