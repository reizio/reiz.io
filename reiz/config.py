import json
from pathlib import Path
from types import SimpleNamespace

from reiz.utilities import logger

# {
#     "database": {
#         "dsn": str,
#         "cluster": str,
#         "database": str
#     },
#     "redis": {
#         "cache": bool,
#         "instance": str
#     },
#     "data": {
#         "path": str
#     },
#     "web": {
#         "host": str,
#         "port": int,
#         "workers": int,
#         "timeout": int
#     },
#     "ir": {
#        "backend": {"edgeql"}
#     }
# }


CONFIG_LOCATION = Path("~/.local/reiz.json").expanduser()


def sync_config(location=CONFIG_LOCATION):
    if not location.exists():
        raise ValueError(
            f"sync_config requires a config file under {location!s}."
        )

    with open(CONFIG_LOCATION) as stream:
        raw_config = json.load(
            stream, object_hook=lambda data: SimpleNamespace(**data)
        )

    return validator.validate(raw_config)


@object.__new__
class validator:
    _segments = {}

    def validate(self, config):
        for segment, validator in self._segments.items():
            self.set_if_not_already(config, segment, SimpleNamespace())
            validator(getattr(config, segment))

        return config

    def segment(self, segment_name, requirements=()):
        def wrapper(func):
            def validator(segment):
                if not all(hasattr(segment, field) for field in requirements):
                    raise ValueError(
                        f"{segment_name!r} is missing a required field."
                    )
                return func(segment)

            self._segments[segment_name] = validator

        return wrapper

    def set_if_not_already(self, segment, field, default=None):
        if not hasattr(segment, field):
            setattr(segment, field, default)

    def cast(self, segment, field, kind):
        original = getattr(segment, field)
        setattr(segment, field, kind(original))


@validator.segment("database", requirements=["dsn", "database"])
def process_segment(segment):
    validator.set_if_not_already(segment, "cluster")
    validator.set_if_not_already(segment, "options", SimpleNamespace())
    validator.cast(segment, "options", vars)


@validator.segment("redis")
def process_segment(segment):
    validator.set_if_not_already(segment, "cache", False)
    validator.set_if_not_already(segment, "instance")


@validator.segment("data", requirements=["path"])
def proccess_segment(segment):
    validator.cast(segment, "path", Path)

    segment.path = segment.path.expanduser()
    if not segment.path.exists():
        logger.warn("designated data path (%r) doesn't exist", segment.path)


@validator.segment("web", requirements=["timeout", "host", "port"])
def process_segment(segment):
    validator.set_if_not_already(segment, "workers", 1)


@validator.segment("ir")
def process_segment(segment):
    validator.set_if_not_already(segment, "backend", "edgeql")


config = sync_config()
