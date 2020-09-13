# python -i reiz/repl.py
import atexit

import edgedb

conn = edgedb.connect("edgedb://edgedb@localhost/asttests")
atexit.register(conn.close)

execute = conn.execute
query = conn.query
query_one = conn.query_one
