import ast
import threading
import tokenize
from pathlib import Path

import edgedb
from flask import Flask, jsonify, request

from reiz.db.connection import connect
from reiz.edgeql import EdgeQLSelector, construct
from reiz.reizql import ReizQLSyntaxError, compile_edgeql, parse_query
from reiz.utilities import get_db_settings, logger

app = Flask(__name__)
DEFAULT_LIMIT = 10
TOKENS_FILE = Path("~/.reiz/TOKENS_FILE").expanduser()


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


def verify_token(token):
    if TOKENS_FILE.exists():
        tokens = TOKENS_FILE.read_text().splitlines()
    else:
        tokens = []
        logger.warning("Tokens file (%r) doesn't exist!", TOKENS_FILE)
    return token in tokens


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
def query():
    if key := validate_keys("query", "token"):
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

    if not verify_token(request.json["token"]):
        return (
            jsonify(
                {
                    "status": "error",
                    "results": [],
                    "exception": "access denied",
                }
            ),
            401,
        )

    reiz_ql = request.json["query"]
    results, ret = result_fetch_worker(reiz_ql)
    return jsonify(results), ret


if __name__ == "__main__":
    app.run(debug=True)
