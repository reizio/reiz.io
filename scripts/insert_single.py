#!/usr/bin/env python

import logging
from argparse import ArgumentParser

from reiz.db.connection import simple_connection
from reiz.serialization.serializer import insert_file
from reiz.utilities import logger


# FIX-ME(medium): Collect more stats (such as total
# execution time, cpu usage, disk usage etc.)
def insert_single(file, show_queries=False):
    total_queries = 0
    if show_queries:
        logger.setLevel(logging.TRACE)

    with simple_connection() as connection:
        original_query_one = connection.query_one

        def query_one_with_stats(*args, **kwargs):
            nonlocal total_queries
            total_queries += 1
            return original_query_one(*args, **kwargs)

        connection.query_one = query_one_with_stats
        insert_file(connection, file)
    print(f"Total {total_queries} performed!")


def main():
    parser = ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--show-queries", action="store_true")
    options = parser.parse_args()
    insert_single(**vars(options))


if __name__ == "__main__":
    main()
