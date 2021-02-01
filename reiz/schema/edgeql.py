from reiz.schema.base import BaseSchema
from reiz.utilities import STATIC_DIR, singleton


@singleton
class EQLSchema(BaseSchema):
    NAMESPACE = "ast"

    with open(STATIC_DIR / "edgeql" / "keywords.txt") as stream:
        KEYWORDS = stream.read().splitlines()

    def wrap(self, name, with_prefix=False):
        if name.casefold() in self.KEYWORDS:
            if name.istitle():
                name = f"Py{name}"
            else:
                name = f"py_{name}"

        if with_prefix:
            name = f"{self.NAMESPACE}::{name}"

        return name
