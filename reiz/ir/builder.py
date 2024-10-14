import uuid

from reiz.ir.optimizer import IROptimizer
from reiz.ir.printer import IRPrinter
from reiz.schema import BaseSchema

_IR_BUILDERS = {}


class IRError(Exception): ...


class UnsupportedOperation(IRError): ...


class IRBuilder:
    schema = BaseSchema
    printer = IRPrinter
    optimizer = IROptimizer

    def __init_subclass__(cls, backend_name):
        cls.BACKEND_NAME = backend_name
        cls.PREPARED_QUERIES = {}
        _IR_BUILDERS[backend_name.casefold()] = cls()

    def negate(self, node):
        return self.unary_operation(node, operator="NOT")

    def combine_filters(self, left, right, operator="AND"):
        if left is None:
            return right
        else:
            return self.filter(left, right, operator)

    def unpack_filters(self, filters, operator="AND"):
        left = None
        for right in filters:
            left = self.combine_filters(left, right)
        return left

    def merge(self, expressions):
        union = next(expressions)
        for expression in expressions:
            union = self.union(union, expression)
        return union

    def _unsupported(self, operation):
        return UnsupportedOperation(
            f"{self.BACKEND_NAME} doesn't support {operation}"
        )

    def add_prepared_query(self, key, node):
        self.PREPARED_QUERIES[key] = node

    def construct(self, node, *, optimize=True, **view_kwargs):
        if optimize:
            optimizer = self.optimizer()
            optimizer.optimize(node)

        view_kwargs.setdefault("top_level", True)
        printer = self.printer()
        printer.view(node, **view_kwargs)
        return printer.construct()

    def construct_prepared(self, key):
        return self.construct(self.PREPARED_QUERIES.get(key))

    def new_reference(self, category=None):
        name = str(uuid.uuid4().hex[:8])
        if category:
            name = f"{category}_{name}"
        return self.name(name)


def get_ir_builder(backend_name):
    if backend := _IR_BUILDERS.get(backend_name.casefold()):
        return backend
    else:
        raise IRError(f"{backend_name!r} backend doesn't exist")
