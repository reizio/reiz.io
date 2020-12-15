# ReizQL

ReizQL is a high level query language, that originated from
the concept of AST matchers. The nodes comes from the [ASDL](https://github.com/reizio/reiz.io/blob/master/static/Python-reiz.asdl);
```
module ReizQL {
    stmt = FunctionDef(identifier name, arguments args,
                       stmt* body, expr* decorator_list, expr? returns,
                       string? type_comment)
          | For(expr target, expr iter, stmt* body, stmt* orelse, string? type_comment)
          | AsyncFor(expr target, expr iter, stmt* body, stmt* orelse, string? type_comment)
          | While(expr test, stmt* body, stmt* orelse)
          | If(expr test, stmt* body, stmt* orelse)

    ...
    expr = BoolOp(boolop op, expr* values)
         | NamedExpr(expr target, expr value)
         | BinOp(expr left, operator op, expr right)
         | UnaryOp(unaryop op, expr operand)
    ...
}
```


The left handside's are named 'sum' types, or more broadly called as, 'base' types. The right
hand side is the 'constructor' types which are the actual nodes. So, for an example, `2 + 2`
represented as;
```
BinOp(
    left = Constant(2),
    op = Add(),
    right = Constant(2)
)
```

The ReizQL is actually a python subset, with different mechanics
that compiles to an intermediate query language called EdgeQL
which then transformed into SQL.

## Concepts
### Node matchers
Node matchers are actually like Python calls with both positional and keyword
arguments. The compiler will first try to subsitute all positional args into
the free fields, and then start consuming the keyword arguments (in case of
there are more than required / two values for the same field, the compiler
would raise an error)

```
matcher := NAME "(" ','.EXPR ','.NAMED_EXPR ")"
```
#### Examples
```
BinOp(Constant(1), operator = Add())
```
would mean the same thing with
```
BinOp(left=Constant(1), operator = Add())
```
which would match any of these cases;
```py
1 + sum([self._actorCount(asys1, C) for C in s.childActors])
1 + len(expected_prefix)
1 + d*x1*x2*y1*y2
1 + univ.Real('inf')
1 + 2 * x
```

#### Extra Matchers
We also have a couple standard matchers which are not actually AST nodes,
their naming convetion is different than the normal matchers and they are
all UPPER-CASE.

- `ALL($0)` is a sequence matcher that takes a single argument of a filter
  and will ensure all elements of the given sequence will be matched with 
  that filter.
- `ANY($0)` very similiar to `ALL($0)` but does the same thing if any of
  the items matched. Can be used to optimize cases where there is a set
  adapter with a single item.
- `LEN(min=$0?, max=$1?)` is a matcher to match the length of a list value.
  Can be either presented as `LEN(min=3, max=5)` or `LEN(min=3)`/`LEN(max=5)`.
  The minimum and the maximum range is included (think them like `>=`/`<=`)
  operators.

### Filters
Filters are common forms to describe the syntactic representation of
the target source code. They might be matchers (such as `left=Constant(1)`);
they might be list adapters, which means that both type and value is checked
(such as `body=[Assign(), Return()]`); or they might be ATOMs (such as
`Constant(1)` or `FunctionDef('foo')`)
```
filter := matcher
        | '[' (filter|expand)* ']'
        | ignore
        | or_filter
        | negated
        | attribute
        | ATOM
```

### The Ignore
The Ignore is a special constant (`...`) that represents any value.
For an example, if you want to match a function where there is 3
elements but all you care is whether the last element is a return
or not, you can basically query this `FunctionDef(body=[..., ..., Return()])`.

```
ignore := '...'
```

### Expand
Expand is like "The Ignore", a pseudo operator that allows you to operate
on a list where you don't know the total length but you know the positions
of items, like `Call(args=[Name(), *..., Name(), ...])` would match a list
where the first, and second from the last items are `Name()` nodes.

```
expand := '*' ignore
```

### Boolean Logic
We have a limited support for `OR` gates, such as `Constant(1 | 2)`.
Even though the syntax allows it, the generated queries take so long
to execute when used with other matchers like `Call(Name() | Attribute())`.
It is on our task list to optimize, and probably will come with Alpha 2.
```
or_filter := filter "|" filter
```

### Negativity
A simple unary `not` will be able to flip your query to 'not to' match,
like `Tuple(ALL(not Constant()))`.
```
negated := "not" filter
```

### Attribute
Fetch the value of an attribute, like `Tuple(lineno = not ~end_lineno)`.

```
attribute := '~' NAME
```

## Example Queries
Match all function definition where there is a `@classmethod` or a `@staticmethod`
decorator and the body consists of a single `return` statement which returns a tuple.
```py
FunctionDef(
    decorator_list=[
        Name('classmethod' | 'staticmethod')
    ],
    body = [..., Return(Call())]
)
```
