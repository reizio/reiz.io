from collections import Counter
from enum import Enum, auto


class Insertion(Enum):
    CACHED = auto()
    FAILED = auto()
    SKIPPED = auto()
    INSERTED = auto()


class Statistics(Counter):
    ...
