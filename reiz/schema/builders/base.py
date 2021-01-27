class SchemaError(Exception):
    ...


class BaseSchemaGenerator:
    # Generic AST type for to be used as a namespace
    # and a base class for every sum/prod
    BASE_TYPE = "AST"
    # A mapping between ASDL types => Native DB types
    TYPE_MAP = {}
    # Required fields for reiz.schema.Schema
    SCHEMA_FIELDS = [
        "unique_fields",
        "tag_exclusions",
        "module_annotated_types",
    ]


def generate_schema(*args, **kwargs):
    raise NotImplementedError
