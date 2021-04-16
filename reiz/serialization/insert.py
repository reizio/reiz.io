import itertools
import warnings
from argparse import ArgumentParser
from collections import deque
from concurrent import futures
from pathlib import Path

from reiz.database import InternalDatabaseError
from reiz.ir import IR, Schema
from reiz.sampling import load_dataset
from reiz.serialization.context import GlobalContext
from reiz.serialization.serializer import apply_ast
from reiz.serialization.statistics import Insertion, Statistics
from reiz.utilities import _available_cores, guarded, logger


@guarded(Insertion.FAILED, ignored_exceptions=(InternalDatabaseError,))
def insert_file(context):
    if context.is_cached():
        return Insertion.CACHED

    if not (tree := context.as_ast()):
        return Insertion.SKIPPED

    with context.connection.transaction():
        module = apply_ast(tree, context)
        module_select = IR.select(
            tree.kind_name, filters=IR.object_ref(module), limit=1
        )

        update_filter = IR.filter(
            IR.attribute(None, "id"),
            IR.call(
                "array_unpack", [IR.cast("array<uuid>", IR.variable("ids"))]
            ),
            "IN",
        )
        for base_type in Schema.module_annotated_types:
            update = IR.update(
                base_type.kind_name,
                filters=update_filter,
                assignments={"_module": module_select},
            )
            context.connection.query(
                IR.construct(update), ids=context.reference_pool
            )

    logger.info("%r has been inserted successfully", context.filename)
    context.cache()
    return Insertion.INSERTED


def insert_project(project, *, global_ctx):
    with global_ctx.pool.new_connection() as connection:
        project_ctx = global_ctx.new_child(project, connection)
        if not project_ctx.is_cached():
            apply_ast(project_ctx.as_ast(), project_ctx)
            project_ctx.cache()

        stats = Statistics()
        for file in project_ctx.path.glob("**/*.py"):
            if project_ctx.apply_constraints(stats):
                break

            file_ctx = project_ctx.new_child(file)
            stats[insert_file(file_ctx)] += 1

    return stats


def _execute_tasks(global_ctx, tasks, projects, populate_tasks):
    global_stats = Statistics()
    while tasks:
        done, _ = futures.wait(tasks, return_when=futures.FIRST_COMPLETED)
        total_completed = len(done)

        for task in done:
            project, stats = tasks.pop(task), task.result()
            global_stats.update(stats)
            if stats[Insertion.INSERTED] == 0:
                projects.remove(project)
            logger.info("%s: %r", project.name, stats)

        if global_ctx.apply_constraints(global_stats):
            for task in tasks:
                task.cancel()
            return global_stats

        projects.rotate(total_completed)
        tasks.update(populate_tasks(total_completed, tasks.values()))


def insert_projects(projects, *, max_workers=None, global_ctx=None):
    if global_ctx is None:
        global_ctx = GlobalContext()

    projects = deque(projects)
    max_workers = max_workers or (_available_cores() // 2) + 1
    max_active_tasks = (
        global_ctx.properties.get("max_files", 10) // max_workers
    )
    with global_ctx:
        with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

            def populate_tasks(amount, known_tasks=()):
                return {
                    executor.submit(
                        insert_project, project, global_ctx=global_ctx
                    ): project
                    for project in itertools.islice(projects, amount)
                    if project not in known_tasks
                }

            return _execute_tasks(
                global_ctx,
                tasks=populate_tasks(max_active_tasks),
                projects=projects,
                populate_tasks=populate_tasks,
            )


def insert_dataset(dataset_path, max_workers=None, **options):
    insert_projects(
        load_dataset(dataset_path),
        max_workers=max_workers,
        global_ctx=GlobalContext(options),
    )


def main():
    parser = ArgumentParser()
    parser.add_argument("dataset_path", type=Path)
    parser.add_argument("-w", "--workers", default=None, type=int)
    parser.add_argument("--fast", action="store_true", dest="fast_mode")
    parser.add_argument("--limit", type=int, dest="hard_limit")
    parser.add_argument(
        "--project-limit", type=int, dest="max_files", default=10
    )
    options = parser.parse_args()

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        insert_dataset(**vars(options))


if __name__ == "__main__":
    main()
