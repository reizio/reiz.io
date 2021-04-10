import math
import tokenize
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List

from reiz.config import config
from reiz.database import DatabaseConnection
from reiz.sampling import SamplingData
from reiz.serialization.cache import Cache
from reiz.serialization.statistics import Insertion
from reiz.serialization.transformers import ast, prepare_ast
from reiz.utilities import picker

_AVG_CHARS = 80 * 80


class Context:
    def as_ast(self):
        raise NotImplementedError

    def new_child(self):
        raise NotImplementedError

    def apply_constraints(self, statistics):
        raise NotImplementedError

    @contextmanager
    def enter_node(self, node):
        yield

    def cache(self):
        return None

    def is_cached(self):
        return False


@dataclass
class GlobalContext(Context):
    db_cache: Cache = field(default_factory=Cache.from_db)
    properties: Dict[str, Any] = field(default_factory=dict)

    def new_child(self, project, *args, **kwargs):
        return ProjectContext(project, self, *args, **kwargs)


@dataclass
class ProjectContext(
    Context, picker("global_ctx"), inherits=("db_cache", "properties")
):
    project: SamplingData
    global_ctx: GlobalContext
    connection: DatabaseConnection

    def as_ast(self):
        return self.project.as_ast()

    def new_child(self, file, *args, **kwargs):
        return FileContext(file, self, *args, **kwargs)

    def apply_constraints(self, statistics):
        return statistics[Insertion.INSERTED] > 10

    @cached_property
    def path(self):
        return config.data.path / self.project.name

    @cached_property
    def limit(self):
        return self.properties.get("max_files", math.inf)

    def cache(self):
        self.db_cache.projects.add(self.project.name)

    def is_cached(self):
        return self.project.name in self.db_cache.projects


@dataclass
class FileContext(
    Context,
    picker("project_ctx"),
    inherits=("db_cache", "connection", "properties"),
):
    file: Path
    project_ctx: ProjectContext

    stack: List[ast.AST] = field(default_factory=list)
    reference_pool: List[uuid.UUID] = field(default_factory=list)

    def as_ast(self):
        with tokenize.open(self.file) as stream:
            source = stream.read()

        if self.apply_constraints(len(source)):
            return None

        tree = prepare_ast(ast.parse(source))
        tree.project = self.project_ctx.as_ast()
        tree.filename = self.filename
        return tree

    def apply_constraints(self, statistics):
        return statistics >= self.limit

    def new_reference(self, object_id):
        self.reference_pool.append(object_id)

    @contextmanager
    def enter_node(self, node):
        try:
            self.stack.append(node)
            yield
        finally:
            self.stack.pop()

    @property
    def flows_from(self):
        if len(self.stack) >= 1:
            return self.stack[-1]
        else:
            return None

    @cached_property
    def filename(self):
        return str(self.file.relative_to(config.data.path))

    @cached_property
    def limit(self):
        if self.properties.get("fast_mode"):
            return _AVG_CHARS
        else:
            return math.inf

    def cache(self):
        self.db_cache.files.add(self.filename)

    def is_cached(self):
        return self.filename in self.db_cache.files
