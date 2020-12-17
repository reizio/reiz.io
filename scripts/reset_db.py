import subprocess
from argparse import ArgumentParser
from pathlib import Path

from edgedb.errors import InvalidReferenceError

from reiz.config import config
from reiz.database import get_new_connection, get_new_raw_connection

SERVER_MANAGER = [Path("~/.edgedb/bin/edgedb").expanduser(), "server"]


def drop_all_connection(cluster):
    print("Stopping the server...")
    subprocess.run(SERVER_MANAGER + ["stop", cluster])
    print("Re-starting the server...")
    subprocess.check_call(SERVER_MANAGER + ["start", cluster])


def drop_and_load_db(schema):
    drop_all_connection(config.database.cluster)
    print("Successfully rebooted...")

    with get_new_raw_connection(database="edgedb") as connection:
        with suppress(InvalidReferenceError):
            connection.execute(f"DROP DATABASE {config.database.database}")
        print("Creating the database...")
        connection.execute(f"CREATE DATABASE {database}")
        print("Database created...")

    with get_new_connection() as connection:
        with open(schema) as stream:
            content = stream.read()

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
    options = parser.parse_args()
    drop_and_load_db(**vars(options))


if __name__ == "__main__":
    main()
