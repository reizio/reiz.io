#!/usr/bin/env python

import json
import os
import subprocess
import sys
import time
import tokenize
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Set

import edgedb

from reiz.config import config
from reiz.database import get_new_connection
from reiz.edgeql import EdgeQLAttribute, EdgeQLFilter, EdgeQLFilterKey
from reiz.fetch import _get_query, _process_query_set
from reiz.sampling import SamplingData
from reiz.serialization.serialize import insert_project
from reiz.utilities import logger, pprint

REPO_PATH = Path(__file__).parent.parent.resolve()
sys.path.insert(0, REPO_PATH)

from scripts.reset_db import drop_and_load_db

TESTING_PATH = REPO_PATH / "test_cases"
DATASET_PATH = TESTING_PATH / "dataset"
QUERIES_PATH = TESTING_PATH / "queries"

TEST_DATABASE_NAME = "reiz_test"
TEST_DATABASE_USER = "reiz_tester"
TEST_DATABASE_PASSWORD = "reiz123"

EDB_PROCESS = None


def edb_running():
    return EDB_PROCESS.poll() is None


def bootstrap_connection(
    connection, user=TEST_DATABASE_USER, password=TEST_DATABASE_PASSWORD
):
    connection.execute(f"CREATE DATABASE {TEST_DATABASE_NAME};")
    connection.execute(
        f"""\
    CREATE SUPERUSER ROLE {user} {{
        SET password := "{password}"
    }};
    """
    )
    connection.execute(
        f"""\
    CONFIGURE SYSTEM INSERT Auth {{
        user := "{user}",
        priority := 10,
        method := (INSERT SCRAM),
    }};
    """
    )


def setup_edgedb_server():
    def dump(out, err):
        print("--OUT--", out, "--ERR-", err, sep="\n")

    if not (server_bin := os.getenv("EDGEDB_SERVER_BIN")):
        raise ValueError(
            "--start-edgedb-server option requires EDGEDB_SERVER_BIN to be set in the current environment"
        )

    global EDB_PROCESS
    EDB_PROCESS = process = subprocess.Popen(
        [
            server_bin,
            "--temp-dir",
            "--testmode",
            "--echo-runtime-info",
            "--port=auto",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        text=True,
    )
    for line in process.stdout:
        prefix, _, raw_data = line.partition(":")
        if prefix == "EDGEDB_SERVER_DATA":
            break
    else:
        raise ValueError("No EDGEDB_SERVER_DATA on stdout")
    server_data = json.loads(raw_data)

    # TO-DO(medium): admin=True is deprecated
    connection = edgedb.connect(
        host=server_data["runstate_dir"],
        port=server_data["port"],
        user="edgedb",
        database="edgedb",
        admin=True,
    )
    bootstrap_connection(connection)

    config.database.options = {
        "host": server_data["runstate_dir"],
        "port": server_data["port"],
        "user": TEST_DATABASE_USER,
        "password": TEST_DATABASE_PASSWORD,
    }


def update_db(change_db_schema):
    assert config.database.database == TEST_DATABASE_NAME
    if change_db_schema:
        drop_and_load_db(
            REPO_PATH / "static" / "Python-reiz.edgeql", reboot_server=False
        )

    fake_sampling_data = SamplingData(
        "dataset",
        downloads=0,
        git_source="https://github.com/reizio/fake_data",
        git_revision="master",
    )
    with get_new_connection() as connection:
        insert_project(connection, fake_sampling_data, TESTING_PATH)


def setup(
    use_same_db=False, change_db_schema=False, start_edgedb_server=False
):
    if start_edgedb_server:
        setup_edgedb_server()

    config.database.database = TEST_DATABASE_NAME
    if not use_same_db:
        update_db(change_db_schema)


class ExpectationFailed(Exception):
    ...


@dataclass
class TestItem:
    name: str
    reiz_ql: str

    expected_filename: str
    expected_line_numbers: Set[int]

    @classmethod
    def from_test_path(cls, path):
        reiz_ql = path.read_text()
        relative_path = path.relative_to(QUERIES_PATH)
        expected_path = (DATASET_PATH / relative_path).with_suffix(".py")

        expected_line_numbers = set()
        with open(expected_path) as stream:
            for token in tokenize.generate_tokens(stream.readline):
                if (
                    token.exact_type == tokenize.COMMENT
                    and "reiz: tp" in token.string
                ):
                    expected_line_numbers.add(token.start[0])

        name = str(relative_path.with_suffix(str()))
        return cls(
            name,
            reiz_ql,
            str(expected_path.relative_to(TESTING_PATH)),
            expected_line_numbers,
        )

    def expect(self, message, left, right, truth):
        if not truth:
            logger.info(
                "(%s) %s: (left=%s, right=%s)", self.name, message, left, right
            )
            raise ExpectationFailed

    def _as_query(self):
        return _get_query(
            self.reiz_ql,
            limit=None,
            offset=0,
            extra_filters=(
                EdgeQLFilter(
                    EdgeQLAttribute(EdgeQLFilterKey("_module"), "filename"),
                    repr(self.expected_filename),
                ),
            ),
        )

    def run_test_query(self, connection, benchmark=False):
        query, is_positional = self._as_query()
        query_set = connection.query(query)
        return _process_query_set(
            query_set, is_positional, include_positions=True
        )

    def execute(self, connection):
        result_line_numbers = set()
        for result in self.run_test_query(connection):
            self.expect(
                "Filenames are not equal",
                result["filename"] + ":" + str(result["lineno"]),
                self.expected_filename,
                result["filename"] == self.expected_filename,
            )
            self.expect(
                "False positive on line numbers",
                result["lineno"],
                self.expected_line_numbers,
                result["lineno"] in self.expected_line_numbers,
            )
            result_line_numbers.add(result["lineno"])

        self.expect(
            "Unmatched line numbers",
            result_line_numbers,
            self.expected_line_numbers,
            result_line_numbers == self.expected_line_numbers,
        )

    def run_benchmarks(self, connection, *, times):
        runs = []
        query, _ = self._as_query()

        for _ in range(times):
            start = time.perf_counter()
            connection.query(query)
            end = time.perf_counter()
            runs.append(end - start)

        return runs


def collect_tests(queries=QUERIES_PATH):
    for query in queries.glob("**/*.reizql"):
        yield TestItem.from_test_path(query)


def run_tests():
    fail = False
    with get_new_connection() as connection:
        for test_case in collect_tests():
            try:
                test_case.execute(connection)
            except ExpectationFailed:
                fail = True
                logger.info("%s %s", test_case.name, "failed")
            else:
                logger.info("%s %s", test_case.name, "succeed")

    return fail


def run_benchmarks(times=3):
    with get_new_connection() as connection:
        benchmarks = {
            test_case.name: test_case.run_benchmarks(connection, times=times)
            for test_case in collect_tests()
        }
        pprint(benchmarks)


def main(argv=None):
    parser = ArgumentParser()
    parser.add_argument("--use-same-db", action="store_true")
    parser.add_argument("--change-db-schema", action="store_true")
    parser.add_argument("--run-benchmarks", action="store_true")
    parser.add_argument("--start-edgedb-server", action="store_true")
    options = parser.parse_args(argv)

    setup(
        use_same_db=options.use_same_db,
        change_db_schema=options.change_db_schema,
        start_edgedb_server=options.start_edgedb_server,
    )
    fail = run_tests()
    if options.run_benchmarks and not fail:
        run_benchmarks()
    return fail


if __name__ == "__main__":
    exit(main())
