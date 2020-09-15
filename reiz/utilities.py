import builtins
import contextlib
import json
import logging
from concurrent.futures import ProcessPoolExecutor
from functools import partial, partialmethod
from pathlib import Path
from typing import ContextManager, List


def add_logging_level(name, value):
    logger_cls = logging.getLoggerClass()
    logger_method = partialmethod(logger_cls.log, value)

    logging.addLevelName(value, name)
    setattr(logging, name, value)
    setattr(logger_cls, name.lower(), logger_method)


add_logging_level("TRACE", 5)
logger = logging.getLogger("source")
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(funcName)-15s --- %(message)s",
    datefmt="%m-%d %H:%M",
)


def get_executor(workers: int) -> ContextManager:
    if workers > 1:
        executor = ProcessPoolExecutor(max_workers=workers)
    else:
        executor = contextlib.nullcontext(builtins)
    return executor


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