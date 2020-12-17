import subprocess
from argparse import ArgumentParser
from concurrent.futures import as_completed
from pathlib import Path

from reiz.sampling import SamplingData
from reiz.utilities import get_executor, guarded, logger


@guarded
def checkout_sampling_data(checkout_directory, force, instance):
    if instance.git_revision and not force:
        return instance

    repo_dir = checkout_directory / instance.name
    if not repo_dir.exists():
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
    with get_executor(workers) as executor:
        futures = [
            executor.submit(
                checkout_sampling_data, checkout_directory, force, instance
            )
            for instance in instances
        ]
        for future in as_completed(futures):
            instance = future.result()
            if instance is None:
                continue

            logger.info(
                "%r has been checked at %s revision",
                instance.name,
                instance.git_revision,
            )
            yield instance


def fetch_dataset(data_file, checkout_directory, workers=4, force=False):
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
    fetch_dataset(**vars(options))


if __name__ == "__main__":
    main()