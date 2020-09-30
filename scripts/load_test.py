#!/usr/bin/env python

import json
import random
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from reiz.utilities import logger

QUERIES = [
    "Name()",
    "Name(ctx=Load())",
    "Attribute(Name(), 'foo')",
    "FunctionDef()",
    "Attribute()",
    "ClassDef()",
    "Name('foo' | 'bar')",
    "Name(ctx=Load() | Store())",
    "FunctionDef(body=[Assign(), Return()])",
    "FunctionDef(body=[Assign(), Return(Dict())])",
    "FunctionDef(body=[Assign(), Return(Dict() | List())])",
    "FunctionDef(decorator_list=[Name('classmethod')], body={Return(Tuple())})",
    "FunctionDef(body={Return(Tuple())}, decorator_list=[Name('classmethod' | 'staticmethod')])",
    "FunctionDef(decorator_list=[Name(), Name(), Name()])",
    "ClassDef(body={FunctionDef(decorator_list=[Name('classmethod')])})",
    "ClassDef(body=[AsyncFunctionDef(), AsyncFunctionDef()])",
]


class QueryError(Exception):
    @property
    def query(self):
        return self.args[0]

    @property
    def reason(self):
        return self.args[1]


def post_request(api, query):
    request = Request(api + "/query")
    request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, json.dumps({"query": query}).encode()) as page:
            results = json.load(page)
    except HTTPError as exc:
        if exc.code == 429:
            raise QueryError(query, "RATE LIMITED!")
        else:
            results = json.load(exc)

    if results["status"] != "success":
        raise QueryError(query, results["exception"])

    return results["results"]


def worker(query, api):
    try:
        matches = len(post_request(api, query))
    except QueryError as exc:
        logger.error("Query %r failed with %s!", exc.query, exc.reason)
        return False
    else:
        logger.info("Query succeed with %d matches!", matches)
        return True


def main():
    parser = ArgumentParser()
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--api", default="https://api.tree.science")
    parser.add_argument("--iterations", type=int, default=100)
    options = parser.parse_args()
    logger.info(
        "Starting %d threads for running total of %d queries",
        options.workers,
        options.iterations,
    )
    with ThreadPoolExecutor(max_workers=options.workers) as executor:
        results = []
        dataset = random.choices(QUERIES, k=options.iterations)
        for result in executor.map(partial(worker, api=options.api), dataset):
            results.append(result)
            logger.info(
                "Status: %d/%d", results.count(True), results.count(False)
            )


if __name__ == "__main__":
    main()
