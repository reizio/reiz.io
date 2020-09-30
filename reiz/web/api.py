import atexit
import json
import traceback

import edgedb
import redis
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from reiz.fetch import get_stats, run_query
from reiz.reizql import ReizQLSyntaxError
from reiz.utilities import get_config_settings, logger

CACHING = None


def get_app():
    global CACHING
    app = Flask(__name__)
    CORS(app)

    extras = {}
    if redis_url := get_config_settings().get("redis"):
        extras["storage_uri"] = redis_url
        CACHING = redis.from_url(redis_url)
        atexit.register(CACHING.close)

    limiter = Limiter(app, key_func=get_remote_address, **extras)
    return app, limiter


app, limiter = get_app()


def run_cached_query(reiz_ql):
    if results := CACHING.get(reiz_ql):
        return json.loads(results)
    else:
        results = run_query(reiz_ql)
        CACHING.set(reiz_ql, json.dumps(results))
        return results


def validate_keys(*keys):
    for key in keys:
        if key not in request.json.keys():
            return key


@app.route("/query", methods=["POST"])
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
        if stats := request.json.get("stats", False) or not CACHING:
            results = run_query(reiz_ql, stats=stats)
        else:
            results = run_cached_query(reiz_ql)
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
def stats():
    return jsonify(get_stats()), 200


if __name__ == "__main__":
    app.run(debug=True)
