# Reiz Internals

## Flow

![flowgraph](flowgraph.png)

## Components

```
Warehouse Preparation (reiz.schema):
    -> reiz.schema.builders.$DB
        Build a schema from the given ASDL file
    -> reiz.schema.$DB
        Store schema metadata for the specific database

Data Collection (reiz.sampling):
    -> reiz.sampling.get_dataset
        Get a list of possible projects with cross references to their SCM pages
    -> reiz.sampling.fetch_dataset
        Download the given list of projects
    -> reiz.sampling.sanitize_dataset
        Remove everything beside valid Python 3 source code files

Data Serialization (reiz.serialization):
    -> reiz.serialization.transformers
        Transform and annotate the raw language AST for querying
    -> reiz.serialization.serializer
        Serialize all source files in a single project to the database
    -> reiz.serialization.serialize
        Serialize all downloaded projects to the database

Data Querying [ReizQL] (reiz.reizql):
    -> reiz.reizql.parser
        -> reiz.reizql.parser.grammar
            Represent Reiz AST
        -> reiz.reizql.parser.parse
            Generate Reiz AST from ReizQL
    -> reiz.reizql.compiler
        Generate IR from Reiz AST
```
