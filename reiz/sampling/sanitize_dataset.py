import ast
import shutil
import subprocess
import tokenize
import warnings
from argparse import ArgumentParser
from concurrent import futures
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from reiz.sampling import SamplingData
from reiz.utilities import guarded, logger


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


@guarded
def sanitize(instance, raw_directory, clean_directory, force, ignore_tests):
    src = raw_directory / instance.name
    dest = clean_directory / instance.name
    if dest.exists() and not force:
        return instance

    shutil.copytree(src, dest, dirs_exist_ok=True)

    def is_test(source):
        if not ignore_tests:
            return False
        return source.name.startswith("test_")

    for possible_source in dest.glob("**/*"):
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
        ["find", ".", "-type", "d", "-empty", "-delete"], cwd=dest
    )
    return instance


def sanitize_dataset(
    data_file,
    checkout_directory,
    clean_directory,
    workers=4,
    force=False,
    ignore_tests=False,
):
    clean_directory.mkdir(exist_ok=True)

    instances = SamplingData.load(data_file)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                sanitize,
                instance,
                checkout_directory,
                clean_directory,
                force,
                ignore_tests,
            )
            for instance in instances
        ]
        for future in futures.as_completed(futures):
            instance = future.result()
            if instance is None:
                continue

            logger.info("%r has been sanitized", instance.name)


def main():
    parser = ArgumentParser()
    parser.add_argument("data_file", type=Path)
    parser.add_argument("checkout_directory", type=Path)
    parser.add_argument("clean_directory", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--ignore-tests", action="store_true")
    options = parser.parse_args()

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        sanitize_dataset(**vars(options))


if __name__ == "__main__":
    main()
