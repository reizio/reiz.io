from contextlib import closing, contextmanager

import edgedb

from reiz.config import config

DatabaseConnection = edgedb.blocking_con.BlockingIOConnection


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


class ConnectionPool:
    def __init__(self, *con_args, **con_kwargs):
        self._con_args = con_args
        self._con_kwargs = con_kwargs

    def acquire(self):
        if self._free_pool:
            return self._free_pool.popleft()
        else:
            return get_new_connection(*self._con_args, **self._con_kwargs)

    def release(self, connection):
        self._free_pool.append(connection)

    @contextmanager
    def new_connection(self):
        try:
            connection = self.acquire()
            yield connection
        finally:
            self.release(connection)
