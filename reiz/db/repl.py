import code
from argparse import ArgumentParser

from reiz.db.connection import DEFAULT_DSN, DEFAULT_TABLE, connect


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
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--table", default=DEFAULT_TABLE)
    options = parser.parse_args()
    start(**vars(options))


if __name__ == "__main__":
    main()
