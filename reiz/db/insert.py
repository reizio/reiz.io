import ast
import json
import sys
import tokenize
import traceback
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

import edgedb

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


def protected_name(name, prefix=True):
    if name in RESERVED_NAMES:
        if name.istitle():
            name = "Py" + name
        else:
            name = "py_" + name

    if prefix:
        name = "ast::" + name
    return name


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
    elif child is None:
        return None
    else:
        raise ValueError(f"Unexpected type: {child}")


def insert(node, connection, **extras):
    name = protected_name(type(node).__name__)
    fields = {**extras}
    for field, child in ast.iter_fields(node):
        if field == "value" and isinstance(node, ast.Constant):
            child = str(child)
        if conversion := convert(child, connection):
            fields[protected_name(field, prefix=False)] = conversion
    query = str(Insertion(name, fields))
    return connection.query_one(query)


def inject_project(directory: Path, **db_opt):
    with closing(edgedb.connect(**db_opt)) as connection:
        for module in directory.glob("**/*.py"):
            try:
                with connection.transaction():
                    with tokenize.open(module) as file:
                        tree = ast.parse(file.read())
                    insert(tree, connection, filename=repr(str(module)))
                    print(f"{module} inserted...")
            except:
                traceback.print_exc()

    return directory.name


def read_config(directory: Path, config: str) -> List[str]:
    if (pkg_config := (directory / config).with_suffix(".json")).exists():
        with open(pkg_config) as config:
            cache = json.load(config)
        return cache
    else:
        return []


def write_config(directory: Path, config: str, data: Any):
    with open((directory / config).with_suffix(".json"), "w") as config:
        json.dump(data, config)


def inject(data_dir, workers, **kwargs):
    origin = read_config(data_dir, "db")
    projects = set(read_config(data_dir, "info")).difference(origin)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        bound_injector = partial(inject_project, **kwargs)
        for project in executor.map(
            bound_injector, map(data_dir.joinpath, projects)
        ):
            origin.append(project)
    write_config(data_dir, "db", origin)


def main():
    parser = ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--dsn", type=str, default=DEF_DSN)
    options = parser.parse_args()
    inject(**vars(options))


if __name__ == "__main__":
    main()
