import json
import logging
import sys
from concurrent.futures import ProcessPoolExecutor
from enum import Enum
from functools import partialmethod, wraps
from pathlib import Path
from typing import ContextManager, List
from urllib.request import urlopen

from reiz.db.connection import DEFAULT_DATABASE, DEFAULT_DSN

try:
    import black
except ModuleNotFoundError:
    import pprint

    USE_PPRINT = True
else:
    USE_PPRINT = False
    BLACK_MODE = black.Mode(line_length=65)

DEFAULT_CONFIG_PATH = Path("~/.local/reiz.json").expanduser()


def add_logging_level(name, value):
    logger_cls = logging.getLoggerClass()
    logger_method = partialmethod(logger_cls.log, value)

    logging.addLevelName(value, name)
    setattr(logging, name, value)
    setattr(logger_cls, name.lower(), logger_method)


add_logging_level("TRACE", 5)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter("[%(asctime)s] %(funcName)-15s --- %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)


def get_executor(workers: int) -> ContextManager:
    return ProcessPoolExecutor(max_workers=workers)


def read_config(config: Path) -> List[str]:
    if config.exists():
        with open(config) as config_f:
            data = json.load(config_f)
        return data
    else:
        return []


def write_config(config: Path, data: List[str]) -> None:
    with open(config, "w") as config:
        json.dump(data, config)


def get_config_settings():
    if DEFAULT_CONFIG_PATH.exists():
        with open(DEFAULT_CONFIG_PATH) as file:
            return json.load(file)
    else:
        return {}


def get_db_settings():
    if config := get_config_settings():
        return config["db"]
    else:
        return {"dsn": DEFAULT_DSN, "database": DEFAULT_DATABASE}


def guarded(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception(
                "Guarded function %r failed the execution", func.__name__
            )
            return None

    return wrapper


class ReizEnum(Enum):
    # normal __repr__: <$cls.$name: $value>
    # ReizEnum __repr__: $cls.$name

    def __repr__(self):
        return str(self)


def normalize(data):
    for key, value in data.copy().items():
        if isinstance(value, ReizEnum):
            data[key] = repr(value)

    return data


# from reiz.utilities import pprint;pprint()
def pprint(obj):
    if USE_PPRINT:
        pprint.pprint(obj)
    else:
        print(black.format_str(repr(obj), mode=BLACK_MODE))


def request(url):
    with urlopen(url) as page:
        return page.read().decode()


def json_request(url):
    return json.loads(request(url))
