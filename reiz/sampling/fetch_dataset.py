import shutil
import subprocess
import warnings
from argparse import ArgumentParser
from concurrent import futures
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from reiz.sampling import SamplingData
from reiz.utilities import guarded, logger


@guarded
def checkout_sampling_data(checkout_directory, instance, force):
    if instance.git_revision and not force:
        return instance

    repo_dir = checkout_directory / instance.name
    if repo_dir.exists():
        shutil.rmtree(repo_dir)

    subprocess.check_call(
        [
            "git",
            "clone",
            instance.git_source,
            instance.name,
            "--depth",
            "1",
        ],
        timeout=60,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        cwd=checkout_directory,
    )
    instance.git_revision = subprocess.check_output(
        ["git", "log", "--format='%H'", "-n", "1"], cwd=repo_dir, text=True
    ).strip()[1:-1]
    return instance


@guarded
def fetch(instances, checkout_directory, workers, force):
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                checkout_sampling_data,
                checkout_directory,
                instance,
                force,
            )
            for instance in instances
        ]
        for future in futures.as_completed(futures):
            instance = future.result()
            if instance is None:
                continue

            logger.info(
                "%r has been checked at %s revision",
                instance.name,
                instance.git_revision,
            )
            yield instance


def fetch_dataset(data_file, checkout_directory, force=False, workers=4):
    checkout_directory.mkdir(exist_ok=True)

    instances = SamplingData.load(data_file)
    instances = list(fetch(instances, checkout_directory, workers, force))
    SamplingData.dump(data_file, instances)


def main():
    parser = ArgumentParser()
    parser.add_argument("data_file", type=Path)
    parser.add_argument("checkout_directory", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--force", action="store_true")

    options = parser.parse_args()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        fetch_dataset(**vars(options))


if __name__ == "__main__":
    main()
