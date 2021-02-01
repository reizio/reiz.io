from reiz.config import config
from reiz.schema.builders import base, edgeql

_SCHEMA_GENERATORS = {"edgeql": edgeql.generate_schema}


def get_schema_generator(backend_name):
    if backend := _SCHEMA_GENERATORS.get(backend_name.casefold()):
        return backend
    else:
        raise base.SchemaError(f"{backend_name!r} backend doesn't exist")


generate_schema = _SCHEMA_GENERATORS.get(config.ir.backend)
