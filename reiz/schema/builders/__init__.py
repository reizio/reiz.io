from reiz.config import config
from reiz.schema.builders import base, esdl

_SCHEMA_GENERATORS = {"edgeql": esdl.generate_schema}


def get_schema_generator(backend_name):
    if backend := _SCHEMA_GENERATORS.get(backend_name.casefold()):
        return backend
    else:
        raise base.SchemaError(f"{backend_name!r} backend doesn't exist")


generate_schema = get_schema_generator(config.ir.backend)
