from __future__ import annotations

import json
import os
import tarfile
import zipfile
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import Generator, List, Literal, Optional, Tuple, Union, cast
from urllib.error import HTTPError
from urllib.request import urlopen, urlretrieve

from reiz.utilities import logger, read_config, write_config

PYPI_INSTANCE = "https://pypi.org/pypi"
PYPI_TOP_PACKAGES = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages-{days}-days.json"

ArchiveKind = Union[tarfile.TarFile, zipfile.ZipFile]
Days = Union[Literal[30], Literal[365]]


def get_package_source(package: str, version: Optional[str] = None) -> str:
    try:
        with urlopen(PYPI_INSTANCE + f"/{package}/json") as page:
            metadata = json.load(page)
    except HTTPError:
        raise ValueError(f"Couldn't locate the data for package: {package!r}")

    if version is None:
        sources = metadata["urls"]
    else:
        if version in metadata["releases"]:
            sources = metadata["releases"][version]
        else:
            raise ValueError(
                f"No releases found with given version ('{version}') tag. "
                f"Found releases: {metadata['releases'].keys()}"
            )

    for source in sources:
        if source["python_version"] == "source":
            break
    else:
        raise ValueError(f"Couldn't find any sources for {package}")

    return cast(str, source["url"])


def get_archive_manager(local_file: str) -> ArchiveKind:
    if tarfile.is_tarfile(local_file):
        return tarfile.open(local_file)
    elif zipfile.is_zipfile(local_file):
        return zipfile.ZipFile(local_file)
    else:
        raise ValueError("Unknown archive kind.")


def get_first_archive_member(archive: ArchiveKind) -> str:
    if isinstance(archive, tarfile.TarFile):
        return archive.getnames()[0]
    elif isinstance(archive, zipfile.ZipFile):
        return archive.namelist()[0]


def download_and_extract(
    package: str, directory: Path, version: Optional[str] = None
) -> Path:
    try:
        source = get_package_source(package, version)
    except ValueError:
        return None

    local_file, _ = urlretrieve(source, directory / f"{package}-src")
    with get_archive_manager(local_file) as archive:
        archive.extractall(path=directory)
        result_dir = get_first_archive_member(archive)
    os.remove(local_file)
    logger.debug("fetched package: %r", package)
    return directory / result_dir


def get_package(
    package: str, directory: Path, version: Optional[str] = None
) -> Tuple[str, Optional[Path]]:
    try:
        return package, download_and_extract(package, directory, version)
    except Exception as e:
        logger.exception("caught exception while fetching %r", package)
        return package, None


def get_top_packages(days: Days) -> List[str]:
    with urlopen(PYPI_TOP_PACKAGES.format(days=days)) as page:
        result = json.load(page)

    return [package["project"] for package in result["rows"]]


def filter_already_downloaded(
    directory: Path, packages: List[str]
) -> List[str]:
    cache = read_config(directory / "info.json")
    return [package for package in packages if package not in cache]


def download_top_packages(
    directory: Path,
    days: Days = 365,
    workers: int = 24,
    limit: slice = slice(None),
) -> Generator[Path, None, None]:
    directory.mkdir(exist_ok=True)
    if not (directory / "info.json").exists():
        dump_config(directory, [])

    packages = get_top_packages(days)[limit]
    packages = filter_already_downloaded(directory, packages)
    caches = []
    # FIX-ME(low): get rid of try/finally and make sure
    # all exceptions are suppresed in get_package
    try:
        # FIX-ME(low): use reiz.utilities.get_executor
        with ThreadPoolExecutor(max_workers=workers) as executor:
            bound_downloader = partial(get_package, directory=directory)
            for package, package_directory in executor.map(
                bound_downloader, packages
            ):
                if package_directory is not None:
                    caches.append(package)
    finally:
        write_config(
            directory / "info.json",
            read_config(directory / "info.json") + caches,
        )
    logging.info("fetched %d projects", len(caches))


def main():
    parser = ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--days", choices=(30, 365), type=int, default=30)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--limit",
        type=lambda limit: slice(*map(int, limit.split(":"))),
        default=slice(0, 100),
    )
    options = parser.parse_args()
    download_top_packages(**vars(options))


if __name__ == "__main__":
    main()
