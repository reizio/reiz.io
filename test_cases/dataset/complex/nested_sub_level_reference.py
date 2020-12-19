@nested_sub_level_reference
def foo():  # reiz: tp
    if bar:
        return bar


@nested_sub_level_reference
def foo():  # reiz: tp
    if bar:
        return bar
    ...
    ...


@nested_sub_level_reference
def foo():
    if baz:
        return bar


@nested_sub_level_reference
def foo():
    if bar:
        return baz
    ...
    ...
