import subprocess
from argparse import ArgumentParser
from contextlib import closing, suppress
from pathlib import Path

import edgedb
from edgedb.errors import InvalidReferenceError

from reiz.utilities import get_db_settings

SERVER_MANAGER = [Path("~/.edgedb/bin/edgedb").expanduser(), "server"]


def drop_all_connection(cluster):
    print("Stopping the server...")
    subprocess.run(SERVER_MANAGER + ["stop", cluster])
    print("Re-starting the server...")
    subprocess.check_call(SERVER_MANAGER + ["start", cluster])


def drop_and_load_db(schema, dsn, database, cluster):
    drop_all_connection(cluster)
    print("Successfully rebooted...")

    with closing(edgedb.connect(cluster, database="edgedb")) as connection:
        with suppress(InvalidReferenceError):
            connection.execute(f"DROP DATABASE {database}")
        print("Creating the database...")
        connection.execute(f"CREATE DATABASE {database}")
        print("Database created...")
    with closing(edgedb.connect(dsn, database=database)) as connection:
        with open(schema) as schema_f:
            content = schema_f.read()
        print("Executing schema...")
        connection.execute(content)
        print("Starting migration...")
        connection.execute("POPULATE MIGRATION")
        print("Committing the schema...")
        connection.execute("COMMIT MIGRATION")
    print("Successfully resetted!")


def main():
    parser = ArgumentParser()
    parser.add_argument("schema", type=Path)
    parser.add_argument("--dsn", default=get_db_settings()["dsn"])
    parser.add_argument("--database", default=get_db_settings()["database"])
    parser.add_argument(
        "--cluster", default=get_config_settings().get("cluster")
    )
    options = parser.parse_args()
    drop_and_load_db(**vars(options))


if __name__ == "__main__":
    main()
