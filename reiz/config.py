import json
from pathlib import Path
from types import SimpleNamespace

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
#         "clean_directory": str
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
        if not isinstance(original, kind):
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


@validator.segment("data", requirements=["clean_directory"])
def proccess_segment(segment):
    validator.cast(segment, "clean_directory", Path)

    segment.clean_directory = segment.clean_directory.expanduser()
    if not segment.clean_directory.exists():
        raise ValueError(
            f"Data directory ({segment.clean_directory!s}) doesn't exist."
        )


@validator.segment("web", requirements=["timeout", "host", "port"])
def process_segment(segment):
    validator.set_if_not_already(segment, "workers", 1)


@validator.segment("ir")
def process_segment(segment):
    validator.set_if_not_already(segment, "backend", "edgeql")


config = sync_config()
