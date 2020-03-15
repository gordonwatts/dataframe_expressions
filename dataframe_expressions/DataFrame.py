import ast
from typing import Optional, Any, Union

class DataFrameTypeError(Exception):
    '''Thrown when we don't understand the type in an expression'''
    def __init__ (self, message):
        Exception.__init__(self, message)

class ast_DataFrame(ast.AST):
    '''Ast that holds onto a DataFrame reference'''
    def __init__ (self, dataframe):
        ast.AST.__init__(self)
        self._fields=()
        self.dataframe = dataframe

class ast_Column(ast.AST):
    '''Ast that holds onto a DataFrame reference'''
    def __init__ (self, col):
        ast.AST.__init__(self)
        self._fields=()
        self.column = col

class Column:
    '''
    Base class for a single sequence. Unlike a `DataFrame` this can't have any complex structure. It is
    a sequence of items, assumed to be of the same type.
    '''
    def __init__ (self, t: Any, pnt, expr: ast.AST):
        self.parent = pnt
        self.child_expr = expr
        self.type = t

    def __and__(self, other) -> Any:
        ''' Bitwise and becomes a logical and. '''
        return Column(type(bool), self, ast.BinOp(left=ast.Name(id='p', ctx=ast.Load()), op=ast.BitAnd(), right=_term_to_ast(other)))
        return None

    def __or__(self, other) -> Any:
        ''' Bitwise and becomes a logical and. '''
        return Column(type(bool), self, ast.BinOp(left=ast.Name(id='p', ctx=ast.Load()), op=ast.BitOr(), right=_term_to_ast(other)))
        return None

class DataFrame:
    '''
    Base class for building a dataframe expression.

    Notes:
        - Any properties we have here will hide the name of a column in this data frame
    '''
    def __init__ (self, pnt = None, expr: Optional[ast.AST] = None, filter = None):
        '''
        Create the base DataFrame that is at the top of the parse tree.

        Arguments
            p           Parent dataframe we are coming from
            expr        Expression to be applied to the parent
        '''
        self.parent: Optional[DataFrame] = pnt
        self.child_expr: Optional[ast.AST] = expr
        self.filter = filter

    def check_attribute_name(self, name):
        'Throw an error if the attribute name is bad'
        pass

    def __getattr__(self, name: str) -> Any:
        '''Reference a column name'''
        # self.check_attribute_name(name)
        child_expr = ast.Attribute(value=ast.Name(id='p', ctx=ast.Load()), attr=name, ctx=ast.Load())
        return DataFrame(self, child_expr)

    def __getitem__(self, expr) -> Any:
        '''A filtering operation of some sort'''
        assert isinstance(expr, DataFrame) or isinstance(expr, Column), "Filtering a data frame must be done by a DataFrame expression (type: DataFrame or Column)"
        return DataFrame(self, None, expr)


    def __binary_operator_compare(self, operator: ast.AST, other: Any) -> Column:
        '''Build a column for a binary operation that results in a column of single values.'''

        # How we do this depends on what other is. We need to encode whatever it is in the AST
        # so that it can be properly unpacked.
        other_ast = _term_to_ast(other)
        compare_ast = ast.Compare(left=ast.Name(id='p', ctx=ast.Load()), ops=[operator], comparators=[other_ast])
        return Column(type(bool), self, compare_ast)

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

def _term_to_ast(term) -> ast.AST:
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
        raise DataFrameTypeError(f"Do not know how to compare a DataFrame with something of type '{type(term).__name__}'.")

    return other_ast