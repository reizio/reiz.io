import ast
import json
from functools import cached_property

from reiz.utilities import STATIC_DIR


class BaseSchema:
    with open(STATIC_DIR / "Python-reiz.json") as stream:
        RAW_SCHEMA = json.load(stream)

    def _ast_tuple(self, type_names):
        return tuple(getattr(ast, type_name) for type_name in type_names)

    @cached_property
    def enum_types(self):
        return self._ast_tuple(self.RAW_SCHEMA["enum_types"])

    @cached_property
    def module_annotated_types(self):
        return self._ast_tuple(self.RAW_SCHEMA["module_annotated_types"])

    @cached_property
    def tag_excluded_fields(self):
        return self.RAW_SCHEMA["tag_exclusions"]
