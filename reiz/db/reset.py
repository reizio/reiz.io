import subprocess
from argparse import ArgumentParser
from collections import Counter
from contextlib import closing, suppress
from pathlib import Path

import edgedb
from edgedb.errors import InvalidReferenceError

DEF_DSN = "edgedb://edgedb@localhost"


def drop_all_connection():
    print("Stopping the server...")
    subprocess.run(
        [Path("~/.edgedb/bin/edgedb").expanduser(), "server", "stop"]
    )
    print("Re-starting the server...")
    subprocess.check_call(
        [Path("~/.edgedb/bin/edgedb").expanduser(), "server", "start"]
    )


def drop_and_load_db(scheme, database_name, edge_host=DEF_DSN):
    drop_all_connection()
    with closing(edgedb.connect(edge_host + "/edgedb")) as connection:
        with suppress(InvalidReferenceError):
            connection.execute(f"DROP DATABASE {database_name}")
        print("Creating the database...")
        connection.execute(f"CREATE DATABASE {database_name}")
    with closing(
        edgedb.connect(edge_host + f"/{database_name}")
    ) as connection:
        with open(scheme) as scheme_f:
            content = scheme_f.read()
        connection.execute(content)
        connection.execute("POPULATE MIGRATION")
        print("Committing the schema...")
        connection.execute("COMMIT MIGRATION")


def main():
    parser = ArgumentParser()
    parser.add_argument("scheme", type=Path)
    parser.add_argument("--database_name", default="asttests")
    parser.add_argument("--edge_host", default=DEF_DSN)
    options = parser.parse_args()
    drop_and_load_db(**vars(options))


if __name__ == "__main__":
    main()
