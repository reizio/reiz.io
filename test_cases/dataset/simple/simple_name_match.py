foo  # reiz: tp

if 2 + 2:
    bar  # reiz: tp
    baz()  # reiz: tp

SIMPLE_NAME_MATCH + x  # reiz: tp
True + False


def func():
    if test:  # reiz: tp
        return None


def foo():
    z << 1  # reiz: tp
