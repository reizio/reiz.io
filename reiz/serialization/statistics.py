from collections import Counter, defaultdict
from enum import auto

from reiz.utilities import ReizEnum


class Insertion(ReizEnum):
    CACHED = auto()
    FAILED = auto()
    SKIPPED = auto()
    INSERTED = auto()


class Statistics(Counter):
    def __init__(self, *args, callbacks=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._callbacks = defaultdict(list, callbacks or {})

    def add_callback(self, target, callback):
        self._callbacks[target].append(callback)

    def __setitem__(self, target, value):
        super().__setitem__(target, value)
        self._trigger_callbacks(target, value)

    def update(self, other):
        super().update(other)
        # Due to a fast path embedded in Counter.update, the operation does
        # not always calls __setitem__ under the hood. This condition ensures
        # that the callbacks are triggered even if CPython decides to go with
        # the fast path. (cc: @3.8 Lib/collections/__init__.py#L634-L635)

        if other and not self:
            for target, value in other.items():
                self._trigger_callbacks(target, value)

    def _trigger_callbacks(self, target, value):
        for callback in self._callbacks[target]:
            callback(value)
