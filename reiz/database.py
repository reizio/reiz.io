from contextlib import closing
from functools import partial

import edgedb

from reiz.config import config


def get_new_raw_connection(*args, **kwargs):
    connection = edgedb.connect(*args, dsn=config.database.dsn, **kwargs)
    return closing(connection)


get_new_connection = partial(
    get_new_raw_connection, database=config.database.database
)
