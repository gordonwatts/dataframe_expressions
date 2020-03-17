from __future__ import annotations
import ast
from typing import Optional, Any, Union


class DataFrameTypeError(Exception):
    '''Thrown when we don't understand the type in an expression'''
    def __init__(self, message):
        Exception.__init__(self, message)


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
        return Column(type(bool), ast.BoolOp(op=ast.And(),
                      values=[_term_to_ast(self), _term_to_ast(other)]))

    def __or__(self, other) -> Column:
        ''' Bitwise and becomes a logical and. '''
        return Column(type(bool), ast.BoolOp(op=ast.Or(),
                      values=[_term_to_ast(self), _term_to_ast(other)]))


class DataFrame:
    '''
    Base class for building a dataframe expression.

    Notes:
        - Any properties we have here will hide the name of a column in this data frame
    '''
    def __init__(self, pnt=None, expr: Optional[ast.AST] = None, filter: Optional[Column] = None):
        '''
        Create the base DataFrame that is at the top of the parse tree.

        Arguments
            p           Parent dataframe we are coming from
            expr        Expression to be applied to the parent
        '''
        self.parent: Optional[DataFrame] = pnt
        self.child_expr: Optional[ast.AST] = expr
        self.filter = filter

    def check_attribute_name(self, name) -> None:
        'Throw an error if the attribute name is bad'
        pass

    def __getattr__(self, name: str) -> DataFrame:
        '''Reference a column name'''
        # self.check_attribute_name(name)
        child_expr = ast.Attribute(value=ast.Name(id='p', ctx=ast.Load()), attr=name,
                                   ctx=ast.Load())
        return DataFrame(self, child_expr)

    def __getitem__(self, expr) -> DataFrame:
        '''A filtering operation of some sort'''
        assert isinstance(expr, DataFrame) or isinstance(expr, Column), \
            "Filtering a data frame must be done by a DataFrame expression " \
            "(type: DataFrame or Column)"
        return DataFrame(self, None, expr)

    def __array_ufunc__(ufunc, method, *inputs, **kwargs) -> Any:
        '''Take over a numpy or similar execution by turning it into a function call'''
        visitor = getattr(ufunc, method.__name__, None)
        assert visitor is not None, f'Unable to call function "{ufunc.__name__}" on dataframe.'
        return visitor(*inputs[2:], **kwargs)

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
        child_expr = ast.Call(func=self.child_expr, args=[_term_to_ast(a) for a in inputs],
                              keywords=[ast.keyword(arg=k, value=_term_to_ast(v))
                                        for k, v in kwargs.items()])
        return DataFrame(self.parent, child_expr)

    def __binary_operator_compare(self, operator: ast.AST, other: Any) -> Column:
        '''Build a column for a binary operation that results in a column of single values.'''

        # How we do this depends on what other is. We need to encode whatever it is in the AST
        # so that it can be properly unpacked.
        other_ast = _term_to_ast(other)
        compare_ast = ast.Compare(left=_term_to_ast(self), ops=[operator],
                                  comparators=[other_ast])
        return Column(type(bool), compare_ast)

    def __binary_operator(self, operator: ast.AST, other: Any) -> DataFrame:
        '''Build a column for a binary operation that results in a column of single values.'''

        # How we do this depends on what other is. We need to encode whatever it is in the AST
        # so that it can be properly unpacked.
        other_ast = _term_to_ast(other)
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


def _term_to_ast(term: Union[int, str, DataFrame, Column]) -> ast.AST:
    '''Return an AST that represents the current term

    Args:
        term        The term (int, string, float, DataFrame, Column, etc.)

    Returns
    '''
    other_ast = None
    if isinstance(term, int) or isinstance(term, float):
        other_ast = ast.Num(n=term)
    elif isinstance(term, str):
        other_ast = ast.Str(s=term)
    elif isinstance(term, DataFrame):
        other_ast = ast_DataFrame(term)
    elif isinstance(term, Column):
        other_ast = ast_Column(term)
    else:
        raise DataFrameTypeError("Do not know how to compare a DataFrame with something "
                                 f"of type '{type(term).__name__}'.")

    return other_ast
