@foo  # reiz: tp
def something():
    @bar(baz(quux), foo)
    def something():
        ...

    if foo:
        for bar in baz:
            return quux()


@foo
def something():
    @bar(baz(quux), foo)
    def something():
        ...

    if foo:
        for bar in baz:
            return quux()

    ...


@foo.bar
def something():
    @bar(baz(quux), foo)
    def something():
        ...

    if foo:
        for bar in baz:
            return quux()


@foo
def something():
    @bar(baz(quux, quux), foo)
    def something():
        ...

    if foo:
        for bar in baz:
            return quux()


@foo
def something():
    @bar(baz(quux), foo, bar)
    def something():
        ...

    if foo:
        for bar in baz:
            return quux()


@foo
def something():
    @bar(baz(), foo)
    def something():
        ...

    if foo:
        for bar in baz:
            return quux()


@foo
def something():
    @bar(foo, foo)
    def something():
        ...

    if foo:
        for bar in baz:
            return quux()


@foo
def something():
    @bar
    def something():
        ...

    if foo:
        for bar in baz:
            return quux()


@foo
def something():
    @bar(baz(quux), foo)
    class something:
        ...

    if foo:
        for bar in baz:
            return quux()


@foo
def something():
    @bar(baz(quux), foo)
    def something():
        ...

    while True:
        for bar in baz:
            return quux()


@foo
def something():
    @bar(baz(quux), foo)
    def something():
        ...

    if foo:
        for bar in baz:
            return quux(a, b)


@foo
def something():
    @bar(baz(quux), foo)
    def something():
        ...

    if foo:
        for bar in baz:
            return quux()
        something()
