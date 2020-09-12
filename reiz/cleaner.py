from __future__ import annotations

import ast
import json
import shutil
import tokenize
import warnings
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path
from typing import List


def read_config(directory: Path) -> List[str]:
    if (pkg_config := directory / "info.json").exists():
        with open(pkg_config) as config:
            cache = json.load(config)
        return cache
    else:
        return []


def source_code(path: Path):
    try:
        with tokenize.open(path) as file:
            source = file.read()
        ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return False
    except Exception:
        # not a file [directories with .py extension, exist :(]
        # or any other issue, but we don't know whether it is
        # syntax related or not, so return True
        return True
    else:
        return True


def extract(project: Path[str, Path], clean_dir: Path) -> Tuple[str, Path]:
    project_name, project_dir = project
    destination_dir = clean_dir / project_name
    try:
        shutil.copytree(project_dir, destination_dir, dirs_exist_ok=True)
        for possible_source in destination_dir.glob("**/*"):
            if not possible_source.is_file():
                continue
            if possible_source.suffix != ".py" or not source_code(
                possible_source
            ):
                possible_source.unlink()
    except:
        return project_name, None
    else:
        return project_name, destination_dir


def clean(dirty_dir: Path, clean_dir: Path, workers: int) -> None:
    projects = read_config(dirty_dir)
    project_paths = {}
    for directory in dirty_dir.iterdir():
        project_name, *version = directory.name.split("-", -1)
        if directory.is_file() or project_name not in projects:
            continue

        project_paths[project_name] = directory

    cache = read_config(clean_dir)
    projects = []
    try:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            bound_extractor = partial(extract, clean_dir=clean_dir)
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                for project_name, destination_dir in executor.map(
                    bound_extractor,
                    filter(
                        lambda item: item[0] not in cache,
                        project_paths.items(),
                    ),
                ):
                    if destination_dir is None:
                        print(f"{project_name} extraction failed")
                    else:
                        print(
                            f"{project_name} extracted to {destination_dir!s}"
                        )
                        cache.append(project_name)
    finally:
        with open(clean_dir / "info.json", "w") as config:
            json.dump(cache, config)


def main():
    parser = ArgumentParser()
    parser.add_argument("dirty_dir", type=Path)
    parser.add_argument("clean_dir", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    options = parser.parse_args()
    clean(**vars(options))


if __name__ == "__main__":
    main()
