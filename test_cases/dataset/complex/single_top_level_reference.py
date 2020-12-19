def foo():  # reiz: tp
    return foo()


def foo():  # reiz: tp
    return foo()


def foo():  # reiz: tp
    ...
    ...
    ...
    return foo()


def bar():
    return foo()


def foo():
    ...
    ...
    return bar()


def foo():
    return foo()
    ...


def foo():
    if x:
        return foo()
