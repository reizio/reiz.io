import functools

from reiz.ir.backends import base

BaseAST = (base.Expression, base.Statement)


class QuitOptimization(Exception):
    ...


class IROptimizer:
    def visit(self, node):
        raise NotImplementedError

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

    def ensure(self, condition):
        if not condition:
            raise QuitOptimization

    @staticmethod
    def guarded(func):
        @functools.wraps(func)
        def wrapper(self, node, *args, **kwargs):
            try:
                res = func(self, node, *args, **kwargs)
            except QuitOptimization:
                return node
            else:
                return res

        return wrapper
