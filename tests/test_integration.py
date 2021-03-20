import json
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

PROJECT_PATH = Path(__file__).parent.parent
STATIC_PATH = PROJECT_PATH / "static"


def query(query_str, host="http://localhost:8000/query/", **query_kwargs):
    query = {"query": query_str, **query_kwargs}
    query_data = json.dumps(query).encode()
    with urlopen(host, data=query_data) as page:
        return json.load(page)


def health_check():
    try:
        query("Name()")
    except (URLError, ConnectionResetError):
        return False
    else:
        return True


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    return PROJECT_PATH / "docker-compose.yml"


@pytest.fixture(scope="session")
def reiz_service():
    process = subprocess.Popen(["docker-compose", "up"])
    total_wait = 0
    while not health_check():
        if total_wait >= 60 * 30:
            raise ValueError(
                "tests: docker service is not responding (awaited 30 mins)"
            )
        time.sleep(30)
        total_wait += 30
    yield
    process.terminate()


def test_reiz_web_api_basic(reiz_service):
    assert query("Name()")
