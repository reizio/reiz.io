# Performance Evaluation

| query                                            | timing (s) |
| ------------------------------------------------ | ---------- |
| `Call(Name("len"))`                              | 0.025985   |
| `BinOp(op=Add() \| Sub())`                       | 0.030508   |
| `Try(handlers=LEN(min=3, max=5))`                | 0.033486   |
| `BinOp(left=Constant(), right=Constant())`       | 0.146516   |
| `FunctionDef(f"run_%", returns = not None)`      | 0.0216     |
| `ClassDef(body=[Assign(), *..., FunctionDef()])` | 0.28737    |

## Analysis

There are 2 major points that cost nearly %95 of the whole query operation. The first,
and the obvious point is the actually running the query in the database. There are a couple
points that Reizc an do to optimize this step, including trying to generate the best
possible query while being in a linear motion (for supporting constructs like reference
variables). The code generator (`reiz.reizql.compiler`) went through a couple major
refactors for performance reasons (e.g [#12](https://github.com/reizio/reiz.io/pull/12)).
Also there is a simple/naive [AST optimization pass](https://github.com/reizio/reiz.io/blob/cff3cc6eaad532ac1a956c1f7c7a58d97ea00e4b/reiz/ir/backends/edgeql.py#L461-L513) on
the IR (EdgeQL) itself.

The second part is the actually retrieving the code snippets from the disk itself. We
already store a lot of metadata (like start/end positions, github project etc.) but
the actual 'source' is still on the disk. So after retrieving the filenames from the
query, we simply go and read those files and get the related segments. This is an area
that is open to more optimizations (we could statically determine the byte-range and
only fetch it, we could parallelize this for multiple matches \[the default resultset
come with 10 matches\], ...), though these won't have the same effects as in getting
a better speed in the DB.

Of course alongside these, there have been tons of ways to optimize postgresql itself
for different workloads, though it is outside of the Reiz project.

## Setup

Machine;

|              |                        |
| ------------ | ---------------------- |
| provider     | digital ocean          |
| service type | droplet (basic plan)   |
| cpu          | (shared) 2vCPU         |
| ram          | 2GB                    |
| disk         | regular SSD (not NVME) |

IndexDB;

|                 |            |
| --------------- | ---------- |
| total files     | 53k        |
| total AST nodes | 17 521 894 |

Benchmark script is present at the source checkout (`scripts/benchmark_doc.py`).
