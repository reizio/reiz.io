from contextlib import closing
from functools import partial

import edgedb

DEFAULT_DSN = "edgedb://edgedb@localhost/"
DEFAULT_DATABASE = "asttests"


def connect(dsn, database, *args, **kwargs):
    return closing(edgedb.connect(dsn=dsn, database=database, *args, **kwargs))


simple_connection = partial(connect, DEFAULT_DSN, DEFAULT_DATABASE)
