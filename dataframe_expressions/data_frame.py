from __future__ import annotations
import ast
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast

from .asts import ast_Callable, ast_DataFrame
from .utils_ast import CloningNodeTransformer


class Column:
    '''
    Base class for a single sequence. Unlike a `DataFrame` this can't have any complex structure.
    It is a sequence of items, assumed to be of the same type.
    '''
    def __init__(self, t: Any, expr: ast.AST):
        self.child_expr: ast.AST = expr
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
            assert callable(self._df), 'Internal Error - bad substitution'
            r = ast_Callable(self._df, df)
            expr = ast.Call(func=r, args=[ast_DataFrame(df)])
            return DataFrame(expr=expr)


def _do_not_extend(o: object):
    'Test if the object has the "no-extend" flag'
    return '__no_arb_attr' in dir(o)


class DataFrame:
    '''
    Base class for building a dataframe expression.

    Notes:
        - Any properties we have here will hide the name of a column in this data frame
    '''
    def __init__(self,
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
        self.child_expr: Optional[ast.AST] = expr
        self.filter: Optional[Column] = filter

        self._sub_df: Dict[str, _sub_link_info] = {}

        if df_to_copy is not None:
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

            # Make sure we aren't changing the data - if so, then we
            # can't walk back up further.
            if not isinstance(p.child_expr, ast_DataFrame):
                return None

            p = p.child_expr.dataframe
            if name in p._sub_df and ((not computed_col_only) or p._sub_df[name].computed_col):
                # Defined column with extension mechanism
                expr = p._sub_df[name].render(p)
                return expr, p, filters

            if name in dir(p):
                # Column is defined in the object
                # We don't call hasattr as we don't want to generate a new attribute.
                expr = getattr(p, name)
                return expr, p, filters

        return None

    def _replace_root_expr(self, parent: DataFrame, filters: List[Column]):
        '''
        Look through our self, and anything attached to us for the parent dataframe.
        Once we've found it, create a new one, and attach all filters to it.
        '''
        if self is parent:
            # Ok - we found the parent dataframe. Time to create new dataframes with
            # all filters strung on it.
            df = self
            for f in filters:
                df = DataFrame(expr=ast_DataFrame(df), filter=f)
            return df

        # Now we need to recurse and find all data frames and rebuild them.
        class search_for_ast(CloningNodeTransformer):
            def __init__(self):
                CloningNodeTransformer.__init__(self)

            def visit_ast_DataFrame(self, a: ast_DataFrame):
                new_df = a.dataframe._replace_root_expr(parent, filters)
                if new_df is a.dataframe:
                    return a
                return ast_DataFrame(new_df)

        sa_transform = search_for_ast()
        new_child = None if self.child_expr is None else sa_transform.visit(self.child_expr)
        if new_child is not self.child_expr:
            return DataFrame(expr=new_child, filter=self.filter, df_to_copy=self)
        return self

    def __getattr__(self, name: str) -> DataFrame:
        '''Reference a column name'''
        if name.startswith('_'):
            raise AttributeError(name)

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

            # Ok - in that case, this is a straight attribute, as long
            # as we are allowed to do the lookup.
            if result is None:
                if _do_not_extend(self):
                    # Oooo - they are trying to access something we don't know about!
                    raise Exception(f'No such attribute explicitly defined ("{name}")')

                child_expr = ast.Attribute(value=ast_DataFrame(self), attr=name,
                                           ctx=ast.Load())
                result = DataFrame(expr=child_expr)

            self._sub_df[name] = _sub_link_info(result, False)
        return self._sub_df[name].render(self)

    def __getitem__(self, expr: Union[Callable, DataFrame, Column, str, int]) -> DataFrame:
        '''A filtering operation of some sort or a branch look up or a slice'''
        assert isinstance(expr, (DataFrame, Column, int, str)) or callable(expr), \
            "Filtering a data frame must be done by a DataFrame expression " \
            f"(type: DataFrame or Column or int) not '{type(expr).__name__}'"

        # Index into an item
        if isinstance(expr, int):
            c_expr = ast.Subscript(
                value=ast_DataFrame(self),
                slice=ast.Index(value=expr)
            )
            return DataFrame(expr=c_expr)

        # A branch look up - like a ".pt" rather than ['pt']
        if isinstance(expr, str):
            return self.__getattr__(expr)

        if callable(expr) and not (isinstance(expr, DataFrame) or isinstance(expr, Column)):
            c_expr = expr(self)
            assert isinstance(c_expr, DataFrame) or isinstance(c_expr, Column), \
                f"Filter function '{expr.__name__}'' did not return a DataFrame expression"
            expr = c_expr

        if isinstance(expr, DataFrame):
            assert expr.filter is None
            assert expr.child_expr is not None
            expr = Column(bool, expr.child_expr)
        # Redundant, but above too complex for type processor?
        assert isinstance(expr, Column), 'Internal error - filter must be a bool column!'
        return DataFrame(ast_DataFrame(self), filter=expr)

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
        Someone is trying to turn an attribute into a function. That is fine, but it takes some
        fancy footwork on our part. Specifically, what we were thinking of as an attribute is
        actual a function call. So we have to haul that back to undo the attribute and turn it
        into a function call.
        '''
        assert self.child_expr is not None, \
            'Cannot call a DataFrame directly - must be a function name!'
        assert isinstance(self.child_expr, ast.Attribute), \
            'Cannot call a DataFrame directly - must be a function name!'
        from .utils import _term_to_ast
        assert isinstance(self.child_expr, ast.Attribute)
        assert isinstance(self.child_expr.value, ast_DataFrame)
        base_df = cast(ast_DataFrame, self.child_expr.value)
        child_expr = ast.Call(func=self.child_expr,
                              args=[_term_to_ast(a, base_df.dataframe) for a in inputs],
                              keywords=[ast.keyword(arg=k, value=_term_to_ast(v, self))
                                        for k, v in kwargs.items()])
        return DataFrame(expr=child_expr)

    def _test_for_extension(self, name: str):
        'If we have the no-extension flag, then bomb out'
        if _do_not_extend(self):
            raise Exception(f'Object {type(self).__name__} does not have "{name}" defined')

    def __abs__(self):
        '''
        Take the absolute value of ourselves using the python default syntax.
        '''
        self._test_for_extension('abs')
        child_expr = ast.Call(func=ast.Attribute(value=ast_DataFrame(self),
                                                 attr='abs', ctx=ast.Load()),
                              args=[], keywords=[])
        return DataFrame(expr=child_expr)

    def __invert__(self) -> DataFrame:
        ''' Invert, or logical NOT operation. '''
        self._test_for_extension('operator invert')
        child_expr = ast.UnaryOp(op=ast.Invert(), operand=ast_DataFrame(self))
        return DataFrame(child_expr)

    def __and__(self, other) -> Column:
        ''' Bitwise and becomes a logical and. '''
        self._test_for_extension('operator and')
        from .utils import _term_to_ast
        return Column(type(bool), ast.BoolOp(op=ast.And(),
                      values=[_term_to_ast(self, None), _term_to_ast(other, None)]))

    def __or__(self, other) -> Column:
        ''' Bitwise and becomes a logical and. '''
        self._test_for_extension('operator or')
        from .utils import _term_to_ast
        return Column(type(bool), ast.BoolOp(op=ast.Or(),
                      values=[ast.Name('p', ctx=ast.Load()), _term_to_ast(other, self)]))

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
        operated = ast.BinOp(left=ast_DataFrame(self), op=operator, right=other_ast)
        return DataFrame(operated)

    def __lt__(self, other) -> Column:
        ''' x < y '''
        self._test_for_extension('operator lt')
        return self.__binary_operator_compare(ast.Lt(), other)

    def __le__(self, other) -> Column:
        ''' x < y '''
        self._test_for_extension('operator le')
        return self.__binary_operator_compare(ast.LtE(), other)

    def __eq__(self, other) -> Column:
        ''' x < y '''
        self._test_for_extension('operator eq')
        return self.__binary_operator_compare(ast.Eq(), other)

    def __ne__(self, other) -> Column:
        ''' x < y '''
        self._test_for_extension('operator ne')
        return self.__binary_operator_compare(ast.NotEq(), other)

    def __gt__(self, other) -> Column:
        ''' x < y '''
        self._test_for_extension('operator gt')
        return self.__binary_operator_compare(ast.Gt(), other)

    def __ge__(self, other) -> Column:
        ''' x < y '''
        self._test_for_extension('operator ge')
        return self.__binary_operator_compare(ast.GtE(), other)

    def __truediv__(self, other) -> DataFrame:
        self._test_for_extension('operator truediv')
        return self.__binary_operator(ast.Div(), other)

    def __mul__(self, other) -> DataFrame:
        self._test_for_extension('operator mul')
        return self.__binary_operator(ast.Mult(), other)

    def __add__(self, other) -> DataFrame:
        self._test_for_extension('operator add')
        return self.__binary_operator(ast.Add(), other)

    def __sub__(self, other) -> DataFrame:
        self._test_for_extension('operator sub')
        return self.__binary_operator(ast.Sub(), other)
