import sys
import tokenize
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Set

from reiz.config import config
from reiz.database import get_new_connection
from reiz.fetch import run_query_on_connection
from reiz.sampling import SamplingData
from reiz.serialization.serialize import insert_project
from reiz.utilities import logger

REPO_PATH = Path(__file__).parent.parent.resolve()
sys.path.insert(0, REPO_PATH)

from scripts.reset_db import drop_and_load_db

TESTING_PATH = REPO_PATH / "test_cases"

DATASET_PATH = TESTING_PATH / "dataset"
QUERIES_PATH = TESTING_PATH / "queries"


def update_db():
    assert config.database.database == "reiz_test"
    drop_and_load_db(
        REPO_PATH / "static" / "Python-reiz.edgeql", reboot_server=False
    )

    fake_sampling_data = SamplingData(
        "dataset",
        downloads=0,
        git_source="https://github.com/reizio/fake_data",
        git_revision="master",
    )
    insert_project(fake_sampling_data, TESTING_PATH)


def setup(use_same_db=False):
    config.database.database = "reiz_test"
    if not use_same_db:
        update_db()


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

    def execute(self, connection):
        result_line_numbers = set()
        for result in run_query_on_connection(
            connection, self.reiz_ql, limit=None, include_positions=True
        ):
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


def collect_tests(queries=QUERIES_PATH):
    for query in queries.glob("**/*.reizql"):
        yield TestItem.from_test_path(query)


def run_tests():
    with get_new_connection() as connection:
        for test_case in collect_tests():
            try:
                test_case.execute(connection)
            except ExpectationFailed:
                logger.info("%s %s", test_case.name, "failed")
            else:
                logger.info("%s %s", test_case.name, "succeed")


def main():
    parser = ArgumentParser()
    parser.add_argument("--use-same-db", action="store_true")

    options = parser.parse_args()
    setup(**vars(options))
    run_tests()


if __name__ == "__main__":
    main()
