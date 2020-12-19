from contextlib import closing

import edgedb

from reiz.config import config


def get_new_connection(*args, **kwargs):
    kwargs.setdefault("database", config.database.database)
    connection = edgedb.connect(*args, dsn=config.database.dsn, **kwargs)
    return closing(connection)


def get_async_db_pool(*args, **kwargs):
    kwargs.setdefault("database", config.database.database)
    return edgedb.create_async_pool(dsn=config.database.dsn)
