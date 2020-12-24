import random
import warnings
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import ExitStack
from pathlib import Path

from reiz.database import get_new_connection
from reiz.edgeql import EdgeQLSelect, EdgeQLSelector, as_edgeql
from reiz.sampling import SamplingData
from reiz.serialization.serializer import insert_file, insert_project_metadata
from reiz.utilities import guarded, logger

FILE_CACHE = frozenset()
PROJECT_CACHE = {}


def sync_cache():
    global FILE_CACHE, PROJECT_CACHE

    with get_new_connection() as connection:
        selection = EdgeQLSelect(
            "Module",
            selections=[
                EdgeQLSelector("filename"),
            ],
        )
        modules = connection.query(as_edgeql(selection))

        selection = EdgeQLSelect(
            "project", selections=[EdgeQLSelector("name")]
        )
        projects = connection.query(as_edgeql(selection))

    FILE_CACHE = frozenset(module.filename for module in modules)
    PROJECT_CACHE.update({project.name: project for project in projects})


@guarded
def insert_project(connection, instance, clean_directory):
    instance_directory = clean_directory / instance.name
    project_ref = insert_project_metadata(
        connection, instance, cache=PROJECT_CACHE
    )
    for file in instance_directory.glob("**/*.py"):
        filename = str(file.relative_to(clean_directory))
        if filename in FILE_CACHE:
            continue

        if insert_file(connection, file, filename, project_ref):
            logger.info("%s successfully inserted", filename)


def insert_dataset(data_file, clean_directory, workers):
    # Collect the files that we have already inserted
    sync_cache()

    instances = SamplingData.load(data_file)
    random.shuffle(instances)

    with ExitStack() as stack:
        executor = stack.enter_context(ThreadPoolExecutor(workers))
        connection_pools = [
            stack.enter_context(get_new_connection())
            for _ in range(workers * 2)
        ]
        total_pools = len(connection_pools)
        futures = [
            executor.submit(
                insert_project,
                connection_pools[index % total_pools],
                instance,
                clean_directory,
            )
            for index, instance in enumerate(instances)
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
    parser.add_argument("--workers", type=int, default=3)
    options = parser.parse_args()

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        insert_dataset(**vars(options))


if __name__ == "__main__":
    main()
