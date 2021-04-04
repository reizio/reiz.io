import json
import random
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

    @staticmethod
    def dump(data_file, instances, *, random_order=False):
        dictified_instances = [asdict(instance) for instance in instances]
        if random_order:
            random.shuffle(dictified_instances)

        with open(data_file, "w") as stream:
            json.dump(dictified_instances, stream, indent=4)

    @classmethod
    def load(cls, data_file, *, random_order=False):
        with open(data_file) as stream:
            instances = json.load(stream)

        instances = [cls(**instance) for instance in instances]
        if random_order:
            random.shuffle(instances)
        return instances

    @classmethod
    def iter_load(cls, *args, **kwargs):
        return iter(cls.load(*args, **kwargs))

    def as_ast(self):
        return ast.project(self.name, self.git_source, self.git_revision)
