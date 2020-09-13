# reiz.io

Internal toolkit for working with source code.

```
$ mkdir /mnt/rawdata
$ ln -s /mnt/rawdata reiz.io/rawdata
$ python -m reiz.samplers.pypi  --limit 4000 rawdata/pypi
$ python -m reiz.cleaner rawdata/pypi rawdata/clean
$ python -m reiz.db.schema_gen static/Python-reiz.asdl > static/Python-reiz.edgeql
$ python -m reiz.db.reset static/Python-reiz.edgeql
$ python -m reiz.db.insert rawdata/clean
```
