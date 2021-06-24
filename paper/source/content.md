# Summary

Reiz is a structural source code search engine that can execute queries written
in ReizQL to retrieve partially known syntactical constructs inside a
pre-processed source index.

# Statement of need

The fact that developers search source code every day is undeniable. This need
to search has various reasons by different groups of people. When introducing
new features to a language, developers often need to see what kind of an impact
that those will have before actually bothering to implement it (or even
discuss it in the first place). Prior to making any changes on a publicly
facing API, maintainers of those libraries do the pre-requisite work of
collecting samples and estimating the ramifications that operation might cause.
When the documentation of a framework doesn't sustain the curiosity, searching
for a structure (e.g a function, a constant) to see how it can be utilized in
real-world software is a common need among developers \[@developersearch2017\].

For the problems mentioned above, we present Reiz: a source code search engine
backend that can exercise queries to match syntax trees in order to leverage
the existing language syntax to describe partial knowledge (e.g a searching for
a `try`/ `finally` construct without knowing what is under the `try` block).

# State of the field

Popular source code search engines (e.g Github Code Search
\[@githubcodesearch\]) use full-text search where the code is treated no
differently than a regular textual document. Even though this approach works
for some basic queries, structurally it can't go further than matching token
sequences. This often causes seeing irrelevant search results on complex
queries, or even not being able to express the search itself in a purely
textual form. In the past, there has been some work done regarding making
queries more expressive through regular expressions (one example might
codesearch.debian.net \[@debiancodesearch\]), and even annotating the result
set with some semantic and structural knowledge (via finding and resolving API
names \[@BAJRACHARYA2014241\]). There also have been various tools \[@fast\],
\[@astsearch\] to search AST patterns within source code, but with a limited
query format and in a file-by-file basis (no index database) which makes them
quite hard to work with in order to examine a large dataset of source code.

# Method

![Stages from the Reiz's pipeline.](internals.png)

The internals consists of a pipeline that enables the ability to plug in and
out different components, such as for frontends of different languages. The
primary piece that every other component directly or indirectly interacts with
is the Index DB (a.k.a source warehouse) where the serialized AASTs (Annotated
Abstract Syntax Trees) are being held. It is based on an EdgeDB \[@edgedb\]
instance which interprets the compiled queries and returns the raw result set.
The schema used in the Index DB is in the format of ESDL (EdgeDB Schema
Definition Language) and automatically generated from the host language's ASDL
\[@asdl97\] declaration. ASDL is a common format used by many different
projects, most notably by CPython itself.

## Sampling Source Code

Reiz is able to sample source code from a list of projects on a git remote (e.g
GitHub). The reference implementation for Reiz comes with an indexer which can
automatically construct a list for the most popular packages on PyPI,
according to the download statistics \[@hugovankemenade_richardsi_2021\]. The
list then gets cross-linked to the project's corresponding source control
platforms (so that, we can reference the revision that we are fetching). Later
on, the data gets downloaded via `git` and then gets sanitized until there is
nothing left besides valid source files for the host language.

Subsequently, files get parsed to the AST form offered by the host language,
and then annotated with some static knowledge, so that the computation of these
properties won't cost anything at runtime. The annotations include node tags
(a unique identifier for a piece of AST that will be the same every time the
same structure is annotated, like tree hash), ancestral information (like a set
of 2-element tuples, where the first one points to the parent type and the the
second one points to the field that the child belongs to) and metadata
regarding the project (like the filename, project name, GitHub URL). Afterward
the annotated AST gets serialized into the Index DB.

## Query Compiler

```ebnf
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

The grammar above describes the ReizQL language which is embedded into the
execution engine. It can be used as is, or can be selected as a compilation
target for a higher level language that is more integrated with the syntax of
the host language.

Following query will search for all occurrences of a for loop, where the
target's `result` method is called subsequently in the loop body. The `target`
is an example of the reference pattern, which has a query-bound value (e.g if
the first `~target` capture is `X`, then the following capture is also expected
to be the same).

```
For(
    target=~target,
    body=[
        Expr(
            value=Call(
                func=Attribute(value=~target, attr="result")
            )
        )
    ],
)
```

The query in the example can be automatically generated through various forms,
as well as being hand written. For example, the IRun project targets ReizQL
with a python superset form to be a more human friendly interface to the
engine:

```
for $target in ...:
    $target.result()
```
