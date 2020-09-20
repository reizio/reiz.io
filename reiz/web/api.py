import ast
import tokenize

from flask import Flask, jsonify, request

from reiz.db.connection import connect
from reiz.edgeql import EdgeQLSelector, construct
from reiz.reizql import ReizQLSyntaxError, compile_edgeql, parse_query
from reiz.utilities import get_db_settings, logger

app = Flask(__name__)
DEFAULT_LIMIT = 10


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


@app.route("/query", methods=["POST"])
def query():
    if key := validate_keys("query"):
        return jsonify({"error": f"Missing key {key}"}), 412

    reiz_ql = request.json["query"]
    try:
        tree = parse_query(reiz_ql)
    except ReizQLSyntaxError as syntax_err:
        error = {"error": "Syntax error", "message": syntax_err.message}
        if syntax_err.position:
            error.update(syntax_err.position)
        return jsonify(error), 422
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
        for result in conn.query(query):
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
    return jsonify(results), 200


if __name__ == "__main__":
    app.run(debug=True)
