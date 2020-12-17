import atexit
import json
import traceback
from dataclasses import asdict

import edgedb
import redis
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from reiz.edgeql import as_edgeql
from reiz.fetch import get_stats, run_query
from reiz.reizql import ReizQLSyntaxError, compile_edgeql, parse_query
from reiz.utilities import normalize


def get_app():
    app = Flask(__name__)
    CORS(app)

    extras = {}
    if config.redis.cached:
        extras["storage_uri"] = config.redis.instance
        redis = redis.from_url(redis_url)
        atexit.register(redis.close)
    else:
        redis = None

    limiter = Limiter(app, key_func=get_remote_address, **extras)
    return app, limiter, redis


app, limiter, redis = get_app()


def run_cached_query(reiz_ql):
    if results := redis.get(reiz_ql):
        return json.loads(results)
    else:
        results = run_query(reiz_ql)
        redis.set(reiz_ql, json.dumps(results))
        return results


def validate_keys(*keys):
    for key in keys:
        if key not in request.json.keys():
            return key


@app.route("/query", methods=["POST"])
@limiter.limit("240 per hour")
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
    try:
        if config.redis.cached:
            results = run_cached_query(reiz_ql)
        else:
            results = run_query(reiz_ql)
    except ReizQLSyntaxError as syntax_err:
        error = {
            "status": "error",
            "results": [],
            "exception": syntax_err.message,
        }
        if syntax_err.position:
            error.update(syntax_err.position)
        return jsonify(error), 422
    except edgedb.errors.InvalidReferenceError as exc:
        return (
            jsonify(
                {
                    "status": "error",
                    "results": [],
                    "exception": exc.args[0],
                }
            ),
            412,
        )
    except Exception:
        return (
            jsonify(
                {
                    "status": "error",
                    "results": [],
                    "exception": traceback.format_exc(),
                }
            ),
            412,
        )
    else:
        return (
            jsonify(
                {"status": "success", "results": results, "exception": None}
            ),
            200,
        )


@app.route("/stats", methods=["GET"])
@limiter.limit("4 per hour")
def stats():
    return jsonify(get_stats()), 200


@app.route("/analyze", methods=["POST"])
@limiter.limit("240 per hour")
def analyze():
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

    results = dict.fromkeys(("exception", "reiz_ql", "edge_ql"))
    try:
        reiz_ql = parse_query(request.json["query"])
        results["reiz_ql"] = normalize(asdict(reiz_ql))
        results["edge_ql"] = as_edgeql(compile_edgeql(reiz_ql))
    except ReizQLSyntaxError as syntax_err:
        results["status"] = "error"
        results["exception"] = syntax_err.message
        results.update(syntax_err.position)
    else:
        results["status"] = "success"

    return jsonify(results), 200


if __name__ == "__main__":
    app.run(debug=True)
