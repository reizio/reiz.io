import random
import warnings
from argparse import ArgumentParser
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from reiz.sampling import load_dataset
from reiz.serialization.context import GlobalContext
from reiz.serialization.serializer import insert_project
from reiz.serialization.statistics import Insertion
from reiz.utilities import logger

TASK_LIMIT = 6
FILE_LIMIT = 10


def insert_dataset(data_file, clean_directory, workers=2, fast=False):
    instances = load_dataset(data_file)
    bound_instances = {}

    global_ctx = GlobalContext(
        properties={"fast_mode": fast, "max_files": FILE_LIMIT}
    )

    with ThreadPoolExecutor(max_workers=workers) as executor:

        def create_tasks(amount):
            tasks = set()
            for instance in random.sample(
                instances, k=min(amount, len(instances))
            ):
                if instance in bound_instances.values():
                    continue
                task = executor.submit(
                    insert_project, instance, global_ctx=global_ctx
                )
                bound_instances[task] = instance
                tasks.add(task)
            return tasks

        tasks = create_tasks(TASK_LIMIT)
        while tasks:
            done, tasks = futures.wait(
                tasks, return_when=futures.FIRST_COMPLETED
            )
            for task in done:
                instance = bound_instances[task]
                stats = task.result()
                if stats[Insertion.INSERTED] == 0:
                    logger.info(
                        "%r project has been inserted successfully",
                        instance.name,
                    )
                    bound_instances.pop(task, None)
                    if instance in instances:
                        instances.remove(instance)
                else:
                    logger.info(
                        "%d files from %r project have been inserted"
                        ", switching to another",
                        stats[Insertion.INSERTED],
                        instance.name,
                    )

            tasks.update(create_tasks(len(done)))


def main():
    parser = ArgumentParser()
    parser.add_argument("data_file", type=Path)
    parser.add_argument("clean_directory", type=Path)
    parser.add_argument("-w", "--workers", default=2, type=int)
    parser.add_argument("--fast", action="store_true")
    options = parser.parse_args()

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        insert_dataset(**vars(options))


if __name__ == "__main__":
    main()
