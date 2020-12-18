import ast
import asyncio
import tokenize

from reiz.config import config
from reiz.database import get_new_connection
from reiz.edgeql import (
    EdgeQLCall,
    EdgeQLSelect,
    EdgeQLSelector,
    EdgeQLUnion,
    as_edgeql,
)
from reiz.edgeql.schema import protected_name
from reiz.reizql import ReizQLSyntaxError, compile_edgeql, parse_query
from reiz.utilities import logger

DEFAULT_LIMIT = 10
CLEAN_DIRECTORY = config.data.clean_directory
STATISTICS_NODES = ("Module", "AST", "stmt", "expr")

PROJECT_SELECTION = [
    EdgeQLSelector("filename"),
    EdgeQLSelector(
        "project",
        [EdgeQLSelector("git_source"), EdgeQLSelector("git_revision")],
    ),
]

POSITION_SELECTION = [
    EdgeQLSelector("lineno"),
    EdgeQLSelector("col_offset"),
    EdgeQLSelector("end_lineno"),
    EdgeQLSelector("end_col_offset"),
    EdgeQLSelector("_module", PROJECT_SELECTION),
]

STATS_QUERY = as_edgeql(
    EdgeQLSelect(
        EdgeQLUnion.from_seq(
            EdgeQLCall("count", [protected_name(node, prefix=True)])
            for node in STATISTICS_NODES
        )
    )
)


class LocationNode(ast.AST):
    _attributes = ("lineno", "col_offset", "end_lineno", "end_col_offset")


def infer_github_url(result):
    return (
        result.project.git_source
        + "/tree/"
        + result.project.git_revision
        + "/"
        + "/".join(result.filename.split("/")[1:])
    )


def fetch(filename, **loc_data):
    with tokenize.open(CLEAN_DIRECTORY / filename) as file:
        source = file.read()

    if loc_data:
        loc_node = LocationNode(**loc_data)
        return ast.get_source_segment(source, loc_node, padded=True)
    else:
        return source


def _get_query(reiz_ql, limit, offset):
    tree = parse_query(reiz_ql)
    logger.info("ReizQL Tree: %r", tree)

    selection = compile_edgeql(tree)
    selection.limit = limit
    if offset > 0:
        selection.offset = offset

    if tree.positional:
        selection.selections.extend(POSITION_SELECTION)
    elif tree.name == "Module":
        selection.selections.extend(PROJECT_SELECTION)
    else:
        raise ReizQLSyntaxError(f"Unexpected root matcher: {tree.name}")

    query = as_edgeql(selection)
    logger.info("EdgeQL query: %r", query)
    return query, tree.positional


def _process_query_set(query_set, is_tree_positional):
    results = []
    for result in query_set:
        loc_data = {}
        if is_tree_positional:
            module = result._module
            github_link = (
                infer_github_url(module)
                + f"#L{result.lineno}-L{result.end_lineno}"
            )
            loc_data.update(
                {
                    "filename": module.filename,
                    "lineno": result.lineno,
                    "col_offset": result.col_offset,
                    "end_lineno": result.end_lineno,
                    "end_col_offset": result.end_col_offset,
                }
            )
        else:
            github_link = infer_github_url(result)
            loc_data.update({"filename": result.filename})

        try:
            source = fetch(**loc_data)
        except Exception:
            source = None

        results.append(
            {
                "source": source,
                "filename": loc_data["filename"],
                "github_link": github_link,
            }
        )

    return results


def run_query_on_connection(
    connection, reiz_ql, limit=DEFAULT_LIMIT, offset=0
):
    query, is_tree_positional = _get_query(reiz_ql, limit, offset)
    query_set = connection.query(query)
    return _process_query_set(query_set, is_tree_positional)


async def run_query_on_async_connection(
    connection,
    reiz_ql,
    limit=DEFAULT_LIMIT,
    offset=0,
    loop=None,
    timeout=config.web.timeout,
):
    query, is_tree_positional = _get_query(reiz_ql, limit, offset)
    coroutine = connection.query(query)
    query_set = await asyncio.wait_for(coroutine, timeout=timeout, loop=loop)
    return _process_query_set(query_set, is_tree_positional)


def run_query(reiz_ql, limit=DEFAULT_LIMIT):
    with get_new_connection() as connection:
        return run_query_on_connection(connection, reiz_ql, limit=limit)
