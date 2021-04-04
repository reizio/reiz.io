import shutil
import subprocess
import warnings
from argparse import ArgumentParser
from concurrent import futures
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from reiz.sampling import dump_dataset, load_dataset
from reiz.utilities import guarded, logger


@guarded
def checkout_sampling_data(checkout_directory, project, force):
    if project.git_revision and not force:
        return project

    repo_dir = checkout_directory / project.name
    if repo_dir.exists():
        shutil.rmtree(repo_dir)

    subprocess.check_call(
        [
            "git",
            "clone",
            project.git_source,
            project.name,
            "--depth",
            "1",
        ],
        timeout=60,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        cwd=checkout_directory,
    )
    project.git_revision = subprocess.check_output(
        ["git", "log", "--format='%H'", "-n", "1"], cwd=repo_dir, text=True
    ).strip()[1:-1]
    return project


@guarded
def fetch(projects, checkout_directory, workers, force):
    with ProcessPoolExecutor(max_workers=workers) as executor:
        tasks = [
            executor.submit(
                checkout_sampling_data,
                checkout_directory,
                project,
                force,
            )
            for project in projects
        ]
        for task in futures.as_completed(tasks):
            if project := task.result():
                logger.info(
                    "%r has been checked at %s revision",
                    project.name,
                    project.git_revision,
                )
            yield project


def fetch_dataset(data_file, checkout_directory, force=False, workers=4):
    checkout_directory.mkdir(exist_ok=True)

    projects = load_dataset(data_file)
    projects = list(fetch(projects, checkout_directory, workers, force))
    dump_dataset(data_file, projects)


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
