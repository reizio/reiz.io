START MIGRATION TO {
    module ast {
        abstract type AST {}
        abstract type mod {}
        type PyModule extending mod, AST {
            multi link body -> stmt;
            multi link type_ignores -> type_ignore;
            required property filename -> str {
                constraint exclusive;
            };
        }
        abstract type stmt {}
        type FunctionDef extending stmt, AST {
            required property name -> str;
            required link args -> arguments;
            multi link body -> stmt;
            multi link decorator_list -> expr;
            link returns -> expr;
            property type_comment -> str;
        }
        type AsyncFunctionDef extending stmt, AST {
            required property name -> str;
            required link args -> arguments;
            multi link body -> stmt;
            multi link decorator_list -> expr;
            link returns -> expr;
            property type_comment -> str;
        }
        type ClassDef extending stmt, AST {
            required property name -> str;
            multi link bases -> expr;
            multi link keywords -> keyword;
            multi link body -> stmt;
            multi link decorator_list -> expr;
        }
        type Return extending stmt, AST {
            link value -> expr;
        }
        type PyDelete extending stmt, AST {
            multi link targets -> expr;
        }
        type Assign extending stmt, AST {
            multi link targets -> expr;
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
            multi link body -> stmt;
            multi link orelse -> stmt;
            property type_comment -> str;
        }
        type AsyncFor extending stmt, AST {
            required link target -> expr;
            required link iter -> expr;
            multi link body -> stmt;
            multi link orelse -> stmt;
            property type_comment -> str;
        }
        type While extending stmt, AST {
            required link test -> expr;
            multi link body -> stmt;
            multi link orelse -> stmt;
        }
        type PyIf extending stmt, AST {
            required link test -> expr;
            multi link body -> stmt;
            multi link orelse -> stmt;
        }
        type PyWith extending stmt, AST {
            multi link items -> withitem;
            multi link body -> stmt;
            property type_comment -> str;
        }
        type AsyncWith extending stmt, AST {
            multi link items -> withitem;
            multi link body -> stmt;
            property type_comment -> str;
        }
        type PyRaise extending stmt, AST {
            link exc -> expr;
            link cause -> expr;
        }
        type Try extending stmt, AST {
            multi link body -> stmt;
            multi link handlers -> excepthandler;
            multi link orelse -> stmt;
            multi link finalbody -> stmt;
        }
        type Assert extending stmt, AST {
            required link test -> expr;
            link msg -> expr;
        }
        type PyImport extending stmt, AST {
            multi link names -> alias;
        }
        type ImportFrom extending stmt, AST {
            property py_module -> str;
            multi link names -> alias;
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
        abstract type expr {}
        type BoolOp extending expr, AST {
            required property op -> boolop;
            multi link values -> expr;
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
            multi link keys -> expr;
            multi link values -> expr;
        }
        type PySet extending expr, AST {
            multi link elts -> expr;
        }
        type ListComp extending expr, AST {
            required link elt -> expr;
            multi link generators -> comprehension;
        }
        type SetComp extending expr, AST {
            required link elt -> expr;
            multi link generators -> comprehension;
        }
        type DictComp extending expr, AST {
            required link key -> expr;
            required link value -> expr;
            multi link generators -> comprehension;
        }
        type GeneratorExp extending expr, AST {
            required link elt -> expr;
            multi link generators -> comprehension;
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
            multi link comparators -> expr;
        }
        type Call extending expr, AST {
            required link func -> expr;
            multi link args -> expr;
            multi link keywords -> keyword;
        }
        type FormattedValue extending expr, AST {
            required link value -> expr;
            property conversion -> int64;
            link format_spec -> expr;
        }
        type JoinedStr extending expr, AST {
            multi link values -> expr;
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
            multi link elts -> expr;
            required property ctx -> expr_context;
        }
        type Tuple extending expr, AST {
            multi link elts -> expr;
            required property ctx -> expr_context;
        }
        scalar type expr_context extending enum<'Load', 'Store', 'Del', 'AugLoad', 'AugStore', 'Param'> {}
        abstract type slice {}
        type Slice extending slice, AST {
            link lower -> expr;
            link upper -> expr;
            link step -> expr;
        }
        type ExtSlice extending slice, AST {
            multi link dims -> slice;
        }
        type Index extending slice, AST {
            required link value -> expr;
        }
        scalar type boolop extending enum<'And', 'Or'> {}
        scalar type operator extending enum<'Add', 'Sub', 'Mult', 'MatMult', 'Div', 'Mod', 'Pow', 'LShift', 'RShift', 'BitOr', 'BitXor', 'BitAnd', 'FloorDiv'> {}
        scalar type unaryop extending enum<'Invert', 'Not', 'UAdd', 'USub'> {}
        scalar type cmpop extending enum<'Eq', 'NotEq', 'Lt', 'LtE', 'Gt', 'GtE', 'Is', 'IsNot', 'In', 'NotIn'> {}
        type comprehension {
            required link target -> expr;
            required link iter -> expr;
            multi link ifs -> expr;
            required property is_async -> int64;
        }
        abstract type excepthandler {}
        type ExceptHandler extending excepthandler, AST {
            link type -> expr;
            property name -> str;
            multi link body -> stmt;
        }
        type arguments {
            multi link posonlyargs -> arg;
            multi link args -> arg;
            link vararg -> arg;
            multi link kwonlyargs -> arg;
            multi link kw_defaults -> expr;
            link kwarg -> arg;
            multi link defaults -> expr;
        }
        type arg {
            required property arg -> str;
            link annotation -> expr;
            property type_comment -> str;
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
    }
};
