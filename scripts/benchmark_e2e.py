#!/usr/bin/env python
import json
import statistics
import timeit
from argparse import ArgumentParser
from dataclasses import asdict, dataclass, field, replace
from typing import List, Optional

from reiz.fetch import DEFAULT_LIMIT, run_query

RUNNER_SCRIPT = "run_query(query, limit=limit)"

THRESHOLD = 1 / 10


@dataclass
class Benchmark:
    query: str
    tries: int = 3
    limit: int = DEFAULT_LIMIT
    performance: Optional[float] = field(default=None, compare=False)
    performances: List[float] = field(default_factory=list, compare=False)

    def execute(self):
        environ = {
            "query": self.query,
            "limit": self.limit,
            "run_query": run_query,
        }
        performances = timeit.repeat(
            RUNNER_SCRIPT, globals=environ, repeat=self.tries, number=1
        )
        return replace(
            self,
            performance=statistics.mean(performances),
            performances=performances,
        )


def load_file(file):
    with open(file) as file_p:
        return [Benchmark(**result) for result in json.load(file_p)]


def action_run(benchmarks_file, output_file):
    results = []
    for benchmark in load_file(benchmarks_file):
        results.append(asdict(benchmark.execute()))
    with open(output_file, "w") as file:
        json.dump(results, file)


def action_show(output_file):
    for benchmark in load_file(output_file):
        print(f"{benchmark.query:110} => {benchmark.performance}")


def action_compare(old_file, new_file):
    benchmarks1, benchmarks2 = load_file(old_file), load_file(new_file)
    for benchmark1, benchmark2 in zip(benchmarks1, benchmarks2):
        assert benchmark1 == benchmark2
        result = benchmark1.performance / benchmark2.performance
        if result < 1 - THRESHOLD:
            status = "slower"
        elif result > 1 + THRESHOLD:
            status = "faster"
        else:
            print(f"{benchmark1.query:110} didn't change")
            continue
        print(f"{benchmark1.query:110} is {round(abs(result), 2)}x {status}")


def execute(action, **kwargs):
    if action == "run":
        executor = action_run
    elif action == "show":
        executor = action_show
    elif action == "compare":
        executor = action_compare
    else:
        return NotImplemented

    return executor(**kwargs)


def main():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest="action")

    subparser_run = subparsers.add_parser("run")
    subparser_run.add_argument(
        "-b", "--benchmarks-file", default="benchmarks/benchmarks.json"
    )
    subparser_run.add_argument(
        "-o", "--output-file", default="benchmarks/output.json"
    )

    subparser_show = subparsers.add_parser("show")
    subparser_show.add_argument(
        "-o", "--output-file", default="benchmarks/output.json"
    )

    subparser_show = subparsers.add_parser("compare")
    subparser_show.add_argument("-o", "--old-file")
    subparser_show.add_argument("-n", "--new-file")

    options = parser.parse_args()
    if execute(**vars(options)) is NotImplemented:
        parser.print_help()


if __name__ == "__main__":
    main()
