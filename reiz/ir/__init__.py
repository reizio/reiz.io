from reiz.config import config
from reiz.ir.backends import edgeql
from reiz.ir.builder import IRBuilder, get_ir_builder
from reiz.ir.printer import IRPrinter

IR = get_ir_builder(config.ir.backend)
Schema = IR.schema

IR.add_prepared_query(
    "module.filenames",
    IR.select("Module", selections=[IR.selection("filename")]),
)

IR.add_prepared_query(
    "project.names", IR.select("project", selections=[IR.selection("name")])
)
