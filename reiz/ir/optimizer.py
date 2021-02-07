import functools

from reiz.ir.backends import base

BaseAST = (base.Expression, base.Statement)


class QuitOptimization(Exception):
    @property
    def node(self):
        if len(self.args) >= 1:
            return self.args[0]
        else:
            return None


class IROptimizer:
    OPTIMIZATIONS = {}

    def visit(self, node):
        node_type = type(node)
        optimizations = self.OPTIMIZATIONS.get(node_type, [])
        for optimization in optimizations:
            node = optimization(self, node)
            if not isinstance(node, node_type):
                break
        return self.generic_visit(node)

    def optimize(self, node):
        self.visit(node)

    def generic_visit(self, node):
        if not isinstance(node, BaseAST):
            return node

        for field, value in vars(node).items():
            if isinstance(value, BaseAST):
                setattr(node, field, self.visit(value))
            elif isinstance(value, list):
                replacement = []
                for item in value:
                    replacement_item = self.visit(item)
                    if isinstance(replacement_item, list):
                        replacement.extend(replacement_item)
                    elif replacement_item is not None:
                        replacement.append(replacement_item)
        return node

    def ensure(self, condition, node=None):
        if not condition:
            raise QuitOptimization(node)

    @staticmethod
    def optimization(func):
        @functools.wraps(func)
        def wrapper(self, node, *args, **kwargs):
            try:
                replacement = func(self, node, *args, **kwargs)
            except QuitOptimization as exc:
                return exc.node or node
            else:
                return self.visit(replacement)

        return wrapper
