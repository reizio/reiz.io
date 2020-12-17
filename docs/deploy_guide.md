# Deploying Reiz.IO

## Requirements
- A clean Python (3.8) environment
- EdgeDB (v1.0a7+)

## Actions
Reiz.IO's initial start can be thinked as a pipeline of commands.

### Configuration
It is required to have a configuration file on your `~/.local/` folder
named `reiz.json`. A simple one might look like this;
```
{
    "database": {
        "dsn": "default",
        "cluster": "default",
        "database": "reiz_store"
    },
    "redis": {
        "cache": false,
        "instance": "redis://localhost:6379"
    },
    "data": {
        "clean_directory": "~/disk/sampling/clean/"
    }
}
```

### Sampling
We try to only collect source code from projects that actually
matters and actively used through the ecosystem. For that, we
initially get a list of top 4000 PyPI packages and then filter
them down with the ones who provide a direct access to the GitHub
repository they use. This way, we can offer a direct link from a
query to the commit revision.

Collect the dataset;

```
$ python -m reiz.sampling.get_dataset sampling_data/data.json
```

Fetch the dataset (this requires over 60 GB space, be careful);

```
$ python -m reiz.sampling.fetch_dataset sampling_data/data.json sampling_data/raw
```

and then finally sanitize the set (which would create a clone of
the set and then remove all files / directories that doesn't
contain source code, such as `.git` folder / readme files / other
asserts etc.)

```
$ python -m reiz.sampling.sanitize_dataset sampling_data/data.json sampling_data/raw \
            sampsampling_dataling/clean
```

### Shaping the EdgeDB Instance
[Our schema](../static/Python-reiz.edgeql) (in the form of SDL) (EdgeDB's
schema language) is auto generated from a modified version of [Python's ASDL](../static/Python-reiz.asdl).
For applying this schema to the `database` that you have specified in the config, the `./scripts/regen_db.sh`
can be simply applied. This might take some time, since it will reboot the EdgeDB instance (to drop all connections)
and then apply the schema.

```
$ ./scripts/regen_db.sh
```

### Populating the DB
When the sanitized dataset is ready, and the EdgeDB instance is cleared, you can
start serializing source code files into EdgeQL and then inserting them over to
your EdgeDB instance with `reiz.serialization.serialize`.

```
$ python -m reiz.serialization.serialize sampling_data/data.json sampling_data/clean/
```

### Running queries
You can run your queries in the forms of files / or from the stdin via `./scripts/run_query.py`.

```
(.venv38) (Python 3.8.5+) [  1:31ÖÖ ]  [ isidentical@desktop:~/reiz.io(master✗) ]
 $ cat tuple_returning_classmethod.reizql
FunctionDef(
    decorator_list=[
        Name("classmethod")
    ],
    body = [
        *...,
        Return(Tuple())
    ]
)
(.venv38) (Python 3.8.5+) [  1:31ÖÖ ]  [ isidentical@desktop:~/reiz.io(master✗) ]
 $ ./scripts/run_query.py tuple_returning_classmethod.reizql

...
...
```

It will print out a list of dictionaries where there are 3 keys (filename, github_link and
source). The given query language is ReizQL, which is described [here](../docs/reizql.md).

### Starting the Web API
For running it with [search.tree.science](https://github.com/treescience/search.tree.science)
reiz can be configured to serve a Web API. For firing it up;
```
$ python -m reiz.web.api
```

Also there is an `reiz.web.wsgi` which can be used with `gunicorn`.

