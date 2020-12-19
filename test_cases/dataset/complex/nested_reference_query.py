@nested_query_reference
class Foo:  # reiz: tp
    def recursive(self):
        recursive()


@nested_query_reference
class Bar:  # reiz: tp
    def recursive(self):
        recursive()

    ...


@nested_query_reference
class Baz:
    def recursive(self):
        return recursive()

    ...
    ...


@nested_query_reference
class Foo:
    def recursive(self):
        recursivex()


@nested_query_reference
class Foo:
    def recursive(self):
        return recursivex()

    ...
    ...


@nested_query_reference
def recursive():
    recursive()


@nested_query_reference
def recursive():
    @nested_query_reference
    def recursivee():
        recursive()
