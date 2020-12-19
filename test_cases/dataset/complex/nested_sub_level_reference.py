def foo():  # reiz: tp
    if bar:
        return bar


def foo():  # reiz: tp
    if bar:
        return bar
    ...
    ...


def foo():
    if baz:
        return bar


def foo():
    if bar:
        return baz
    ...
    ...
