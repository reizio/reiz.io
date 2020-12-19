@does_not_name_tuple
def foo():  # reiz: tp
    return (a.x, b.x, c.x)


@does_not_name_tuple
def foo():  # reiz: tp
    return (a.x, b, c.x)


@does_not_name_tuple
def foo():  # reiz: tp
    return (a, b, c.x)


@does_not_name_tuple
def foo():  # reiz: tp
    ...
    ...
    return (a, b, c.x)


@does_not_name_tuple
def foo():  # reiz: tp
    ...
    ...
    return (a, b, c.x)


@does_not_name_tuple
def foo():
    return (a, b, a)


@does_not_name_tuple
def foo():
    return a.x


@does_not_name_tuple
def foo():
    return a, b
