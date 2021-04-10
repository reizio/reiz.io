from collections import Counter
from enum import auto

from reiz.utilities import ReizEnum


class Insertion(ReizEnum):
    CACHED = auto()
    FAILED = auto()
    SKIPPED = auto()
    INSERTED = auto()


class Statistics(Counter):
    ...
