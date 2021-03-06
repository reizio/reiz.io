call(foo, bar=baz)  # reiz: tp
call(foo, bar=quux)  # reiz: tp

call(bar, bar=baz)
call(foo, bar, bar=baz)
call(foo, baz=bar)
call(foo, bar=baz, quux=bar)
