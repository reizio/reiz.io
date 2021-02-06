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
        for field, value in vars(node).items():
            if isinstance(value, BaseAST):
                self.visit(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(value, BaseAST):
                        self.visit(value)

    def ensure(self, condition):
        if not condition:
            raise QuitOptimization

    @staticmethod
    def guarded(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                res = func(*args, **kwargs)
            except QuitOptimization:
                return None
            else:
                return res

        return wrapper
