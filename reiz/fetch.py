import ast
import tokenize

from reiz.config import config
from reiz.database import get_new_connection
from reiz.db.schema import protected_name
from reiz.edgeql import (
    EdgeQLCall,
    EdgeQLSelect,
    EdgeQLSelector,
    EdgeQLUnion,
    as_edgeql,
)
from reiz.reizql import ReizQLSyntaxError, compile_edgeql, parse_query
from reiz.utilities import logger

DEFAULT_LIMIT = 10
DEFAULT_NODES = ("Module", "AST", "stmt", "expr")
CLEAN_DIRECTORY = config.data.clean_directory

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


def get_stats(nodes=DEFAULT_NODES):
    query = as_edgeql(
        EdgeQLSelect(
            EdgeQLUnion.from_seq(
                EdgeQLCall("count", [protected_name(node, prefix=True)])
                for node in nodes
            )
        ),
    )

    with get_new_connection() as connection:
        stats = tuple(connection.query(query))

    return dict(zip(nodes, stats))


def fetch(filename, **loc_data):
    with tokenize.open(filename) as file:
        source = file.read()

    if loc_data:
        loc_node = LocationNode(**loc_data)
        return ast.get_source_segment(source, loc_node)
    else:
        return source


def run_query(reiz_ql, limit=DEFAULT_LIMIT):
    tree = parse_query(reiz_ql)
    logger.info("ReizQL Tree: %r", tree)

    selection = compile_edgeql(tree)
    selection.limit = limit

    if tree.positional:
        selection.selections.extend(POSITION_SELECTION)
    elif tree.name == "Module":
        selection.selections.extend(PROJECT_SELECTION)
    else:
        raise ReizQLSyntaxError(f"Unexpected root matcher: {tree.name}")

    query = as_edgeql(selection)
    logger.info("EdgeQL query: %r", query)

    results = []
    with get_new_connection() as connection:
        query_set = connection.query(query)

        for result in query_set:
            loc_data = {}
            if tree.positional:
                module = result._module
                github_link = (
                    infer_github_url(module)
                    + f"#L{result.lineno}-L{result.end_lineno}"
                )
                loc_data.update(
                    {
                        "filename": CLEAN_DIRECTORY / module.filename,
                        "lineno": result.lineno,
                        "col_offset": result.col_offset,
                        "end_lineno": result.end_lineno,
                        "end_col_offset": result.end_col_offset,
                    }
                )
            elif tree.name == "Module":
                github_link = infer_github_url(result)
                loc_data.update(
                    {"filename": CLEAN_DIRECTORY / result.filename}
                )
            else:
                github_link = None

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
