def foo(bar, /, baz):  # reiz: tp
    pass


def quux(bar, /, baz):  # reiz: tp
    print(baz)
    looooool()
    print(bar)


def foo(bar, baz):
    pass


def foo(baz, /, bar):
    print(1)
    print(2)


def quux(bar, /, something_else):
    pass


def quux(something_else, /, bar):
    pass


def empty(): ...


def maybe(*bar, **baz): ...


def only(bar, /):
    print(3)


def only(*, baz): ...
