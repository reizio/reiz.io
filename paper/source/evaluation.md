
# Evaluation

For the little subset of things that can be described in either of the competitor engines, we
evaluate the performance of `Reiz` by running similiar queries in Github Code Search and grep.app
and report back the amount of matches (true positives) and irrelevant results (false positives)
in the tables below.

The method of evaluation is running the queroes and analyzing the top 10 results. Some engines offer
multiple matches in a single result, so for the sake of simplicity we'll count them as true positive
if any of the matches are actually a true positive. Also the capture areas are ignored, since none of
the competitor can successfully capture only the individual expression/statement that is being searched.

## Comparisons

Objective: search for a `len(...)` call

| engine               | query                   | true positives | false positives |
|----------------------|-------------------------|----------------|-----------------|
| Github Code Search   | `language:python len()` | 5              | 5               |
| grep.app             | `len\((.*)\)`           | 10             | 0               |
| Reiz                 | `Call(Name("len"))`     | 10             | 0               |

Objective: search for an addition or a subtraction operation

| engine               | query                     | true positives | false positives |                                                                            |
|----------------------|---------------------------|----------------|-----------------|
| Github Code Search   | `language:python + -`     | 0              | 0               |
| grep.app             | `(.*)(\+|\-)(.*)`         | 2              | 8               |
| Reiz                 | `BinOp(op=Add() | Sub())` | 10             | 0               |

Objective: search for a return statement that returns a tuple `return ..., ...`

| engine             | query                          | true positives | false positives |
|--------------------|--------------------------------|----------------|-----------------|
| Github Code Search | `language:python return ,`     | 2              | 8               |
| grep.app           | `return ((.*))(,\s*(.*))+`     | 0              | 10              |
| grep.app (2)       | `return \(((.*))(,\s*(.*))+\)` | 9              | 1               |
| Reiz               | `Return(Tuple())`              | 10             | 0               |
