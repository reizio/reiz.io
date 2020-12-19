SIMPLE_NAME_MATCH  # reiz: tp

if test:
    OTHER_NAME
    SIMPLE_NAME_MATCH  # reiz: tp

SIMPLE_NAME_MATCH + x  # reiz: tp
x + y


def func():
    if test:
        SIMPLE_NAME_MATCH  # reiz: tp


def foo():
    z << 1
    not q
    e(a, SIMPLE_NAME_MATCH)  # reiz: tp
