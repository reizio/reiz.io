def foo():
    if ...:  # reiz: tp
        foo = bar
        return ...


def foo():
    if ...:  # reiz: tp
        foo = bar
        ...
        return ...


def foo():
    if ...:  # reiz: tp
        foo = bar
        foo()
        bar()
        return ...


def foo():
    if ...:  # reiz: tp
        foo = bar
        foo()
        bar()
        baz()
        return ...


def foo():
    if ...:
        foo = bar
        foo()
        bar()
        baz()
        not_this()
        return ...


def foo():
    if ...:
        foo = bar
        ...
        ...
        ...
        ...
        return ...


def foo():
    with ... as some:
        foo = bar
        foo()
        not_this()
        return ...
