import code
from argparse import ArgumentParser

from reiz.db.connection import connect
from reiz.utilities import get_db_settings


def start(**db_opts):
    with connect(**db_opts) as conn:
        code.interact(
            local={
                "conn": conn,
                "query": conn.query,
                "execute": conn.execute,
                "query_one": conn.query_one,
                "connection": conn,
            }
        )


def main():
    parser = ArgumentParser()
    parser.add_argument("--dsn", default=get_db_settings()["dsn"])
    parser.add_argument("--database", default=get_db_settings()["database"])
    options = parser.parse_args()
    start(**vars(options))


if __name__ == "__main__":
    main()
