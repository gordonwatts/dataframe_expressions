import ast
import inspect
from typing import List, Optional, Union, Callable

from dataframe_expressions.asts import ast_Callable, ast_Column, ast_FunctionPlaceholder

from .data_frame import Column, DataFrame, ast_DataFrame

ItemType = Union[ast.AST, DataFrame, Column]


class var_context:
    def __init__(self):
        self._df_counter = 1
        self._var_memory = {}

    def _normalize(self, a: ItemType) -> ItemType:
        if isinstance(a, ast_DataFrame):
            return a.dataframe
        if isinstance(a, ast_Column):
            return a.column
        return a

    def new_df(self, a: ItemType) -> str:
        a = self._normalize(a)

        if id(a) in self._var_memory:
            return self.lookup(a)

        r = f'df_{self._df_counter}'
        self._var_memory[id(a)] = r
        self._df_counter += 1
        return r

    def define_df(self, a: ItemType, r: str):
        a = self._normalize(a)
        self._var_memory[id(a)] = r

    def add_syn(self, new_item: ItemType, old_item: ItemType):
        s = self.lookup(old_item)
        self._var_memory[id(new_item)] = s

    def is_defined(self, a: ItemType) -> bool:
        a = self._normalize(a)
        return id(a) in self._var_memory

    def lookup(self, a: ItemType) -> str:
        a = self._normalize(a)
        if id(a) not in self._var_memory:
            raise Exception("Attempt to find non-existing dataframe")
        return self._var_memory[id(a)]


_binary_operators = {
    ast.Add: '+',
    ast.Sub: '-',
    ast.Mult: '*',
    ast.Div: '/',
    ast.Eq: '==',
    ast.NotEq: '!=',
    ast.Lt: '<',
    ast.Gt: '>',
    ast.LtE: '<=',
    ast.GtE: '>=',
    ast.And: '&',
    ast.Or: '|',
}


def parse_ast(a: Optional[ast.AST], context: var_context) -> List[str]:
    result = []

    class ast_traverser(ast.NodeVisitor):
        def visit(self, node: ast.AST):
            'Do not repeat visit a node we have already visited'
            if not context.is_defined(node):
                ast.NodeVisitor.visit(self, node)

        def generic_visit(self, node: ast.AST):
            nonlocal result
            result.append(f'{context.new_df(node)} = {type(node).__name__}(')
            ast.NodeVisitor.generic_visit(self, node)
            result.append(')')

        def visit_ast_DataFrame(self, node: ast_DataFrame):
            nonlocal result
            result += dumps(node.dataframe, context)

        def visit_ast_Column(self, node: ast_Column):
            nonlocal result
            result += dumps(node.column, context)

        def _resolve_args(self, args) -> str:
            arg_list = []
            for a in args:
                self.visit(a)
                arg_list.append(context.lookup(a))
            arg_list_str = ','.join(arg_list)
            return arg_list_str

        def _resolve_kwargs(self, kw: List[ast.keyword]) -> str:
            kw_list = []
            for k in kw:
                self.visit(k.value)
                kw_list.append((k.arg, context.lookup(k.value)))
            return ','.join(f'{k_a}={k_v}' for k_a, k_v in kw_list)

        def visit_Call(self, node: ast.Call):
            if isinstance(node.func, ast.Attribute):
                self.visit(node.func.value)
                name = f'{context.lookup(node.func.value)}.{node.func.attr}'
            elif isinstance(node.func, ast_FunctionPlaceholder):
                name = node.func.name  # type: ignore
            elif isinstance(node.func, ast_Callable):
                sig = self._get_callable_sig(node.func.callable)  # type: ignore
                name = f'<{sig}>'
            elif isinstance(node.func, ast.Name):
                name = node.func.id
            else:
                raise Exception(f'Do not know how to translate call to {node.func}')

            # The arguments
            position_arg_list_str = self._resolve_args(node.args)
            kw_list_str = self._resolve_kwargs(node.keywords) if hasattr(node, 'keywords') else ""
            arg_list_str = \
                ','.join([a for a in [position_arg_list_str, kw_list_str] if len(a) > 0])

            result.append(f'{context.new_df(node)} = {name}({arg_list_str})')

        def _get_callable_sig(self, c: Callable):
            s = inspect.signature(c)
            return f'{c.__name__}{s}'

        def visit_ast_Callable(self, node: ast_Callable):
            assert node.callable is not None
            result.append(f'{context.new_df(node)} = {self._get_callable_sig(node.callable)}')

        def visit_Attribute(self, node: ast.Attribute):
            self.visit(node.value)
            nonlocal result
            result.append(f'{context.new_df(node)} = {context.lookup(node.value)}.{node.attr}')

        def visit_BinOp(self, node: ast.BinOp):
            self.visit(node.left)
            self.visit(node.right)
            assert type(node.op) in _binary_operators, 'Unsupported Operator'
            result.append(f'{context.new_df(node)} = {context.lookup(node.left)}'
                          f' {_binary_operators[type(node.op)]} '  # type: ignore
                          f'{context.lookup(node.right)}')

        def visit_Compare(self, node: ast.Compare):
            assert len(node.ops) == 1
            assert len(node.comparators) == 1

            self.visit(node.left)
            self.visit(node.comparators[0])

            assert type(node.ops[0]) in _binary_operators, 'Unsupported operator'
            result.append(f'{context.new_df(node)} = {context.lookup(node.left)}'
                          f' {_binary_operators[type(node.ops[0])]} '  # type: ignore
                          f'{context.lookup(node.comparators[0])}')

        def visit_BoolOp(self, node: ast.BoolOp):
            assert len(node.values) == 2
            for a in node.values:
                self.visit(a)

            assert type(node.op) in _binary_operators, 'Unsupported operator'
            result.append(f'{context.new_df(node)} = {context.lookup(node.values[0])}'
                          f' {_binary_operators[type(node.op)]} '  # type: ignore
                          f'{context.lookup(node.values[1])}')

        def visit_Num(self, node: ast.Num):
            context.define_df(node, str(node.n))

        def visit_Str(self, node: ast.Str):
            context.define_df(node, f"'{str(node.s)}'")

        def visit_Tuple(self, node: ast.Tuple):
            for n in node.elts:
                self.visit(n)
            s = [context.lookup(n) for n in node.elts]
            tuple_text = ','.join(s)
            context.define_df(node, f'({tuple_text})')

        def visit_List(self, node: ast.List):
            for n in node.elts:
                self.visit(n)
            s = [context.lookup(n) for n in node.elts]
            tuple_text = ','.join(s)
            context.define_df(node, f'[{tuple_text}]')

    if a is not None:
        ast_traverser().visit(a)

    return result


def parse_column(c: Optional[Column], context: var_context) -> List[str]:
    if c is None:
        return []
    r = parse_ast(c.child_expr, context)
    context.add_syn(c, c.child_expr)
    return r


def dumps(df: Union[DataFrame, Column],
          context: Optional[var_context] = None) -> List[str]:
    '''
    Do our best to dump a `DataFrame` expression back to python. Result is returned as a
    multi-line string.

    Arguments

        df          `DataFrame` to be dumped

    Returns

        str         Multi-line string result.

    Notes:

        - Any function object that participates in the `DataFrame` rendering (e.g. a
          lambda or the like) can't be looked inside. The dumper will do its best to return
          text that describes what the function is so that one may find it in ones source
          code.
    '''
    if context is None:
        context = var_context()

    # Split out what we are dealing with
    if isinstance(df, DataFrame):

        # Deal with special case
        if df.child_expr is None and df.filter is None:
            if not context.is_defined(df):
                return [f'{context.new_df(df)} = DataFrame()']
            # We will never get here because we do not enter this
            # method if we've already seen this dataframe.
        assert df.child_expr is not None

        filter = parse_column(df.filter, context)
        child = parse_ast(df.child_expr, context)
        ll = [item for lst in [filter, child] for item in lst if len(item) > 0]

        if len(filter) != 0:
            assert df.filter is not None, 'There is no way this ever fires'
            ll.append(f'{context.new_df(df)} = {context.lookup(df.child_expr)}'
                      f'[{context.lookup(df.filter)}]')
        else:
            context.add_syn(df, df.child_expr)

    else:
        assert isinstance(df, Column)
        assert df.child_expr is not None
        child = parse_ast(df.child_expr, context)
        context.add_syn(df, df.child_expr)

        ll = child

    return ll
