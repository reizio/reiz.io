import json
from dataclasses import asdict, dataclass
from typing import Optional

from reiz.serialization.transformers import ast


@dataclass
class SamplingData:
    name: str
    downloads: int
    git_source: str
    git_revision: Optional[str] = None
    license_type: Optional[str] = None

    dump = asdict

    def as_ast(self):
        return ast.project(self.name, self.git_source, self.git_revision)


def load_dataset(path):
    with open(path) as stream:
        projects = json.load(stream)

    return [SamplingData(**project) for project in projects]


def dump_dataset(path, projects):
    with open(path, "w") as stream:
        json.dump([project.dump() for project in projects], stream, indent=4)
