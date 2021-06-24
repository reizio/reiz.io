
# Evaluation

For the limited subset of things that can be described in any of the competitor engines, we
evaluate the performance of `Reiz` by running similiar queries in Github Code Search \[@githubcodesearch\]
grep.app \[@grepapp\] and Krugle \[@krugle\] and report back the amount of true / false positives. Each
result that contains an exact match with the intended objective, e.g a call to `len(...)` function will
be counted as a true positive, and otherwise will be counted as a false positive.  Some engines offer
multiple matches per result, and they will be marked as true positive if any of them checks out with
the objective. We also discard match spans, since none of the competitors can successfully display
the expression boundaries.

Objective: search for a `len(...)` call

| engine               | query                          | true positives | false positives |
|----------------------|--------------------------------|----------------|-----------------|
| Github Code Search   | `language:python len()`        | 5              | 5               |
| grep.app             | `len\((.*)\)`                  | 10             | 0               |
| Krugle (advanced)    | `len functioncall:len`         | 10             | 0               |
| Reiz                 | `Call(Name("len"))`            | 10             | 0               |

Objective: search for an addition or a subtraction operation

| engine               | query                          | true positives | false positives |
|----------------------|--------------------------------|----------------|-----------------|
| Github Code Search   | `language:python + -`          | 0              | 0               |
| Krugle (fuzzy)       | `expr + expr` / `expr - expr`  | 0              | 0               |
| Krugle (solr syntax) | `\+ \-`                        | 2              | 8               |
| Krugle (regex syntax)| `(.*)(\+\|\-)(.*)`             | 1              | 9               |
| grep.app             | `(.*)(\+\|\-)(.*)`             | 2              | 8               |
| Reiz                 | `BinOp(op=Add() \| Sub())`     | 10             | 0               |

Objective: search for a return statement that returns a tuple `return ..., ...`

| engine               | query                          | true positives | false positives |
|----------------------|--------------------------------|----------------|-----------------|
| Github Code Search   | `language:python return ,`     | 2              | 8               |
| Krugle (solr syntax) | `return \,`                    | 1              | 9               |
| Krugle (regex syntax)| `return ((.*))(,\s*(.*))+`     | 0              | 10              |
| grep.app             | `return ((.*))(,\s*(.*))+`     | 0              | 10              |
| grep.app (2)         | `return \(((.*))(,\s*(.*))+\)` | 9              | 1               |
| Reiz                 | `Return(Tuple())`              | 10             | 0               |


## Conclusion

On all three objectives, Reiz got all the matches as true-positive due to due to it's ability to
leverage syntax tree structure as well as other annotations that it could collect at pre-processing
stage (such as node boundaries to report the exact location) unlike others where the source code is
exercised like a regular textual document.
