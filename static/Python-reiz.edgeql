START MIGRATION TO {
    module ast {
        abstract type AST {}
        type PyModule {
            multi link body -> stmt {
                property index -> int64;
            };
            multi link type_ignores -> type_ignore {
                property index -> int64;
            };
            required property filename -> str {
                constraint exclusive;
            };
            required link project -> project;
        }
        abstract type stmt {
            required property lineno -> int64;
            required property col_offset -> int64;
            property end_lineno -> int64;
            property end_col_offset -> int64;
            link _module -> PyModule;
        }
        type FunctionDef extending stmt, AST {
            required property name -> str;
            required link args -> arguments;
            multi link body -> stmt {
                property index -> int64;
            };
            multi link decorator_list -> expr {
                property index -> int64;
            };
            link returns -> expr;
            property type_comment -> str;
        }
        type AsyncFunctionDef extending stmt, AST {
            required property name -> str;
            required link args -> arguments;
            multi link body -> stmt {
                property index -> int64;
            };
            multi link decorator_list -> expr {
                property index -> int64;
            };
            link returns -> expr;
            property type_comment -> str;
        }
        type ClassDef extending stmt, AST {
            required property name -> str;
            multi link bases -> expr {
                property index -> int64;
            };
            multi link keywords -> keyword {
                property index -> int64;
            };
            multi link body -> stmt {
                property index -> int64;
            };
            multi link decorator_list -> expr {
                property index -> int64;
            };
        }
        type Return extending stmt, AST {
            link value -> expr;
        }
        type PyDelete extending stmt, AST {
            multi link targets -> expr {
                property index -> int64;
            };
        }
        type Assign extending stmt, AST {
            multi link targets -> expr {
                property index -> int64;
            };
            required link value -> expr;
            property type_comment -> str;
        }
        type AugAssign extending stmt, AST {
            required link target -> expr;
            required property op -> operator;
            required link value -> expr;
        }
        type AnnAssign extending stmt, AST {
            required link target -> expr;
            required link annotation -> expr;
            link value -> expr;
            required property simple -> int64;
        }
        type PyFor extending stmt, AST {
            required link target -> expr;
            required link iter -> expr;
            multi link body -> stmt {
                property index -> int64;
            };
            multi link orelse -> stmt {
                property index -> int64;
            };
            property type_comment -> str;
        }
        type AsyncFor extending stmt, AST {
            required link target -> expr;
            required link iter -> expr;
            multi link body -> stmt {
                property index -> int64;
            };
            multi link orelse -> stmt {
                property index -> int64;
            };
            property type_comment -> str;
        }
        type While extending stmt, AST {
            required link test -> expr;
            multi link body -> stmt {
                property index -> int64;
            };
            multi link orelse -> stmt {
                property index -> int64;
            };
        }
        type PyIf extending stmt, AST {
            required link test -> expr;
            multi link body -> stmt {
                property index -> int64;
            };
            multi link orelse -> stmt {
                property index -> int64;
            };
        }
        type PyWith extending stmt, AST {
            multi link items -> withitem {
                property index -> int64;
            };
            multi link body -> stmt {
                property index -> int64;
            };
            property type_comment -> str;
        }
        type AsyncWith extending stmt, AST {
            multi link items -> withitem {
                property index -> int64;
            };
            multi link body -> stmt {
                property index -> int64;
            };
            property type_comment -> str;
        }
        type PyRaise extending stmt, AST {
            link exc -> expr;
            link cause -> expr;
        }
        type Try extending stmt, AST {
            multi link body -> stmt {
                property index -> int64;
            };
            multi link handlers -> excepthandler {
                property index -> int64;
            };
            multi link orelse -> stmt {
                property index -> int64;
            };
            multi link finalbody -> stmt {
                property index -> int64;
            };
        }
        type Assert extending stmt, AST {
            required link test -> expr;
            link msg -> expr;
        }
        type PyImport extending stmt, AST {
            multi link names -> alias {
                property index -> int64;
            };
        }
        type ImportFrom extending stmt, AST {
            property py_module -> str;
            multi link names -> alias {
                property index -> int64;
            };
            property level -> int64;
        }
        type PyGlobal extending stmt, AST {
            multi property names -> str;
        }
        type Nonlocal extending stmt, AST {
            multi property names -> str;
        }
        type Expr extending stmt, AST {
            required link value -> expr;
        }
        type Pass extending stmt, AST {}
        type Break extending stmt, AST {}
        type Continue extending stmt, AST {}
        abstract type expr {
            required property lineno -> int64;
            required property col_offset -> int64;
            property end_lineno -> int64;
            property end_col_offset -> int64;
            property tag -> int64;
            link _module -> PyModule;
        }
        type BoolOp extending expr, AST {
            required property op -> boolop;
            multi link values -> expr {
                property index -> int64;
            };
        }
        type NamedExpr extending expr, AST {
            required link target -> expr;
            required link value -> expr;
        }
        type BinOp extending expr, AST {
            required link left -> expr;
            required property op -> operator;
            required link right -> expr;
        }
        type UnaryOp extending expr, AST {
            required property op -> unaryop;
            required link operand -> expr;
        }
        type Lambda extending expr, AST {
            required link args -> arguments;
            required link body -> expr;
        }
        type IfExp extending expr, AST {
            required link test -> expr;
            required link body -> expr;
            required link orelse -> expr;
        }
        type Dict extending expr, AST {
            multi link keys -> expr {
                property index -> int64;
            };
            multi link values -> expr {
                property index -> int64;
            };
        }
        type PySet extending expr, AST {
            multi link elts -> expr {
                property index -> int64;
            };
        }
        type ListComp extending expr, AST {
            required link elt -> expr;
            multi link generators -> comprehension {
                property index -> int64;
            };
        }
        type SetComp extending expr, AST {
            required link elt -> expr;
            multi link generators -> comprehension {
                property index -> int64;
            };
        }
        type DictComp extending expr, AST {
            required link key -> expr;
            required link value -> expr;
            multi link generators -> comprehension {
                property index -> int64;
            };
        }
        type GeneratorExp extending expr, AST {
            required link elt -> expr;
            multi link generators -> comprehension {
                property index -> int64;
            };
        }
        type Await extending expr, AST {
            required link value -> expr;
        }
        type Yield extending expr, AST {
            link value -> expr;
        }
        type YieldFrom extending expr, AST {
            required link value -> expr;
        }
        type Compare extending expr, AST {
            required link left -> expr;
            multi property ops -> cmpop;
            multi link comparators -> expr {
                property index -> int64;
            };
        }
        type Call extending expr, AST {
            required link func -> expr;
            multi link args -> expr {
                property index -> int64;
            };
            multi link keywords -> keyword {
                property index -> int64;
            };
        }
        type FormattedValue extending expr, AST {
            required link value -> expr;
            property conversion -> int64;
            link format_spec -> expr;
        }
        type JoinedStr extending expr, AST {
            multi link values -> expr {
                property index -> int64;
            };
        }
        type Constant extending expr, AST {
            required property value -> str;
            property kind -> str;
        }
        type Attribute extending expr, AST {
            required link value -> expr;
            required property attr -> str;
            required property ctx -> expr_context;
        }
        type Subscript extending expr, AST {
            required link value -> expr;
            required link slice -> slice;
            required property ctx -> expr_context;
        }
        type Starred extending expr, AST {
            required link value -> expr;
            required property ctx -> expr_context;
        }
        type Name extending expr, AST {
            required property py_id -> str;
            required property ctx -> expr_context;
        }
        type List extending expr, AST {
            multi link elts -> expr {
                property index -> int64;
            };
            required property ctx -> expr_context;
        }
        type Tuple extending expr, AST {
            multi link elts -> expr {
                property index -> int64;
            };
            required property ctx -> expr_context;
        }
        type Sentinel extending expr, AST {}
        abstract type slice {
            required link sentinel -> expr;
        }
        type Slice extending slice, AST {
            link lower -> expr;
            link upper -> expr;
            link step -> expr;
        }
        type ExtSlice extending slice, AST {
            multi link dims -> slice {
                property index -> int64;
            };
        }
        type Index extending slice, AST {
            required link value -> expr;
        }
        type comprehension {
            required link target -> expr;
            required link iter -> expr;
            multi link ifs -> expr {
                property index -> int64;
            };
            required property is_async -> int64;
        }
        abstract type excepthandler {
            required property lineno -> int64;
            required property col_offset -> int64;
            property end_lineno -> int64;
            property end_col_offset -> int64;
            link _module -> PyModule;
        }
        type ExceptHandler extending excepthandler, AST {
            link type -> expr;
            property name -> str;
            multi link body -> stmt {
                property index -> int64;
            };
        }
        type arguments {
            multi link posonlyargs -> arg {
                property index -> int64;
            };
            multi link args -> arg {
                property index -> int64;
            };
            link vararg -> arg;
            multi link kwonlyargs -> arg {
                property index -> int64;
            };
            multi link kw_defaults -> expr {
                property index -> int64;
            };
            link kwarg -> arg;
            multi link defaults -> expr {
                property index -> int64;
            };
        }
        type arg {
            required property arg -> str;
            link annotation -> expr;
            property type_comment -> str;
            required property lineno -> int64;
            required property col_offset -> int64;
            property end_lineno -> int64;
            property end_col_offset -> int64;
            link _module -> PyModule;
        }
        type keyword {
            property arg -> str;
            required link value -> expr;
        }
        type alias {
            required property name -> str;
            property asname -> str;
        }
        type withitem {
            required link context_expr -> expr;
            link optional_vars -> expr;
        }
        abstract type type_ignore {}
        type TypeIgnore extending type_ignore, AST {
            required property lineno -> int64;
            required property tag -> str;
        }
        scalar type cmpop extending enum<'Eq', 'NotEq', 'Lt', 'LtE', 'Gt', 'GtE', 'Is', 'IsNot', 'In', 'NotIn'> {}
        scalar type expr_context extending enum<'Load', 'Store', 'Del', 'AugLoad', 'AugStore', 'Param'> {}
        scalar type operator extending enum<'Add', 'Sub', 'Mult', 'MatMult', 'Div', 'Mod', 'Pow', 'LShift', 'RShift', 'BitOr', 'BitXor', 'BitAnd', 'FloorDiv'> {}
        scalar type boolop extending enum<'And', 'Or'> {}
        scalar type unaryop extending enum<'Invert', 'Not', 'UAdd', 'USub'> {}
        type project {
            required property name -> str;
            required property git_source -> str;
            required property git_revision -> str;
        }
    }
};
