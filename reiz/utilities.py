import json
import logging
import os
import sys
from contextlib import contextmanager
from enum import Enum
from functools import cached_property, partial, partialmethod, wraps
from pathlib import Path
from urllib.request import urlopen

from tqdm import tqdm

try:
    import black
except ModuleNotFoundError:
    import pprint

    USE_PPRINT = True
else:
    USE_PPRINT = False
    BLACK_MODE = black.Mode(line_length=65)

STATIC_DIR = Path(__file__).parent.parent / "static"
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


def guarded(arg, *, ignored_exceptions=()):
    def make(func, default_value, ignored_exceptions):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ignored_exceptions:
                return None
            except Exception:
                logger.exception(
                    "Guarded function %r failed the execution", func.__name__
                )
                return None

        return wrapper

    if callable(arg):
        return make(
            arg, default_value=None, ignored_exceptions=ignored_exceptions
        )
    else:
        return partial(
            make, default_value=arg, ignored_exceptions=ignored_exceptions
        )


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


def singleton(cls):
    cls.__repr__ = lambda self: type(self).__name__
    return object.__new__(cls)


def make_prop(parent, cls, field):
    def _property(self):
        return getattr(getattr(self, parent), field)

    prop = cached_property(_property)
    prop.__set_name__(cls, field)
    return prop


def picker(parent):
    class CherryPicker:
        def __init_subclass__(cls, **kwargs):
            if fields := kwargs.get("inherits"):
                for field in fields:
                    setattr(cls, field, make_prop(parent, cls, field))

    return CherryPicker


def _available_cores():
    if affinity := os.sched_getaffinity(0):
        return len(affinity)
    elif cpu_count := os.cpu_count():
        return cpu_count
    else:
        return 4


def apply_defaults(original, defaults):
    for key, value in defaults.items():
        if original.get(key) is None:
            original[key] = value


class ProgressBar(tqdm):
    def move(self, _):
        self.update()


class ProgressMixin:
    def _initalize(self):
        if not hasattr(self, "_pbar_stack"):
            self._pbar_stack = []

    @contextmanager
    def set_bar(self, *args, **kwargs):
        self._initalize()
        self._pbar_stack.append(ProgressBar(*args, **kwargs))
        yield self.bar
        self._pbar_stack.pop().close()

    @property
    def bar(self):
        self._initalize()
        if self._pbar_stack:
            return self._pbar_stack[-1]
        else:
            return None
