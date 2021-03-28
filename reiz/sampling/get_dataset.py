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
            if len(instances) >= limit:
                break

        for future in futures:
            if not future.done():
                future.cancel()

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
    parser.add_argument("--limit", type=int, default=500)
    options = parser.parse_args()
    get_pypi_dataset(**vars(options))


if __name__ == "__main__":
    main()
