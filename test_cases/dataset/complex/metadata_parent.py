if something():  # reiz: tp
    ...

if 1:
    something()
elif something():  # reiz: tp
    ...

foo = bar if something() else baz

if 1:
    something()

if 2:
    ...
else:
    something()

if 1:
    ...
elif 2:
    something()
else:
    ...

for x in y:
    something()

while something():
    ...
