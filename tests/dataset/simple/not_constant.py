def foo():
    return print(bar)  # reiz: tp


def foo():
    return baz + quux  # reiz: tp


def foo():
    return lambda: rollo  # reiz: tp


def foo():
    return "x" + "y"  # reiz: tp


def foo():
    return "x"


def bar():
    return 200000


def baz():
    return 2000000e12
