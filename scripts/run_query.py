#!/usr/bin/env python
import ast
from argparse import ArgumentParser, FileType

from reiz.db.connection import DEFAULT_DSN, DEFAULT_TABLE, connect
from reiz.edgeql import EdgeQLSelector, construct
from reiz.reizql import compile_edgeql, parse_query
from reiz.utilities import logger


class LocationNode(ast.AST):
    _attributes = ("lineno", "col_offset", "end_lineno", "end_col_offset")


def fetch(filename, **loc_data):
    loc_node = LocationNode(**loc_data)
    with open(filename) as file:
        source = file.read()
    return ast.get_source_segment(source, loc_node)


def query(source, limit=10, show_source=True, **db_opts):
    with connect(**db_opts) as conn:
        tree = parse_query(source)
        logger.info("ReizQL Tree: %r", tree)

        selection = compile_edgeql(tree)
        selection.limit = limit
        selection.selections = [
            EdgeQLSelector("lineno"),
            EdgeQLSelector("col_offset"),
            EdgeQLSelector("end_lineno"),
            EdgeQLSelector("end_col_offset"),
            EdgeQLSelector("_module", [EdgeQLSelector("filename")]),
        ]

        query = construct(selection, top_level=True)
        logger.info("EdgeQL query: %r", query)

        for result in conn.query(query):
            print(
                result._module.filename
                + ":"
                + str(result.lineno)
                + ":"
                + str(result.col_offset)
            )
            if show_source:
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
    parser.add_argument(
        "--no-source", default=True, dest="show_source", action="store_false"
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--table", default=DEFAULT_TABLE)
    options = parser.parse_args()
    with options.source:
        query(
            options.source.read(),
            show_source=options.show_source,
            limit=options.limit,
            dsn=options.dsn,
            table=options.table,
        )


if __name__ == "__main__":
    main()
