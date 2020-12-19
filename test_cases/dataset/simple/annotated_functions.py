def foo() -> int:  # reiz: tp
    pass


def foo() -> List[str]:  # reiz: tp
    ...
    ...


def foo():
    pass


async def foo() -> List[str]:
    ...


async def foo():
    ...
