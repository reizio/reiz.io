import ast
import tokenize
from functools import lru_cache

from reiz.db.connection import connect
from reiz.db.schema import protected_name
from reiz.edgeql import (
    EdgeQLCall,
    EdgeQLSelect,
    EdgeQLSelector,
    EdgeQLUnion,
    construct,
)
from reiz.reizql import compile_edgeql, parse_query
from reiz.utilities import get_db_settings, logger

DEFAULT_LIMIT = 10


class LocationNode(ast.AST):
    _attributes = ("lineno", "col_offset", "end_lineno", "end_col_offset")


@lru_cache(8)
def get_stats(nodes=("Module", "AST", "stmt", "expr")):
    query = construct(
        EdgeQLSelect(
            EdgeQLUnion.from_seq(
                EdgeQLCall("count", [protected_name(node, prefix=True)])
                for node in nodes
            )
        ),
        top_level=True,
    )

    with connect(**get_db_settings()) as conn:
        stats = tuple(conn.query(query))

    return dict(zip(nodes, stats))


def fetch(filename, **loc_data):
    loc_node = LocationNode(**loc_data)
    with tokenize.open(filename) as file:
        source = file.read()
    return ast.get_source_segment(source, loc_node)


def run_query(reiz_ql, limit=DEFAULT_LIMIT):
    tree = parse_query(reiz_ql)
    logger.info("ReizQL Tree: %r", tree)

    selection = compile_edgeql(tree)
    selection.limit = limit
    selection.selections = [
        EdgeQLSelector("lineno"),
        EdgeQLSelector("col_offset"),
        EdgeQLSelector("end_lineno"),
        EdgeQLSelector("end_col_offset"),
        EdgeQLSelector("_module", [EdgeQLSelector("filename")]),
    ]

    query = construct(selection, top_level=True)
    logger.info("EdgeQL query: %r", query)

    results = []
    with connect(**get_db_settings()) as conn:
        query_set = conn.query(query)

        for result in query_set:
            try:
                source = fetch(
                    result._module.filename,
                    lineno=result.lineno,
                    col_offset=result.col_offset,
                    end_lineno=result.end_lineno,
                    end_col_offset=result.end_col_offset,
                )
            except Exception:
                source = None

            results.append(
                {
                    "source": source,
                    "filename": result._module.filename,
                }
            )

    return results
