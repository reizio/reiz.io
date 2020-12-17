from argparse import ArgumentParser
from concurrent.futures import as_completed
from pathlib import Path

from reiz.sampling import SamplingData
from reiz.utilities import get_executor, guarded, json_request, logger

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


@guarded
def get_sampling_data(project, download_count):
    package_response = json_request(PYPI_INSTANCE + f"/{project}/json")
    if info := package_response.get("info"):
        links = info.get("project_urls") or {}
        sorted(links, key=lambda kv: str(kv[0]) in SOURCE_LOCATIONS)

        for link in links.values():
            if is_github_link(link):
                break
        else:
            return None

    return SamplingData(project, download_count, link)


def get_pypi_dataset(data_file, workers=4):
    response = json_request(PYPI_DATSET_URL)
    instances = []

    with get_executor(workers) as executor:
        futures = [
            executor.submit(get_sampling_data, **package)
            for package in response["rows"]
        ]
        for future in as_completed(futures):
            instance = future.result()
            if instance is None:
                continue
            logger.info("Fetched: %s", instance)
            instances.append(instance)

    logger.info(
        "%d repositories have been added to the %s",
        len(instances),
        str(data_file),
    )
    SamplingData.dump(data_file, instances)


def main():
    parser = ArgumentParser()
    parser.add_argument("data_file", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    options = parser.parse_args()
    get_pypi_dataset(**vars(options))


if __name__ == "__main__":
    main()
