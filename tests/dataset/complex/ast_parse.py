with open("somefile.py") as file_s:  # reiz: tp
    tree = ast.parse(file_s.read())

with open(some_path) as stream:  # reiz: tp
    tree = ast.parse(stream.read())

with open(pathlib_path / "file.py") as s_file:  # reiz: tp
    tree = ast.parse(s_file.read())

with open(pathlib_path / "file.py", encoding="x") as stream:
    tree = ast.parse(stream.read())

with open() as stream:
    tree = ast.parse(stream.read())

with foo(path) as stream:
    tree = ast.parse(stream.read())

with open(path) as stream:
    tree = ast.parse(other_stream.read())

with open(path) as stream:
    tree = ast.foo(stream.read())

with open(path) as stream:
    tree = bar.parse(stream.read())

with open(path) as stream:
    tree = bar.baz(stream.read())

with open(path) as xxx:
    tree = ast.parse(yyy.read())

with open(path) as xxx:
    zzz = ast.parse(xxx.read())
