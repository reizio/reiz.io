def foo():  # reiz: tp
    return (a.x, b.x, c.x)


def foo():  # reiz: tp
    return (a.x, b, c.x)


def foo():  # reiz: tp
    return (a, b, c.x)


def foo():  # reiz: tp
    ...
    ...
    return (a, b, c.x)


def foo():  # reiz: tp
    ...
    ...
    return (a, b, c.x)


def foo():
    return (a, b, a)


def foo():
    return a.x


def foo():
    return a, b
