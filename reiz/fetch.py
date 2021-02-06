import ast
import asyncio
import tokenize

from reiz.config import config
from reiz.database import get_new_connection
from reiz.ir import IR
from reiz.reizql import compile_to_ir, parse_query

DEFAULT_LIMIT = 10
CLEAN_DIRECTORY = config.data.clean_directory
STATISTICS_NODES = ("Module", "AST", "stmt", "expr")

POSITION_SELECTION = [
    IR.selection("lineno"),
    IR.selection("col_offset"),
    IR.selection("end_lineno"),
    IR.selection("end_col_offset"),
    IR.selection(
        "_module",
        [
            IR.selection("filename"),
            IR.selection(
                "project",
                [IR.selection("git_source"), IR.selection("git_revision")],
            ),
        ],
    ),
]

STATS_QUERY = IR.construct(
    IR.select(
        IR.merge(
            IR.call("count", [IR.wrap(name)]) for name in STATISTICS_NODES
        )
    )
)


class LocationNode(ast.AST):
    _attributes = ("lineno", "col_offset", "end_lineno", "end_col_offset")


def get_username(link):
    if link.endswith("/"):
        index = 3
    else:
        index = 2

    return link.split("/")[-index]


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

    loc_node = LocationNode(**loc_data)
    return ast.get_source_segment(source, loc_node, padded=True)


def compile_query(reiz_ql, limit, offset):
    tree = parse_query(reiz_ql)

    selection = compile_to_ir(tree)
    if limit is not None:
        selection.limit = limit
    if offset > 0:
        selection.offset = offset

    selection.selections.extend(POSITION_SELECTION)
    return selection


def process_queryset(query_set):
    results = []
    for result in query_set:
        module = result._module
        github_link = (
            infer_github_url(module)
            + f"#L{result.lineno}-L{result.end_lineno}"
        )
        loc_data = {
            "filename": module.filename,
            "lineno": result.lineno,
            "col_offset": result.col_offset,
            "end_lineno": result.end_lineno,
            "end_col_offset": result.end_col_offset,
        }

        try:
            source = fetch(**loc_data)
        except Exception:
            source = None

        result = {
            "repo": module.project.git_source,
            "username": get_username(module.project.git_source),
            "source": source,
            "github_link": github_link,
            **loc_data,
        }
        results.append(result)

    return results


def run_query_on_connection(
    connection,
    reiz_ql,
    *,
    limit=DEFAULT_LIMIT,
    offset=0,
):
    query = IR.construct(compile_query(reiz_ql, limit, offset))
    query_set = connection.query(query)
    return process_queryset(query_set)


async def run_query_on_async_connection(
    connection,
    reiz_ql,
    *,
    limit=DEFAULT_LIMIT,
    offset=0,
    loop=None,
    timeout=config.web.timeout,
):
    query = IR.construct(compile_query(reiz_ql, limit, offset))
    query_set = await asyncio.wait_for(
        connection.query(query), timeout=timeout, loop=loop
    )
    return process_queryset(query_set)


def run_query(reiz_ql, limit=DEFAULT_LIMIT):
    with get_new_connection() as connection:
        return run_query_on_connection(connection, reiz_ql, limit=limit)
