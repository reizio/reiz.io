from dataclasses import dataclass, field
from typing import Set

from reiz.database import get_new_connection
from reiz.ir import IR


@dataclass
class Cache:
    files: Set[str] = field(default_factory=set)
    projects: Set[str] = field(default_factory=set)

    @classmethod
    def from_db(cls):
        cache = cls()
        with get_new_connection() as connection:
            cache.sync(connection)
        return cache

    def sync(self, connection):
        query_set = connection.query(IR.construct_prepared("module.filenames"))
        self.files = {module.filename for module in query_set}

        query_set = connection.query(IR.construct_prepared("project.names"))
        self.projects = {project.name for project in query_set}
