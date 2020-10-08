import subprocess
from argparse import ArgumentParser
from contextlib import closing, suppress
from pathlib import Path

import edgedb
from edgedb.errors import InvalidReferenceError

from reiz.utilities import get_db_settings


def drop_all_connection():
    print("Stopping the server...")
    subprocess.run(
        [Path("~/.edgedb/bin/edgedb").expanduser(), "server", "stop"]
    )
    print("Re-starting the server...")
    subprocess.check_call(
        [Path("~/.edgedb/bin/edgedb").expanduser(), "server", "start"]
    )


def drop_and_load_db(schema, dsn, database):
    print("Re-starting the server [using systemd]...")
    subprocess.check_call(["systemctl", "restart", "edgedb-server@default"])

    with closing(edgedb.connect(dsn, database="edgedb")) as connection:
        with suppress(InvalidReferenceError):
            connection.execute(f"DROP DATABASE {database}")
        print("Creating the database...")
        connection.execute(f"CREATE DATABASE {database}")
    with closing(edgedb.connect(dsn, database=database)) as connection:
        with open(schema) as schema_f:
            content = schema_f.read()
        connection.execute(content)
        connection.execute("POPULATE MIGRATION")
        print("Committing the schema...")
        connection.execute("COMMIT MIGRATION")


def main():
    parser = ArgumentParser()
    parser.add_argument("schema", type=Path)
    parser.add_argument("--dsn", default=get_db_settings()["dsn"])
    parser.add_argument("--database", default=get_db_settings()["database"])
    options = parser.parse_args()
    drop_and_load_db(**vars(options))


if __name__ == "__main__":
    main()
