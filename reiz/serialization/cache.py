from dataclasses import dataclass, field
from typing import Set

from reiz.ir import IR


@dataclass
class Cache:
    files: Set[str] = field(default_factory=set)
    projects: Set[str] = field(default_factory=set)
    auto_sync: bool = False

    def __post_init__(self):
        if self.auto_sync:
            with get_new_connection() as connection:
                self.sync(connection)

    def sync(self, connection):
        query_set = connection.query(IR.query("module.filenames"))
        self.files = {module.filename for module in query_set}

        query_set = connection.query(IR.query("project.names"))
        self.projects = {project.name for project in query_set}
