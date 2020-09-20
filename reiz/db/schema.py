import ast

# FIX-ME(low): auto-generate these in the ./scripts/regen_db.sh
ENUM_TYPES = (
    ast.expr_context,
    ast.boolop,
    ast.operator,
    ast.unaryop,
    ast.cmpop,
)

MODULE_ANNOTATED_TYPES = (ast.expr, ast.stmt)

ATOMIC_TYPES = (int, str)

RESERVED_NAMES = frozenset(
    (
        "id",
        "If",
        "Set",
        "For",
        "With",
        "Raise",
        "Import",
        "module",
        "Global",
        "Module",
        "Delete",
    )
)


def protected_name(name, *, prefix=True):
    if name in RESERVED_NAMES:
        if name.istitle():
            name = "Py" + name
        else:
            name = "py_" + name

    if prefix:
        name = "ast::" + name
    return name
