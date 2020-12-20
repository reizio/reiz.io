#!/usr/bin/env python
from argparse import ArgumentParser, FileType
from pprint import pprint

from reiz.fetch import DEFAULT_LIMIT, run_query


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "source",
        type=FileType(mode="rb"),
        nargs="?",
        default="-",
        help="the file to parse; defaults to stdin",
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    options = parser.parse_args()
    with options.source:
        pprint(
            run_query(
                options.source.read(),
                limit=options.limit,
            )
        )


if __name__ == "__main__":
    main()
