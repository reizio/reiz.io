import json
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger("source")
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(funcName)-15s --- %(message)s",
    datefmt="%m-%d %H:%M",
)


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
