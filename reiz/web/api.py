import ast
import threading
import tokenize
from pathlib import Path

import edgedb
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from reiz.db.connection import connect
from reiz.db.schema import protected_name
from reiz.edgeql import (
    EdgeQLCall,
    EdgeQLSelect,
    EdgeQLSelector,
    EdgeQLUnion,
    construct,
)
from reiz.reizql import ReizQLSyntaxError, compile_edgeql, parse_query
from reiz.utilities import get_db_settings, logger

app = Flask(__name__)
extras = {}
if redis_url := get_db_settings().get("redis"):
    extras["storage_uri"] = redis_url

limiter = Limiter(app, key_func=get_remote_address, **extras)

DEFAULT_LIMIT = 10

STAT_NODES = ("Module", "AST", "stmt", "expr")
STATS_QUERY = construct(
    EdgeQLSelect(
        EdgeQLUnion.from_seq(
            EdgeQLCall("count", [protected_name(node_t, prefix=True)])
            for node_t in STAT_NODES
        )
    ),
    top_level=True,
)


class LocationNode(ast.AST):
    _attributes = ("lineno", "col_offset", "end_lineno", "end_col_offset")


def fetch(filename, **loc_data):
    loc_node = LocationNode(**loc_data)
    with tokenize.open(filename) as file:
        source = file.read()
    return ast.get_source_segment(source, loc_node)


def validate_keys(*keys):
    for key in keys:
        if key not in request.json.keys():
            return key


def result_fetch_worker(reiz_ql):
    try:
        tree = parse_query(reiz_ql)
    except ReizQLSyntaxError as syntax_err:
        error = {
            "status": "error",
            "results": [],
            "exception": syntax_err.message,
        }
        if syntax_err.position:
            error.update(syntax_err.position)
        return error, 422
    else:
        logger.info("ReizQL Tree: %r", tree)

    selection = compile_edgeql(tree)
    selection.limit = DEFAULT_LIMIT
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
        try:
            query_set = conn.query(query)
        except edgedb.errors.InvalidReferenceError as exc:
            return {"status": "error", "results": [], "exception": exc.args[0]}

        for result in query_set:
            results.append(
                {
                    "source": fetch(
                        result._module.filename,
                        lineno=result.lineno,
                        col_offset=result.col_offset,
                        end_lineno=result.end_lineno,
                        end_col_offset=result.end_col_offset,
                    ),
                    "filename": result._module.filename,
                }
            )
    return {"status": "success", "results": results, "exception": None}, 200


@app.route("/query", methods=["POST"])
@limiter.limit("120 per hour")
def query():
    if key := validate_keys("query"):
        return (
            jsonify(
                {
                    "status": "error",
                    "results": [],
                    "exception": f"Missing key {key}",
                }
            ),
            412,
        )

    reiz_ql = request.json["query"]
    results, ret = result_fetch_worker(reiz_ql)
    return jsonify(results), ret


@app.route("/stats", methods=["GET"])
def stats():
    with connect(**get_db_settings()) as conn:
        logger.info("EdgeQL query: %r", STATS_QUERY)
        stats = tuple(conn.query(STATS_QUERY))

    return jsonify(dict(zip(STAT_NODES, stats))), 200


if __name__ == "__main__":
    app.run(debug=True)
