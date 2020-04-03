import ast
from typing import Callable, Union, Optional
import inspect

from .DataFrame import (
    Column, DataFrame, ast_Callable, ast_Column, ast_DataFrame, ast_FunctionPlaceholder)


# TODO: Fix the circular include triggered by _term_to_ast


class DataFrameTypeError(Exception):
    '''Thrown when we don't understand the type in an expression'''
    def __init__(self, message):
        Exception.__init__(self, message)


def _term_to_ast(term: Union[int, str, DataFrame, Column, Callable],
                 parent_df: Optional[Union[DataFrame, Column]]) \
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
        assert parent_df is not None, \
            'Internal Error: Parent DF is required when creating a Callable'
        assert isinstance(parent_df, DataFrame)
        other_ast = ast_Callable(term, parent_df)
    else:
        raise DataFrameTypeError("Do not know how to render a term "
                                 f"of type '{type(term).__name__}'.")

    return other_ast


def user_func(f: Callable) -> Callable:
    '''
    This will allow a function to be embded into the DataFrame call sequence. For example,

        ```
        @user_func
        def add_it(p1: float) -> float:
            assert False, 'should never be called'
        ```

        And then if you've got `df` defined as your dataframe, you can write:

        ```
        add_it(df.jets.pt)
        ```

        And the resulting `DataFrame` will effecively call `add_it` on each value of `pt` in the
        sequence.

        There are a lot of limitations in this prototype!
    '''
    def emulate_function_call_in_DF(*args):
        f_sig = inspect.signature(f)
        if len(f_sig.parameters) != len(args):
            raise Exception(f'Function {f.__name__} was called with {len(args)} arguments '
                            '- but needs {len(f_sig.parameters)}')
        f_args = [_term_to_ast(a, None) for a in args]
        call = ast.Call(func=ast_FunctionPlaceholder(f), args=f_args)
        return DataFrame(DataFrame(), expr=call)

    return emulate_function_call_in_DF
