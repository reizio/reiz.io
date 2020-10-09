#!/usr/bin/env python
import timeit
from argparse import ArgumentParser, FileType

from reiz.db.connection import connect
from reiz.utilities import get_db_settings


def run_raw_edgeql(query, times):
    with connect(**get_db_settings()) as connection:
        return timeit.timeit(
            "connection.query(query)", number=times, globals=locals()
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
    parser.add_argument("--times", type=int, default=5)
    options = parser.parse_args()
    with options.source:
        total_time = run_raw_edgeql(options.source.read(), times=options.times)
        per_iteration_time = total_time / options.times
        print(
            options.times,
            "took total of",
            f"{total_time} seconds",
            "with an average of",
            f"{per_iteration_time} seconds",
        )


if __name__ == "__main__":
    main()
