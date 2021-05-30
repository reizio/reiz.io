# reiz.io

reiz.io is a structural source code search engine for Python. Compared to the
popular alternatives (e.g Github Code Search) it executes queries over the
syntax trees (instead of raw source code) and tries to retrive structural
knowledge (no semantics applied).

```{toctree}
:hidden:
:maxdepth: 1

reizql
internals
```

## Installation via Docker

A local instance of Reiz can be installed through `docker` and `docker-compose`
without any need to setup anythin else. It will run on a very small dataset (~75
files from 10 different projects) and will come with a bundled web interface.
Steps;

Get a fresh reiz clone

```
$ git clone https://github.com/reizio/reiz.io
```

Enter the directory and run `docker-compose up`

```
$ cd reiz.io
$ docker-compose up --build --remove-orphans
```

It will take about six to seven minutes for Reiz to initially build necessary
packages, install requirements, sample some packages for the dataset, prepare
the database and apply the schema, serialize those packages and finally run the
API.

```
reiz_1    | ... is inserted
reiz_1    | + python -m reiz.web.api
reiz_1    | [2021-04-24 21:35:38 +0000] [157] [INFO] Goin' Fast @ http://0.0.0.0:8000
reiz_1    | [2021-04-24 21:35:38,597] _helper         --- Goin' Fast @ http://0.0.0.0:8000
reiz_1    | [2021-04-24 21:35:38 +0000] [157] [INFO] Starting worker [157]
reiz_1    | [2021-04-24 21:35:38,929] serve           --- Starting worker [157]
```

After seeing the `Goin' Fast @ ...` message, you can open up your browser and
visit `http://localhost:8000/` and be greeted by the web UI.

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
