def foo():  # reiz: tp
    some_call()
    return some_call()


def foo():  # reiz: tp
    some_other_call()
    return some_other_call()


def foo():  # reiz: tp
    some_other_call(with_, some_=args)
    ...
    ...
    return some_other_call(with_, some_=args)


def foo():  # reiz: tp
    some_other_call(with_, *some, other=stuff, **to)
    ...
    ...
    return some_other_call(with_, *some, other=stuff, **to)


def foo():
    other_call()
    return some_call()


def foo():
    some_call()
    return other_call()


def foo():
    some_other_call(with_, some_=args)
    ...
    ...
    return some_other_call(with_, some_different=args)


def foo():
    some_other_call(with_, some_=args)
    ...
    ...
    return some_other_call(with_, some_)


def foo():
    some_other_call(with_, some_)
    ...
    ...
    return some_other_call(with_, some_, maybe)


def foo():
    some_other_call(with_, some, other=stuff, **to)
    ...
    ...
    return some_other_call(with_, *some, other=stuff, **to)


def foo():
    some_other_call(with_, some, other=stuff, **to)
    ...
    ...
    return some_other_call(with_, some, other=stuff, to=1)
