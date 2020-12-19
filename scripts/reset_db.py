import subprocess
from argparse import ArgumentParser
from contextlib import suppress
from pathlib import Path

from edgedb.errors import InvalidReferenceError

from reiz.config import config
from reiz.database import get_new_connection
from reiz.utilities import logger

SERVER_MANAGER = [Path("~/.edgedb/bin/edgedb").expanduser(), "server"]


def drop_all_connection(cluster):
    logger.info("Stopping the server...")
    subprocess.run(SERVER_MANAGER + ["stop", cluster])
    logger.info("Re-starting the server...")
    subprocess.check_call(SERVER_MANAGER + ["start", cluster])


def drop_and_load_db(schema, reboot_server=True):
    if reboot_server:
        drop_all_connection(config.database.cluster)
        logger.info("Successfully rebooted...")

    with get_new_connection(database="edgedb") as connection:
        with suppress(InvalidReferenceError):
            connection.execute(f"DROP DATABASE {config.database.database}")
        logger.info("Creating the database %s...", config.database.database)
        connection.execute(f"CREATE DATABASE {config.database.database}")
        logger.info("Database created...")

    with get_new_connection() as connection:
        with open(schema) as stream:
            content = stream.read()

        logger.info("Executing schema on %s...", connection.dbname)
        connection.execute(content)
        logger.info("Starting migration...")
        connection.execute("POPULATE MIGRATION")
        logger.info("Committing the schema...")
        connection.execute("COMMIT MIGRATION")

    logger.info("Successfully resetted!")


def main():
    parser = ArgumentParser()
    parser.add_argument("schema", type=Path)
    options = parser.parse_args()
    drop_and_load_db(**vars(options))


if __name__ == "__main__":
    main()
