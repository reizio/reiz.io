# reiz.io

Internal toolkit for working with source code.

```
$ mkdir /mnt/rawdata
$ ln -s /mnt/rawdata reiz.io/rawdata
$ python -m reiz.samplers.pypi  --limit 4000 rawdata/pypi
$ python -m reiz.cleaner rawdata/pypi rawdata/clean
```

```
$ cat functionality.py
def entry(project: Project) -> None:
    print(project.name)
    print(project.paths)
$ python -m reiz.execute functionality.py
```
