from __future__ import annotations
import ast
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class ast_DataFrame(ast.AST):
    '''Ast that holds onto a DataFrame reference'''
    def __init__(self, dataframe):
        ast.AST.__init__(self)
        self._fields = ()
        self.dataframe = dataframe


class ast_Column(ast.AST):
    '''Ast that holds onto a DataFrame reference'''
    def __init__(self, col):
        ast.AST.__init__(self)
        self._fields = ()
        self.column = col


class ast_Callable(ast.AST):
    'An AST node that is some sort of python callable, along with the df it was called from.'
    def __init__(self, callable: Callable, relative_to: DataFrame):
        '''
        relative_to is optional - in which case this is a function call, not an
        extension method!
        '''
        ast.AST.__init__(self)
        self._fields = ()
        self.callable = callable
        self.dataframe = relative_to


class ast_FunctionPlaceholder(ast.AST):
    'An AST node that represents a function to be called, that is a placeholder'
    def __init__(self, callable: Callable):
        ast.AST.__init__(self)
        self._fields = ()
        self.callable = callable


class Column:
    '''
    Base class for a single sequence. Unlike a `DataFrame` this can't have any complex structure.
    It is a sequence of items, assumed to be of the same type.
    '''
    def __init__(self, t: Any, expr: ast.AST):
        self.child_expr = expr
        self._fields = ('child_expr',)
        self.type = t

    def __and__(self, other) -> Column:
        ''' Bitwise and becomes a logical and. '''
        from .utils import _term_to_ast
        return Column(type(bool), ast.BoolOp(op=ast.And(),
                      values=[_term_to_ast(self, self), _term_to_ast(other, self)]))

    def __or__(self, other) -> Column:
        ''' Bitwise and becomes a logical and. '''
        from .utils import _term_to_ast
        return Column(type(bool), ast.BoolOp(op=ast.Or(),
                      values=[_term_to_ast(self, self), _term_to_ast(other, self)]))

    def __invert__(self) -> Column:
        ''' Invert, or logical NOT operation. '''
        from .utils import _term_to_ast
        return Column(type(bool), ast.UnaryOp(op=ast.Invert(),
                      operand=_term_to_ast(self, self)))


class _sub_link_info:
    '''
    Info on links between dataframes or functions that modify data frames
    '''
    def __init__(self, df: Union[DataFrame, Callable[[DataFrame], DataFrame]],
                 computed_col: bool):
        self._df = df
        self.computed_col = computed_col

    def render(self, df: DataFrame) -> DataFrame:
        '''
        Given the parent DF, render the substitution
        '''
        if isinstance(self._df, DataFrame):
            return self._df
        else:
            assert callable(self._df), 'Internal Error - bad subsititution'
            r = ast_Callable(self._df, df)
            expr = ast.Call(func=r, args=[ast.Name(id='p', ctx=ast.Load())])
            return DataFrame(df, expr=expr)


class DataFrame:
    '''
    Base class for building a dataframe expression.

    Notes:
        - Any properties we have here will hide the name of a column in this data frame
    '''
    def __init__(self, pnt: DataFrame = None,
                 expr: Optional[ast.AST] = None,
                 filter: Optional[Column] = None,
                 df_to_copy: Optional[DataFrame] = None):
        '''
        Create the base DataFrame that is at the top of the parse tree.

        Arguments
            p           Parent dataframe we are coming from
            expr        Expression to be applied to the parent
            filter      A filter to be applied
            df_to_copy  A dataframe to be copied from (like a clone operation)
        '''
        self.parent: Optional[DataFrame] = pnt
        self.child_expr: Optional[ast.AST] = expr
        self.filter = filter
        self._sub_df: Dict[str, _sub_link_info] = {}

        if df_to_copy is not None:
            self.child_expr = df_to_copy.child_expr
            self.filter = df_to_copy.filter
            self._sub_df = df_to_copy._sub_df

    def check_attribute_name(self, name) -> None:
        'Throw an error if the attribute name is bad'
        pass

    def _find_compat_parent_attribute(self, name, computed_col_only: bool = True) \
            -> Optional[Tuple[DataFrame, DataFrame, List[Column]]]:
        '''
        Find a compatible parent's attribute. If not compatible, then
        return none.
        '''
        p = self
        filters: List[Column] = []
        while p is not None:
            if p.filter is not None:
                filters.append(p.filter)

            p = p.parent
            if p is not None:
                if name in p._sub_df and ((not computed_col_only) or p._sub_df[name].computed_col):
                    expr = p._sub_df[name].render(p)
                    return expr, p, filters

                p = p.parent
                if p is not None and p.child_expr is not None:
                    return None

        return None

    def _replace_root_expr(self, parent: DataFrame, filters: List[Column]):
        '''
        Find the parent in our hierarchy, and then insert the new stuff,
        cloning the df as we go back
        '''
        if self is parent:
            # Ok - we found the parent dataframe. Time to create new dataframes with
            # filters.
            df = self
            for f in filters:
                df = DataFrame(df, None, f)
            return df

        if self.parent is None:
            return self

        if self != parent:
            df = self.parent._replace_root_expr(parent, filters)
            # If no replacements happened, then do nothing.
            if df is self.parent:
                return self
            # Clone.
            return DataFrame(df, df_to_copy=self)

    def __getattr__(self, name: str) -> DataFrame:
        '''Reference a column name'''
        # Have we done this before?
        if name not in self._sub_df:
            result = None

            # Resolve any aliases we need
            if result is None:
                from .alias import lookup_alias
                a = lookup_alias(self, name)
                if a is not None:
                    result = a.apply(self)

            # Is this attribute used by anyone above us?
            if result is None:
                p_attr = self._find_compat_parent_attribute(name)
                if p_attr is not None:
                    # Tricky part - we need any of the filters that were accumulated applied.
                    attr, parent, filters = p_attr
                    df = attr._replace_root_expr(parent, filters)
                    result = df

            # Ok - in that case, this is a straight attribute.
            if result is None:
                child_expr = ast.Attribute(value=ast.Name(id='p', ctx=ast.Load()), attr=name,
                                           ctx=ast.Load())
                result = DataFrame(self, child_expr)

            self._sub_df[name] = _sub_link_info(result, False)
        return self._sub_df[name].render(self)

    def __getitem__(self, expr: Union[Callable, DataFrame, Column]) -> DataFrame:
        '''A filtering operation of some sort'''
        assert isinstance(expr, DataFrame) or isinstance(expr, Column) or callable(expr), \
            "Filtering a data frame must be done by a DataFrame expression " \
            f"(type: DataFrame or Column) not '{type(expr).__name__}'"

        if callable(expr) and not (isinstance(expr, DataFrame) or isinstance(expr, Column)):
            c_expr = expr(self)
            assert isinstance(c_expr, DataFrame) or isinstance(c_expr, Column), \
                f"Filter function '{expr.__name__}'' did not return a DataFrame expression"
            expr = c_expr

        if isinstance(expr, DataFrame):
            assert expr.filter is None
            assert expr.child_expr is not None
            assert expr.parent is not None
            from .utils import _replace_parent_references
            child_expr = _replace_parent_references(expr.child_expr, expr.parent)
            expr = Column(bool, child_expr)
        # Redundant, but above too complex for type processor?
        assert isinstance(expr, Column), 'Internal error - filter must be a bool column!'
        return DataFrame(self, None, expr)

    def __setitem__(self, key: str,
                    expr: Union[DataFrame, Callable[[DataFrame], DataFrame]]) \
            -> DataFrame:
        '''
        Add a new leaf to this data frame
        '''
        assert isinstance(key, str)
        assert len(key) > 0
        if key in self._sub_df:
            if not self._sub_df[key].computed_col:
                raise Exception(f'You may not redefine "{key}".')
            else:
                logging.getLogger(__name__).warning('')

        self._sub_df[key] = _sub_link_info(expr, True)
        return self

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs) -> Any:
        '''Take over a numpy or similar execution by turning it into a function call'''
        visitor = getattr(self, ufunc.__name__, None)
        assert visitor is not None, f'Unable to call function "{ufunc.__name__}" on dataframe.'
        return visitor(*inputs[1:], **kwargs)

    def __call__(self, *inputs, **kwargs) -> DataFrame:
        '''
        Someone is trying to turn an attribute into a funciton. That is fine, but it takes some
        fancy footwork on our part. Specifically, what we were thinking of as an attribute is
        actuall a function call. So we have to haul that back to undo the attribute and turn it
        into a funciton call.
        '''
        assert self.child_expr is not None, \
            'Cannot call a DataFrame directly - must be a funciton name!'
        assert isinstance(self.child_expr, ast.Attribute), \
            'Cannot call a DataFrame directly - must be a function name!'
        from .utils import _term_to_ast
        assert self.parent is not None, 'Internal programming error'
        child_expr = ast.Call(func=self.child_expr,
                              args=[_term_to_ast(a, self.parent) for a in inputs],
                              keywords=[ast.keyword(arg=k, value=_term_to_ast(v, self))
                                        for k, v in kwargs.items()])
        return DataFrame(self.parent, child_expr)

    def __abs__(self):
        '''
        Take the absolute value of ourselves using the python default syntax.
        '''
        child_expr = ast.Call(func=ast.Attribute(value=ast.Name('p', ctx=ast.Load()),
                                                 attr='abs', ctx=ast.Load()),
                              args=[], keywords=[])
        return DataFrame(self, child_expr)

    def __binary_operator_compare(self, operator: ast.AST, other: Any) -> Column:
        '''Build a column for a binary operation that results in a column of single values.'''

        # How we do this depends on what other is. We need to encode whatever it is in the AST
        # so that it can be properly unpacked.
        from .utils import _term_to_ast
        other_ast = _term_to_ast(other, self)
        compare_ast = ast.Compare(left=_term_to_ast(self, self), ops=[operator],
                                  comparators=[other_ast])
        return Column(type(bool), compare_ast)

    def __binary_operator(self, operator: ast.AST, other: Any) -> DataFrame:
        '''Build a column for a binary operation that results in a column of single values.'''

        # How we do this depends on what other is. We need to encode whatever it is in the AST
        # so that it can be properly unpacked.
        from .utils import _term_to_ast
        other_ast = _term_to_ast(other, self)
        operated = ast.BinOp(left=ast.Name(id='p', ctx=ast.Load()), op=operator, right=other_ast)
        return DataFrame(self, operated)

    def __lt__(self, other) -> Column:
        ''' x < y '''
        return self.__binary_operator_compare(ast.Lt(), other)

    def __le__(self, other) -> Column:
        ''' x < y '''
        return self.__binary_operator_compare(ast.LtE(), other)

    def __eq__(self, other) -> Column:
        ''' x < y '''
        return self.__binary_operator_compare(ast.Eq(), other)

    def __ne__(self, other) -> Column:
        ''' x < y '''
        return self.__binary_operator_compare(ast.NotEq(), other)

    def __gt__(self, other) -> Column:
        ''' x < y '''
        return self.__binary_operator_compare(ast.Gt(), other)

    def __ge__(self, other) -> Column:
        ''' x < y '''
        return self.__binary_operator_compare(ast.GtE(), other)

    def __truediv__(self, other) -> DataFrame:
        return self.__binary_operator(ast.Div(), other)

    def __mul__(self, other) -> DataFrame:
        return self.__binary_operator(ast.Mult(), other)

    def __add__(self, other) -> DataFrame:
        return self.__binary_operator(ast.Add(), other)

    def __sub__(self, other) -> DataFrame:
        return self.__binary_operator(ast.Sub(), other)
