from contextlib import closing

import edgedb

from reiz.config import config


def _apply_defaults(kwargs):
    if config.database.options:
        kwargs.update(config.database.options)
    kwargs.setdefault("database", config.database.database)
    if not kwargs.get("host"):
        kwargs.setdefault("dsn", config.database.dsn)


def get_new_connection(*args, **kwargs):
    _apply_defaults(kwargs)
    connection = edgedb.connect(*args, **kwargs)
    return closing(connection)


def get_async_db_pool(*args, **kwargs):
    _apply_defaults(kwargs)
    return edgedb.create_async_pool(*args, **kwargs)
