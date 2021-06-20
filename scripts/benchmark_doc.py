#!/usr/bin/env python
import statistics
import time
from argparse import ArgumentParser
from collections import defaultdict

from reiz.database import get_new_connection
from reiz.fetch import run_query_on_connection

PRECISION = 6

queries = [
    'Call(Name("len"))',
    "BinOp(op=Add() | Sub())",
    'FunctionDef(f"run_%", returns = not None)',
    "BinOp(left=Constant(), right=Constant())",
    "Try(handlers=LEN(min=3, max=5))",
    "ClassDef(body=[Assign(), *..., FunctionDef()])",
]


def run_benchmarks(query, repeat=5):
    results = defaultdict(list)
    with get_new_connection() as connection:
        for query in queries:
            for _ in range(repeat):
                start = time.perf_counter()
                run_query_on_connection(connection, query)
                results[query].append(time.perf_counter() - start)

    return {
        key: round(statistics.fmean(val), PRECISION)
        for key, val in results.items()
    }


def make_field(*items):
    return "|" + "|".join(items) + "|"


def display(results):
    results = sorted(results.items(), key=lambda query: len(query[0]))
    padding = len(results[-1][0]) + 4
    time_padding = PRECISION + 2
    print(make_field("query".ljust(padding), "timing".ljust(time_padding)))
    print(make_field("-" * padding, "-" * time_padding))
    for query, result in results:
        print(
            make_field(
                f"`{query}`".ljust(padding), str(result).ljust(time_padding)
            )
        )


def main():
    parser = ArgumentParser()
    parser.add_argument("--repeat", type=int, default=5)

    options = parser.parse_args()
    display(run_benchmarks(queries, repeat=options.repeat))


if __name__ == "__main__":
    main()
