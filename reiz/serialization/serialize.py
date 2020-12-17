import random
import warnings
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from pathlib import Path

from reiz.db.connection import connect
from reiz.edgeql import EdgeQLSelect, EdgeQLSelector, construct
from reiz.sampling import SamplingData
from reiz.serialization.serializer import insert_file, insert_project_metadata
from reiz.utilities import get_db_settings, guarded, logger

FILE_CACHE = frozenset()


def sync_cache(connector):
    global FILE_CACHE
    with connector() as connection:
        selection = EdgeQLSelect(
            "Module",
            selections=[
                EdgeQLSelector("filename"),
            ],
        )
        result_set = connection.query(construct(selection, top_level=True))

    FILE_CACHE = frozenset(module.filename for module in result_set)


@guarded
def insert_project(instance, clean_directory, connector):
    instance_directory = clean_directory / instance.name
    with connector() as connection:
        project_ref = insert_project_metadata(connection, instance)
        for file in instance_directory.glob("**/*.py"):
            filename = str(file.relative_to(clean_directory))
            if filename in FILE_CACHE:
                continue

            if insert_file(connection, file, filename, project_ref):
                logger.info("%s successfully inserted", filename)


def insert_dataset(data_file, clean_directory, workers, **db_opts):
    connector = partial(connect, **db_opts)

    # Collect the files that we have already inserted
    sync_cache(connector)

    instances = SamplingData.load(data_file)
    random.shuffle(instances)
    with ThreadPoolExecutor(workers) as executor:
        futures = [
            executor.submit(
                insert_project, instance, clean_directory, connector
            )
            for instance in instances
        ]
        for future in as_completed(futures):
            instance = future.result()
            if instance is None:
                continue
            logger.info("%r has been inserted", instance.name)


def main():
    parser = ArgumentParser()
    parser.add_argument("data_file", type=Path)
    parser.add_argument("clean_directory", type=Path)
    parser.add_argument("--dsn", default=get_db_settings()["dsn"])
    parser.add_argument("--database", default=get_db_settings()["database"])
    parser.add_argument("--workers", type=int, default=3)
    options = parser.parse_args()

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        insert_dataset(**vars(options))


if __name__ == "__main__":
    main()
