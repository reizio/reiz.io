def foo():
    ...
    ...
    return bar  # reiz: tp


def bar():
    return bar, baz  # reiz: tp


def lol():
    return bar.baz, baz  # reiz: tp


def baz():
    return [bar, baz]


def quux():
    return bar.baz


def lol():
    return [bar.baz, baz]
