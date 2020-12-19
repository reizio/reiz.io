class T:  # reiz: tp
    @STARTS_WITH_CLASSMETHOD
    def _():
        ...


class Z:  # reiz: tp
    @STARTS_WITH_CLASSMETHOD
    def _():
        ...


class Q:
    def _():
        ...

    @STARTS_WITH_CLASSMETHOD
    def __():
        ...


class Q:
    @OTHER_DECORATOR
    def _():
        ...
