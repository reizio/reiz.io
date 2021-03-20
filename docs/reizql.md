# ReizQL Language

ReizQL is a declarative query language for building AST matchers
that work on the Reiz platform.

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
start                   := match_pattern

pattern                 := negate_pattern
                         | or_pattern
                         | and_pattern
                         | match_pattern
                         | sequential_pattern
                         | reference_pattern
                         | match_string_pattern
                         | atom_pattern

negate_pattern          := "not" pattern
or_pattern              := pattern "|" pattern
and_pattern             := pattern "&" pattern
match_pattern           := NAME "(" ",".argument+ ")"
sequential_pattern      := "[" ",".(pattern | "*" IGNORE)+ "]"
reference_pattern       := "~" NAME
match_string_pattern    := "f" STRING

atom_pattern            := NONE
                         | STRING
                         | NUMBER
                         | IGNORE

argument                := pattern
                         | NAME "=" pattern

NONE                    := "None"
IGNORE                  := "..."
NAME                    := "a".."Z"
NUMBER                  := INTEGER | FLOAT
```

### Match Patterns

```bnf
match_pattern           := NAME "(" ",".argument+ ")"
```

A match pattern is the most fundamental part of a query. It consists
from a matcher name and fields to be matched. 


