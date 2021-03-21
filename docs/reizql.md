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
atom_pattern            ::= NONE
                         | STRING
                         | NUMBER
                         | IGNORE
                         | "f" STRING

argument                ::= pattern
                         | NAME "=" pattern

NONE                    ::= "None"
IGNORE                  ::= "..."
NAME                    ::= "a".."Z"
NUMBER                  ::= INTEGER | FLOAT
```

## Match Patterns

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
/ `NamedExpr`, ...). The star (`*`) at the end of type declaration implies that
it requires a [sequential pattern](#list-patterns) where the member types
inherit from that base type (e.g `stmt*` might be something like
`[If(), If(), While()]`). The question mark (`?`) indicates the value is
optional and can be `None`.

If the values are not named (e.g `BinOp(Constant())`) then the name will be
positionally given (`BinOp(Constant(), Add())` will be transformed to
`BinOp(left=Constant(), op=Add()`).

### Example Queries

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

## Sequential Patterns

```bnf
sequential_pattern      ::= "[" ",".(pattern | "*" IGNORE)+ "]"
```

Sequential patterns represent a list of subpatterns that are combined together
to match a list on the host AST. If we want to search a function definition
where there are 2 statements, the first one being an if statement and the second
one is a return of an identifier named `status` then we simply describe this
query like this;

```py
FunctionDef(
    body = [
        If(),
        Return(
            Name('status')
        )
    ]
)
```

Sequential patterns are ordered, and matched one-to-one unless a
[ignore star](#ignore-star) is seen.

### Ignore Star

If any of the elements on the sequence pattern is a star (`*`) followed by an
[ignore](#ignore-atom) then the matchers before the ignore-star are relative
from the beginning and the matchers after the ignore-star are relative to the
end of the sequence. This implies that there is no maximum limit of items (in
contrast to normal sequential patterns, where the number of elements is always
fixed to amount of patterns seen) and the minimum being the total amount of
matchers (excluding the ignore star).

Let's say we want to find a function that starts with an if statement, and then
ends with a call to `fetch` function.

```py
FunctionDef(
    body = [
        If(),
        *...,
        Return(
            Call(
                Name(
                    'fetch'
                )
            )
        )
    ]
)
```

There might be any number of elements between the if statement and the return,
and it simply won't care.

:::{note} If you need a filler value (for example you want the minimum number of
statements to be 3 instead of 2 in the case above) you can use
[ignore atom](#ignore-atom).

```py
FunctionDef(
    body = [
        If(),
        ...,
        *...,
        Return(
            Call(
                Name(
                    'fetch'
                )
            )
        )
    ]
)
```

:::

### Example Queries

- Match all functions that have 2 statements and the last being a return

```py
FunctionDef(
    body = [
        ...,
        Return()
    ]
)
```

- Match all try/except's where the last except handler is a bare `except: ...`

```py
Try(
    handlers = [
        *...,
        ExceptHandler(
            type = None
        )
    ]
)
```

## Logical Patterns

Logical patterns are different patterns connected together in the sense of some
logical operation (either `AND` or `OR`)

### AND patterns

```bnf
and_pattern             ::= pattern "&" pattern
```

`AND` patterns chains 2 different pattern together and matches the host value if
it can be matched by both of the connected patterns.

### OR patterns

```bnf
or_pattern              ::= pattern "|" pattern
```

`OR` patterns chains 2 different pattern together and matches the host value if
it can be matched by either of the connected patterns.

### Example Queries

- Match a return statement that either returns a list literal or a tuple literal

```py
Return(List() | Tuple())
```

- Match an if statement where the first statement is an assign and the total
  number of statements lower/equal than 5

```py
If(
    body = [
        Assign(),
        *...
    ] & LEN(max=5)
)
```

## NOT Patterns

```bnf
negate_pattern          ::= "not" pattern
```

For checking whether a certain pattern *does not* match on the host AST, the
negation operator can be used.

:::{hint} If a value is described as an optional (`?`) on the ASDL, then the
existence of value can be denoted via `not None` pattern.

### Example Queries

- Match a return statement that doesn't return a call

```py
Return(not Call())
```

- A list that doesn't start with tuples or sets

```py
List(
    elts = [
        (not Tuple()) & (not List()),
        *...
    ]
)
```

## Reference Patterns

```bnf
reference_pattern       ::= "~" NAME
```

Reference patterns are query-bound variables that can be referred elsewhere and
the truthness determined by checking whether all the references point to the
same expression (structurally, not semantically) or not.

### Example Queries

- Match a function definition where the last statement calls another function with
  the same name

```py
FunctionDef(
    ~name,
    body = [
        *...,
        Expr(Call(Name(~name)))
    ]
)
```

- Match an if statement where the test is a compare operation with the same
  lhs/rhs (`a == a` / `b() is b()`)

```py
If(
    test = CompareOp(
        left=~comp_expr,
        comparators = [
            ~comp_expr
        ]
    )
)
```

## Atom Patterns

```bnf
atom_pattern            ::= NONE
                         | STRING
                         | NUMBER
                         | IGNORE
                         | "f" STRING
```

Atoms represents basic values (like integers, strings) and also some
ReizQL-flavored constructs.

### Ignore

```
IGNORE                  ::= "..."
```

Ignore is a construct that just omits matching that field/element (in contrary
to None, where it means that value does not exist).

### None

```
NONE                    ::= "None"
```

None represents the absence of the value

### Match String

```
MATCH_STRING            ::= "f" STRING
```

| Pattern | Interpretation |
|----------------|------------------------------------| | `%` | matches zero or
more characters | | `_` | matches exactly one character | | `\%`/`\_` | matches
the literal `%`/`_` |

Match strings can match alike strings via denoting some basic structures (like
starts/ends with some static text).

### Example Queries

- Match a string that starts with `http://` or `https://`

```py
Constant(f'http://%' & f'https://%') 
```

- Match an arg that doesn't have any type annotations

```py
arg(annotation = None)
```

## Builtin Matchers

There are a couple of builtin matchers (builtin functions) that can match
against certain conditions.

### ALL/ANY

**Signature**: `ALL($0: pattern)` / `ANY($0: pattern)`

Apply the given matcher (`$0`) to a sequence. `ALL` would check whether all
elements can be matched through the given argument, and any would check if any
of the elements would be matched.

### LEN

**Signature**: `LEN($0: Opt[INTEGER], $1: Opt[INTEGER])`

Checks whether the length of the sequence fits into `$0 <= <host AST> <= $1`.
The `$0`/`$1` are optional values but at least one of them should be specified.

### META

**Signature**: `META(**metadata_providers)`

Checks for various metadata information (like file names, project names, parent
types, etc).

### I

**Signature**: `I($0: atom_pattern[MATCH_STRING])`

Supports case insensitive match through match strings.

### Example Queries

- Match a tuple where all members are literals

```py
Tuple(ALL(Constant()))
```

- Match a function where one of the top level statements is an if statement

```py
FunctionDef(
    body = ANY(
        If()
    )
)
```

- Match a function call where there are minimum 3 positional arguments and 5
  maximum keyword arguments

```py
Call(
    args = LEN(min=3),
    keywords = LEN(max=5)
)
```

- Match a string in an case insensitive way

```py
Constant(I(f"foo"))
```
