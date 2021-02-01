from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from typing import List


@dataclass
class IRPrinter:
    source: List[str] = field(default_factory=list)
    indentation_level: int = 0

    def construct(self):
        lines = "".join(self.source).splitlines()
        return "\n".join(line for line in lines if line and not line.isspace())

    def write(self, source):
        assert isinstance(source, str)
        self.source.append(source)

    def newline(self):
        self.write("\n")
        self.write(self.indent)

    def indent_if_newline(self):
        if len(self.source) >= 2:
            if self.source[-1].isspace() and self.source[-2] == "\n":
                self.source.pop()

        if self.source and self.source[-1] == "\n":
            self.write(self.indent)

    def view(self, ir_node):
        raise NotImplementedError

    def sequence_view(self, ir_nodes, delimiter=None):
        raise NotImplementedError

    @property
    def indent(self):
        return " " * (4 * self.indentation_level)

    @contextmanager
    def _enter_newlines(self):
        self.newline()
        yield
        self.newline()

    @contextmanager
    def _between(self, string):
        left, right = string
        self.indent_if_newline()
        self.write(left)
        yield
        self.indent_if_newline()
        self.write(right)

    @contextmanager
    def _indented(self):
        self.indentation_level += 1
        yield
        self.indentation_level -= 1

    def between(self, string, condition=True):
        return self._between(string) if condition else nullcontext()

    def indented(self, condition=True):
        return self._indented() if condition else nullcontext()

    def enter_newlines(self, condition=True):
        return self._enter_newlines() if condition else nullcontext()
