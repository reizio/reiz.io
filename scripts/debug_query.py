#!/usr/bin/env python
from argparse import ArgumentParser, FileType

from reiz.ir import IR
from reiz.reizql import compile_to_ir, parse_query
from reiz.utilities import pprint


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

        ir = compile_to_ir(query)
        print(IR.construct(ir, top_level=True))


if __name__ == "__main__":
    main()
