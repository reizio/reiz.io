# ReizQL -- Language Reference

ReizQL is a pattern matching language, for the [Python's AST](https://docs.python.org/3.8/library/ast.html#abstract-grammar). It
allows users to describe and match nested, sequential, and ambiguous syntactic patterns in ease.

```
start                   := match_pattern

pattern                 := negatated_pattern
                         | or_pattern
                         | and_pattern
                         | match_pattern
                         | sequential_pattern
                         | reference_pattern
                         | atom_pattern

negate_pattern          := 'not' pattern
or_pattern              := pattern '|' pattern
and_pattern             := pattern '&' pattern
match_pattern           := NAME '(' ','.argument+ ')'
reference_pattern       := "~" NAME
sequential_pattern      := '[' ','.(pattern | '*' IGNORE)+ ']'

atom_pattern            := NONE
                         | STRING
                         | NUMBER
                         | IGNORE

argument                := pattern
                         | NAME '=' pattern

NONE                    := 'None'
IGNORE                  := '...'
NAME                    := 'a'..'Z'
NUMBER                  := INTEGER | FLOAT
STRING                  := QUOTE (.?*) QUOTE
```

## Patterns
A pattern may be any of these things;

### Logical Pattern
#### NOT pattern
A logical NOT operator that matches anything but the operand.
```py
Call(not Name())
```
would match all `Call()`s where the function is not a `Name()` node.

#### OR pattern
A logical OR operator that connects 2 different patterns together.
```py
Call(Name() | Attribute())
```
would yield all `Call()`s where the function is either `Name()` or `Attribute()`.

#### AND pattern
A logical AND operator, works just like the `OR pattern`, useful when combined
on built-in matchers such as `LEN()` or `ANY()`.
```py
Call(args=[*..., Name()] & LEN(min=7))
```
would yield all `Call()`s where the last argument is a `Name()` node, and the
arguments list has the minimum length of 7.


### Match Patterns

A match pattern consists from a matcher, and a set of positional / keyword
arguments. The matcher is either a built-in function (such as `ALL`) or an
AST node from the [Python's Abstract Grammar](https://docs.python.org/3.8/library/ast.html#abstract-grammar).

#### Built-in Matchers
##### `ALL($0)` / `ANY($0)`
These functions are generalized sequence filtering mechanizms to verify that
all or any elements of the given sequence matches the inner query `$0`. The `ALL()`
will act like a reducer which would test every element on the given sequence with
the given pattern, and try to reduce the results with an `AND` gate. On the other
hand, the `ANY` will do the same thing with an `OR` gate.

```py
Call(args=ALL(Constant()))
Call(args=ANY(Attribut()))
```
##### `LEN(min=$0, max=$1)`
`LEN` is a special utility for ensuring that the length of the matched sequence
fits the given range. It can either take them both or `min` and `max` indivudually.
The `min` is translated to `len(sequence) >= $0`, and the max is translated to
`len(sequence) <= $1`. The `LEN(min=x, max=y)` is a syntactic sugar for `LEN(min=x) & LEN(max=y)`.

```py
Call(args=LEN(min=3))
Call(args=LEN(max=7))
Call(args=LEN(min=5, max=8))
```
##### `ATTR($0)`
Some types in the [Python's ASDL](https://docs.python.org/3.8/library/ast.html#abstract-grammar)
are annotated with some attributes (can be seen at the end of declarations). These attributes
are often used for positional information (such as the start line of the node etc). `$0` can be
any attribute's value, so that it can be used in a check. A quick example to find all multi-line
assignments;

```py
Assign(lineno = not ATTR(end_lineno))
```


#### AST matchers
The nodes in the [Python's ASDL](https://docs.python.org/3.8/library/ast.html#abstract-grammar) described in this format;
```
<matcher category> = <matcher name>(<field type><field qualifier> <field name>, ...)`
                   | ...
```


The `<field type>` may correspond to a sequence of AST node types (such as `expr`) or only one (such as `withitem`). If it
corresponds to a sequence, the value to be matched can be any of the types that is a member to that *sum* type. The qualifier
that follows the `<field type>` is an optional value that represents value spec for the given type. If there is no qualifier
the value is required, if there is;
- `*` qualifier means the value of that field is a sequence of items that belongs to the `<field type>`
- `?` qualifier means that value is optional, and may be `None`.

When a matcher is initalized (such as `ClassDef('lol')`) the positional arguments will fill
the fields left to right, on the other hand keyword arguments will only fill the fields
that they correspond to.

Example

```py
Name()
Attribute(Name(), attr='foo')
FunctionDef(name='foo', body=LEN(max=5))
```

### Reference Pattern
Reiz allows you to give internal references to values of the executed query. These can be thought as
(some sort of) `variables`. Basically it will try to match the references with each other.

```py
Module(
    body = [
        FunctionDef(
            ~name,
            body = [
                *...,
                Expr(
                    Call(
                        Name(~name)
                    )
                )
            ]
        ),
        *...
    ]
)
```


### Sequential Pattern

A sequential pattern consist start with a `[` (LEFT BRACKET) and end with a `]` (RIGHT
BRACKET). It matches a list of items, one by one with the given sequence. For example,
if you want to match a list of length 3 where the first and the second item is a `Name()`
and the third item is anything, you can simply right `[Name(), Name(), ...]`. Each element
of this sequence is an individual match.


If the length of list is uncertain, an expansion may be used `*...` (ASTERISK directly
followed by an IGNORE token). This would mean that, after that point, there can be zero
or more items. An example would be `[*..., Name(), ...]`, which would match all lists where
the second from the last item is a `Name()`. Or `[Name, *..., Attribute()]` would match any
list where the initial and last item is matched with the given patterns and ignoring the length.

```py
ClassDef(
    body=[
        FunctionDef(),
        FunctionDef(),
        Assign(targets=[Name()])
    ]
)
FunctionDef(body=[Expr(), ..., Return()])
Call(args=[Name(), *..., Attribute(), ..., ....])
```

### Atom Pattern

Atom's are the literals (like string, integer) and the special `IGNORE` token. `IGNORE`
is just like `pass`. It has no real effect but just being a place holder.
