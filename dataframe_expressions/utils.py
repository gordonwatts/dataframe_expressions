from typing import Union, Callable
import ast
from .DataFrame import DataFrame, Column, ast_DataFrame, ast_Column, ast_Callable


# TODO: Fix the circular include triggered by _term_to_ast


class DataFrameTypeError(Exception):
    '''Thrown when we don't understand the type in an expression'''
    def __init__(self, message):
        Exception.__init__(self, message)


def _term_to_ast(term: Union[int, str, DataFrame, Column, Callable],
                 parent_df: Union[DataFrame, Column]) \
        -> ast.AST:
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
    elif callable(term):
        other_ast = ast_Callable(term, parent_df)
    else:
        raise DataFrameTypeError("Do not know how to render a term "
                                 f"of type '{type(term).__name__}'.")

    return other_ast
