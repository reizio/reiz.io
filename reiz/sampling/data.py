import json
from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class SamplingData:
    name: str
    downloads: int
    git_source: str
    git_revision: Optional[str] = None

    dump = asdict

    @staticmethod
    def dump(data_file, instances):
        dictified_instances = [asdict(instance) for instance in instances]

        with open(data_file, "w") as stream:
            json.dump(dictified_instances, stream)

    @classmethod
    def load(cls, data_file):
        with open(data_file) as stream:
            instances = json.load(stream)

        return [cls(**instance) for instance in instances]
