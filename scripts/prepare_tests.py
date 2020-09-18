#!/usr/bin/env python

from argparse import ArgumentParser
from pathlib import Path

from reiz.ql.query import generate_edgeql, parse_query

GENERATED_SOURCE_SIGN = "# GENERATED-CODE"


def append_test_matrixes(source):
    for rzql_file in source.glob("**/*.rzql"):
        source = []
        for line in rzql_file.read_text().splitlines():
            if line == GENERATED_SOURCE_SIGN:
                break
            else:
                source.append(line)

        ql_ast = parse_query("\n".join(source))
        source.append(GENERATED_SOURCE_SIGN)
        source.append(generate_edgeql(ql_ast).construct())
        rzql_file.write_text("\n".join(source))


def main():
    parser = ArgumentParser()
    parser.add_argument("source", type=Path)
    options = parser.parse_args()
    append_test_matrixes(**vars(options))


if __name__ == "__main__":
    main()
