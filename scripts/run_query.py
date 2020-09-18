#!/usr/bin/env python
import ast
from argparse import ArgumentParser, FileType

from reiz.db.connection import DEFAULT_DSN, DEFAULT_TABLE, connect
from reiz.ql.query import generate_edgeql, parse_query


class LocationNode(ast.AST):
    _attributes = ("lineno", "col_offset", "end_lineno", "end_col_offset")


def fetch(filename, **loc_data):
    loc_node = LocationNode(**loc_data)
    with open(filename) as file:
        source = file.read()
    return ast.get_source_segment(source, loc_node)


def query(source, limit=10, **db_opts):
    with connect(**db_opts) as conn:
        tree = parse_query(source)
        print(tree)
        selection = generate_edgeql(
            tree,
            [
                "lineno",
                "col_offset",
                "end_lineno",
                "end_col_offset",
                "_module: {filename}",
            ],
        )
        selection.limit = limit
        query = selection.construct()
        print(query)
        for result in conn.query(query):
            print(
                result._module.filename
                + ":"
                + str(result.lineno)
                + ":"
                + str(result.col_offset)
            )
            print(
                fetch(
                    result._module.filename,
                    lineno=result.lineno,
                    col_offset=result.col_offset,
                    end_lineno=result.end_lineno,
                    end_col_offset=result.end_col_offset,
                )
            )


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "source",
        type=FileType(mode="rb"),
        nargs="?",
        default="-",
        help="the file to parse; defaults to stdin",
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--table", default=DEFAULT_TABLE)
    options = parser.parse_args()
    with options.source:
        query(
            options.source.read(),
            limit=options.limit,
            dsn=options.dsn,
            table=options.table,
        )


if __name__ == "__main__":
    main()
