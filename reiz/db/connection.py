from contextlib import closing
from functools import partial

import edgedb

DEFAULT_DSN = "edgedb://edgedb@localhost/"
DEFAULT_TABLE = "asttests"


def connect(*args, **kwargs):
    return closing(edgedb.connect(*args, **kwargs))


simple_connection = partial(connect, DEFAULT_DSN + DEFAULT_TABLE)
