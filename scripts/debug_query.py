#!/usr/bin/env python
from argparse import ArgumentParser, FileType
from pprint import pprint

from reiz.edgeql import as_edgeql
from reiz.reizql import compile_edgeql, parse_query


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "source",
        type=FileType(mode="rb"),
        nargs="?",
        default="-",
        help="the file to parse; defaults to stdin",
    )
    options = parser.parse_args()
    with options.source:
        query = parse_query(options.source.read())
        pprint(query)
        edgeql = compile_edgeql(query)
        print(as_edgeql(edgeql))


if __name__ == "__main__":
    main()
