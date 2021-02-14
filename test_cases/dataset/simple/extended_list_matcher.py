for x in y:  # reiz: tp
    a = 1

for y in z:  # reiz: tp
    continue
    b = 2

for x in y:  # reiz: tp
    continue

for x in y:  # reiz: tp
    continue
    try:
        ...
    except:
        ...

async for x in y:
    pass

async for y in z:
    continue
    continue

for x in y:
    break


def foo():
    pass


for x in y:
    continue
    x()

for x in y:
    foo()

for x in y:
    foo()
    continue

for x in y:
    break
    foo()

for x in y:
    try:
        break
    except:
        continue
    foo()
