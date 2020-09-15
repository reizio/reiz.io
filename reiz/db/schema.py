import ast

ENUM_TYPES = (
    ast.expr_context,
    ast.boolop,
    ast.operator,
    ast.unaryop,
    ast.cmpop,
)


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
