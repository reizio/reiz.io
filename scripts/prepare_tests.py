#!/usr/bin/env python

from argparse import ArgumentParser
from pathlib import Path

from reiz.ql.query import generate_edgeql, parse_query

GENERATED_CODE_SYMBOL = "# GENERATED-CODE"


def display(results, verbose=False):
    for test_name, (generated, expected) in results.items():
        success = generated == expected
        if verbose or not success:
            print(f"{test_name:45} ==>", "passed" if success else "failed")


def append_test_matrixes(source, update=False, verbose=False):
    results = {}
    for rzql_file in source.glob("**/*.rzql"):
        source_lines = rzql_file.read_text().splitlines()
        if (
            len(source_lines) >= 2
            and source_lines[-2] == GENERATED_CODE_SYMBOL
        ):
            source = source_lines[:-2]
            expected = source_lines[-1]
        else:
            source = source_lines
            if not update:
                raise ValueError(
                    f"{rzql_file.stem} is an incomplete test, please first run with --update flag"
                )

        ql_ast = parse_query("\n".join(source))
        reizql = generate_edgeql(ql_ast).construct()

        if update:
            updated_test = source + [GENERATED_CODE_SYMBOL, reizql]
            rzql_file.write_text("\n".join(updated_test))
        else:
            results[rzql_file.stem] = [reizql, expected]

    if not update:
        display(results, verbose=verbose)


# FIX-ME(medium): exit with 1 on fail
def main():
    parser = ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    options = parser.parse_args()
    append_test_matrixes(**vars(options))


if __name__ == "__main__":
    main()
