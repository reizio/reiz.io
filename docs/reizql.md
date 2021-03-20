# ReizQL Language

ReizQL is a declarative query language for building AST matchers that work on
the Reiz platform.

:::{hint} Here is an example ReizQL query that searches for an if statement
where the body consists from a single assignment statement that assigns the
result of `requests.get(...)` call's result into a variable named `response`

```
if cache.invalidated:
    response = requests.get('https://api.reiz.io/refresh')
```

:::

```py
If(
    body = [
        Assign(
            targets = [
                Name('response')
            ],
            value = Call(
                Attribute(
                    Name('requests'),
                    'get'
                )
            )
        )
    ]
)
```

## Full Grammar

```bnf
start                   ::= match_pattern

pattern                 ::= negate_pattern
                         | or_pattern
                         | and_pattern
                         | match_pattern
                         | sequential_pattern
                         | reference_pattern
                         | match_string_pattern
                         | atom_pattern

negate_pattern          ::= "not" pattern
or_pattern              ::= pattern "|" pattern
and_pattern             ::= pattern "&" pattern
match_pattern           ::= NAME "(" ",".argument+ ")"
sequential_pattern      ::= "[" ",".(pattern | "*" IGNORE)+ "]"
reference_pattern       ::= "~" NAME
match_string_pattern    ::= "f" STRING

atom_pattern            ::= NONE
                         | STRING
                         | NUMBER
                         | IGNORE

argument                ::= pattern
                         | NAME "=" pattern

NONE                    ::= "None"
IGNORE                  ::= "..."
NAME                    ::= "a".."Z"
NUMBER                  ::= INTEGER | FLOAT
```

### Match Patterns

```bnf
match_pattern           ::= NAME "(" ",".argument+ ")"
```

Match patterns are the most fundamental part of the query expression. They
consist from an identifier (matcher name) which corresponds to an AST node type,
additionally they take any number of fields to be matched (values, optionally
attached with the corresponding field names).

All node types and fields are described in the
[Abstract Grammar](https://docs.python.org/3.8/library/ast.html#abstract-grammar)
of Python. Here are some entries from the ASDL;

```
module Python
{
    ...
    stmt = FunctionDef(identifier name, arguments args,
                       stmt* body, expr* decorator_list, expr? returns,
                       string? type_comment)
          | While(expr test, stmt* body, stmt* orelse)
          | If(expr test, stmt* body, stmt* orelse)
          | With(withitem* items, stmt* body, string? type_comment)

    expr = BoolOp(boolop op, expr* values)
         | NamedExpr(expr target, expr value)
         | BinOp(expr left, operator op, expr right)
         | UnaryOp(unaryop op, expr operand)
         | Lambda(arguments args, expr body)
         | IfExp(expr test, expr body, expr orelse)
         | Dict(expr* keys, expr* values)
```

The left hand side is the name of the base type, `stmt` would be a matcher that
could match all of the types in its right hand side (e.g `stmt()` would match
`FunctionDef()` / `While()` / `If()` / `With()`). Each element on the right hand
side are concrete matchers for that element in syntax. For example a `BinOp()`
represents a binary operation (2 operands), like `2 + 2` or `a % b()`.

Each element on the right hand side have different fields with types attached to
them. So the `BinOp()` node has 3 fields: `left`, `op`, `right` (respectively
they mean left hand side, operator, right hand side of an arithmetic operation).
`left` and the `right` must be another matcher from the `expr` base type (`BoolOp`
/ `NamedExpr`, ...). The star (`*`) at the end of type implies that it requires
a [list pattern](#list-pattern) that consists from that type (e.g `stmt*` might
be something like `[If(), If(), While()]`). The question mark (`?`) indicates
the value is optional and can be `None`.

If the values are not named (e.g `BinOp(Constant())`) then the name will be
positionally given (`BinOp(Constant(), Add())` will be transformed to
`BinOp(left=Constant(), op=Add()`).

#### Example Queries

- Match the `1994` literal

```py
Constant(1994)
```

- Match a binary operation where both sides are literals

```py
BinOp(left=Constant(), right=Constant())
```

- Match an (ternary) if expression that checks `a.b`'s truthness

```py
IfExp(
    test = Attribute(
        Name('a'),
        attr = 'b'
    )
)
```
