from collections import deque
from contextlib import ExitStack, closing, contextmanager

import edgedb
import edgedb.blocking_con
from edgedb.errors import ConstraintViolationError
from edgedb.errors import InternalServerError as InternalDatabaseError

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
        self._conn_args = con_args
        self._conn_kwargs = con_kwargs
        self._free_conns = deque()
        self._total_conns = 0
        self._exit_stack = ExitStack()

    def acquire(self):
        if self._free_conns:
            return self._free_conns.popleft()
        else:
            context = get_new_connection(*self._conn_args, **self._conn_kwargs)
            self._total_conns += 1
            return self._exit_stack.enter_context(context)

    def release(self, connection):
        self._free_conns.append(connection)

    def close(self):
        self._exit_stack.close()

    @contextmanager
    def new_connection(self):
        connection = self.acquire()
        try:
            yield connection
        finally:
            self.release(connection)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __str__(self):
        return f"{self.__class__.__name__}(free_connections={len(self._free_conns)}, total_connections={self._total_conns})"
