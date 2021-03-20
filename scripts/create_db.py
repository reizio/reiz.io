#!/usr/bin/env python

import subprocess
from argparse import ArgumentParser
from contextlib import suppress
from pathlib import Path

from edgedb.errors import InvalidReferenceError

from reiz.database import get_new_connection
from reiz.utilities import logger

SCRIPTS_DIR = Path(__file__).parent


def does_db_exist():
    try:
        with get_new_connection() as connection:
            connection.execute("SELECT ast::Name;")
    except Exception:
        return False
    else:
        return True


def create_db():
    if does_db_exist():
        logger.info("database exits, doing nothing...")
    else:
        subprocess.check_call(
            ["/bin/bash", "scripts/regen_db.sh"], cwd=SCRIPTS_DIR.parent
        )


def main():
    create_db()


if __name__ == "__main__":
    main()
