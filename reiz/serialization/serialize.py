import random
import warnings
from argparse import ArgumentParser
from concurrent import futures
from pathlib import Path

from reiz.sampling import SamplingData
from reiz.serialization.serializer import insert_project
from reiz.utilities import logger

TASK_LIMIT = 6
FILE_LIMIT = 10


def insert_dataset(data_file, clean_directory, workers=2, fast=False):
    instances = SamplingData.load(data_file, random_order=True)
    bound_instances = {}

    with futures.ThreadPoolExecutor(max_workers=workers) as executor:

        def create_tasks(amount):
            tasks = set()
            for instance in random.sample(instances, k=amount):
                task = executor.submit(
                    insert_project, instance, limit=FILE_LIMIT, fast=fast
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
                insertions = task.result()
                if insertions == 0:
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
                        insertions,
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
