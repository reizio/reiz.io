import ast
import shutil
import subprocess
import tokenize
import warnings
from argparse import ArgumentParser
from concurrent.futures import as_completed
from pathlib import Path

from reiz.sampling import SamplingData
from reiz.utilities import get_executor, guarded, logger


def source_code(path: Path):
    try:
        with tokenize.open(path) as file:
            source = file.read()
        ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return False
    except Exception:
        return False
    else:
        return True


def sanitize(path, ignore_tests):
    def is_test(source):
        if not ignore_tests:
            return False
        return source.name.startswith("test_")

    for possible_source in path.glob("**/*"):
        if not possible_source.is_file():
            continue

        if (
            possible_source.suffix == ".py"
            and not is_test(possible_source)
            and source_code(possible_source)
        ):
            continue
        else:
            possible_source.unlink()

    subprocess.check_call(
        ["find", ".", "-type", "d", "-empty", "-delete"], cwd=path
    )


@guarded
def checkout_sampling_data(checkout_directory, instance, fetch_options):
    if instance.git_revision and not fetch_options.force:
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

    shutil.rmtree(repo_dir / ".git")
    sanitize(repo_dir, fetch_options.ignore_tests)
    return instance


@guarded
def fetch(instances, checkout_directory, workers, fetch_options):
    with get_executor(workers) as executor:
        futures = [
            executor.submit(
                checkout_sampling_data,
                checkout_directory,
                instance,
                fetch_options,
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


def fetch_dataset(
    data_file, checkout_directory, fetch_options, workers=4, **_
):
    checkout_directory.mkdir(exist_ok=True)

    instances = SamplingData.load(data_file)
    instances = list(
        fetch(instances, checkout_directory, workers, fetch_options)
    )
    SamplingData.dump(data_file, instances)


def main():
    parser = ArgumentParser()
    parser.add_argument("data_file", type=Path)
    parser.add_argument("checkout_directory", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--ignore-tests", action="store_true")

    options = parser.parse_args()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        fetch_dataset(**vars(options), fetch_options=options)


if __name__ == "__main__":
    main()
