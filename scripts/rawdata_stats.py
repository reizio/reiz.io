#!/usr/bin/env python

import subprocess
from argparse import ArgumentParser
from pathlib import Path


def size(path: Path) -> str:
    return subprocess.check_output(["du", "-sh", path]).split()[0].decode()


def dump_stats(directory: Path) -> None:
    for raw_source in ("PyPI",):
        print(
            f"Total size of {raw_source} samples:",
            size(directory / raw_source.lower()),
        )
    print("Finalized source size:", size(directory / "clean"))


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("directory", type=Path)
    options = parser.parse_args()

    dump_stats(**vars(options))


if __name__ == "__main__":
    main()
