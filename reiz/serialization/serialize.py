import itertools
import warnings
from argparse import ArgumentParser
from concurrent import futures
from pathlib import Path

from reiz.sampling import SamplingData
from reiz.serialization.serializer import insert_project

TASK_LIMIT = 6


def insert_dataset(data_file, clean_directory, jobs):
    instances = SamplingData.iter_load(data_file, random_order=True)

    with futures.ThreadPoolExecutor(max_workers=jobs) as executor:

        def create_tasks(amount):
            return {
                executor.submit(insert_project, instance)
                for instance in itertools.islice(instances, amount)
            }

        tasks = create_tasks(TASK_LIMIT)
        while tasks:
            done, tasks = futures.wait(
                tasks, return_when=futures.FIRST_COMPLETED
            )
            for task in done:
                try:
                    task.exception()
                except:
                    exit()
            tasks.update(create_tasks(len(done)))


def main():
    parser = ArgumentParser()
    parser.add_argument("data_file", type=Path)
    parser.add_argument("clean_directory", type=Path)
    parser.add_argument("-j", "--jobs", default=2, type=int)
    options = parser.parse_args()

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        insert_dataset(**vars(options))


if __name__ == "__main__":
    main()
