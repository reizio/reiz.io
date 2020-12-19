@single_top_level
def foo():  # reiz: tp
    return foo()


@single_top_level
def foo():  # reiz: tp
    return foo()


@single_top_level
def foo():  # reiz: tp
    ...
    ...
    ...
    return foo()


@single_top_level
def bar():
    return foo()


@single_top_level
def foo():
    ...
    ...
    return bar()


@single_top_level
def foo():
    return foo()
    ...


@single_top_level
def foo():
    if x:
        return foo()
