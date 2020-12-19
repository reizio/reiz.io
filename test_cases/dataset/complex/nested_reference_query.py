class Foo:  # reiz: tp
    def recursive(self):
        recursive()


class Bar:  # reiz: tp
    def recursive(self):
        recursive()

    ...


class Baz:
    def recursive(self):
        return recursive()

    ...
    ...


class Foo:
    def recursive(self):
        recursivex()


class Foo:
    def recursive(self):
        return recursivex()

    ...
    ...


def recursive():
    recursive()


def recursive():
    @nested_query_reference
    def recursivee():
        recursive()
