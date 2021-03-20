from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from requests.exceptions import ConnectionError

PROJECT_PATH = Path(__file__).parent.parent
STATIC_PATH = PROJECT_PATH / "static"


def query(host, query_str, **query_kwargs):
    query = {"query": query_str, **query_kwargs}
    query_data = json.dumps(query).encode()
    with urlopen(host, data=query_data) as page:
        return json.load(page)


def health_check(host):
    try:
        query(host, "Name()")
    except URLError:
        return False
    else:
        return True


@pytest.fixture(scope="session")
def reiz_service(docker_ip, docker_services):
    docker_cfg = sync_config(STATIC_PATH / "configs" / "docker_config.json")
    url = "http://{}:{}".format(docker_ip, 8000)
    docker_services.wait_until_responsive(
        timeout=1800, pause=30, check=lambda: health_check(url)
    )
    return url


def test_reiz_web_api_basic(reiz_service):
    assert query("Name()")