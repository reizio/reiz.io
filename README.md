<p align="center"><img src="https://github.com/reizio/reiz.io/blob/master/static/assets/reiz.png"></p>

# reiz.io

reiz.io is a structural source code search engine for Python. Compared to the
popular alternatives (e.g Github Code Search) it executes queries over the
syntax trees (instead of raw source code) and tries to retrive structural
knowledge (no semantics applied). For more information, please see the
[docs](https://reizio.readthedocs.io/en/latest/).

## A gentle introduction

Reiz is the code search framework that reiz.io is built a top on. Due to it's
nature, it solely works with the ASTs and intentionally avoids doing any
semantical work.

```{note}
Some ASTs attach a bit of contextual knowledge (e.g `Name(ctx=...)`
on python) which can be queried through simple matcher queries but
reiz.io doesn't include them when comparing references (see
matchers#reference-matcher for details).
```

Here is a simple ReizQL query that searches for a function that ends with a try
statement where we return a call to a function that has the same name as the
function we are within.

```python
FunctionDef(~func, body=[*..., Try(body=[Return(Call(Name(~func)))])])
```

which would match the following;

```py
def foo(spam):
    eggs = bar()
    try:
        return foo(spam + eggs)
    except ValueError:
        return None
```

In the very basic sense, it is generating the AST of the code above and checks
whether it fits the *pattern* (ReizQL query) or not.;

```py
FunctionDef(
    name='foo',
    args=arguments(
        posonlyargs=[],
        args=[arg(arg='spam', annotation=None, type_comment=None)],
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[],
    ),
    body=[
        Assign(
            targets=[Name(id='eggs', ctx=Store())],
            value=Call(
                func=Name(id='bar', ctx=Load()),
                args=[],
                keywords=[],
            ),
            type_comment=None,
        ),
        Try(
            body=[
                Return(
                    value=Call(
                        func=Name(id='foo', ctx=Load()),
                        args=[
                            BinOp(
                                left=Name(id='spam', ctx=Load()),
                                op=Add(),
                                right=Name(id='eggs', ctx=Load()),
                            ),
                        ],
                        keywords=[],
                    ),
                ),
            ],
            handlers=[
                ExceptHandler(
                    type=Name(id='ValueError', ctx=Load()),
                    name=None,
                    body=[
                        Return(
                            value=Constant(value=None, kind=None),
                        ),
                    ],
                ),
            ],
            orelse=[],
            finalbody=[],
        ),
    ],
    decorator_list=[],
    returns=None,
    type_comment=None,
)
```
