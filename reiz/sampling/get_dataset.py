from argparse import ArgumentParser
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from reiz.sampling import SamplingData, dump_dataset
from reiz.utilities import guarded, json_request, logger

PYPI_INSTANCE = "https://pypi.org/pypi"
PYPI_DATSET_URL = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages-365-days.json"

SOURCE_LOCATIONS = frozenset(
    (
        "Source Code",
        "Source",
        "Code",
        "GitHub Project",
        "Repository",
        "Homepage",
    )
)


def is_github_link(link):
    if not link.endswith("/"):
        link += "/"

    parts = link.split("/")
    return len(parts) >= 5 and parts[-4] == "github.com"


def _contains(item):
    key, value = item
    return str(key) in SOURCE_LOCATIONS


@guarded
def get_sampling_data(project, download_count):
    package_response = json_request(PYPI_INSTANCE + f"/{project}/json")
    if info := package_response.get("info"):
        license_type = info.get("license") or None
        links = info.get("project_urls") or {}

        for _, link in sorted(links.items(), key=_contains):
            if is_github_link(link):
                break
        else:
            return None

    return SamplingData(
        project, download_count, link, license_type=license_type
    )


def get_pypi_dataset(data_file, workers=4, limit=500):
    response = json_request(PYPI_DATSET_URL)
    projects = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        tasks = [
            executor.submit(get_sampling_data, **package)
            for package in response["rows"]
        ]

        for task in futures.as_completed(tasks):
            if project := task.result():
                logger.info("Adding %s to the dataset", project.name)
                projects.append(project)

            if len(projects) >= limit:
                break

        for task in tasks:
            if not task.done():
                task.cancel()

    logger.info(
        "%d repositories have been added to the %s",
        len(projects),
        str(data_file),
    )
    dump_dataset(data_file, projects)


def main():
    parser = ArgumentParser()
    parser.add_argument("data_file", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=500)
    options = parser.parse_args()
    get_pypi_dataset(**vars(options))


if __name__ == "__main__":
    main()
