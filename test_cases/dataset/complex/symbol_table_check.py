@bar  # reiz: tp
@bar
def foo():
    baz
    baz.anything
    return foo()


@baz  # reiz: tp
@baz
def foo():
    baz
    baz.anything
    return foo()


@bar
@baz
def foo():
    xxx
    xxx.anything
    return foo()


@bar
@bar
def foo():
    bar
    xxx.anything
    return foo()


@bar
@bar
def uuu():
    xxx
    xxx.anything
    return foo()
