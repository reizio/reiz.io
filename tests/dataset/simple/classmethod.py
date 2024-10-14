@classmethod  # reiz: tp
def foo(): ...


@classmethod  # reiz: tp
@staticmethod
def foo():
    ...
    ...


@staticmethod
def foo(): ...


@staticmethod
@classmethod
def foo():
    ...
    ...
