import json
import traceback
from dataclasses import asdict

import aioredis
from edgedb.errors import InvalidReferenceError
from sanic import Sanic
from sanic.response import json as json_response
from sanic_cors import CORS
from sanic_limiter import Limiter, get_remote_address

from reiz.config import config
from reiz.database import get_async_db_pool
from reiz.edgeql import as_edgeql
from reiz.fetch import (
    STATISTICS_NODES,
    STATS_QUERY,
    run_query_on_async_connection,
)
from reiz.reizql import ReizQLSyntaxError, compile_edgeql, parse_query
from reiz.utilities import normalize

app = Sanic(__name__)
limiter = Limiter(app, key_func=get_remote_address)
CORS(app)


@app.listener("before_server_start")
async def init(sanic, loop):
    app.database_pool = await get_async_db_pool()
    if config.redis.cache:
        app.redis_pool = await aioredis.create_redis_pool(
            config.redis.instance
        )


@app.listener("after_server_stop")
async def close_db(app, loop):
    if config.redis.cache:
        app.redis_pool.close()
        await app.redis_pool.wait_closed()


async def check_cache(key):
    if not config.redis.cache:
        return None

    entry = await app.redis_pool.get(json.dumps(key))
    if entry is not None:
        return json.loads(entry)


async def set_cache(key, value):
    if not config.redis.cache:
        return None

    await app.redis_pool.set(json.dumps(key), json.dumps(value))


@app.route("/query", methods=["POST"])
@limiter.limit("240 per hour;10/minute")
async def query(request):
    if "query" not in request.json:
        return error("Missing 'query' data")

    offset = request.json.get("offset", 0)
    reiz_ql = request.json["query"]

    if entry := await check_cache(request.json):
        return success(entry)

    async with app.database_pool.acquire() as connection:
        try:
            results = await run_query_on_async_connection(
                connection, reiz_ql, offset=offset
            )
        except ReizQLSyntaxError as syntax_err:
            return error(syntax_err.message, **syntax_err.position)
        except InvalidReferenceError as exc:
            return error(exc.args[0])
        except Exception:
            return error(traceback.format_exc())
        else:
            await set_cache(request.json, results)
            return success(results)


@app.route("/analyze", methods=["POST"])
async def analyze_query(request):
    if "query" not in request.json:
        return error("Missing 'query' data")

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

    return json_response(results)


@app.route("/stats", methods=["GET"])
async def stats(request):
    async with app.database_pool.acquire() as connection:
        stats = tuple(await connection.query(STATS_QUERY))

    return success(dict(zip(STATISTICS_NODES, stats)))


def success(result_set, **kwargs):
    return json_response(
        {
            "status": "success",
            "results": result_set,
            "exception": None,
            **kwargs,
        }
    )


def error(message, **kwargs):
    return json_response(
        {
            "status": "error",
            "results": [],
            "exception": message,
            **kwargs,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
