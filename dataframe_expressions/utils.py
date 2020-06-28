import ast
from typing import Callable, Union, Optional, TypeVar
import inspect

from dataframe_expressions import (
    Column, DataFrame, ast_Callable, ast_Column, ast_DataFrame, ast_FunctionPlaceholder)


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
    This will allow a function to be embedded into the DataFrame call sequence. For example,

        ```
        @user_func
        def add_it(p1: float) -> float:
            assert False, 'should never be called'
        ```

        And then if you've got `df` defined as your dataframe, you can write:

        ```
        add_it(df.jets.pt)
        ```

        And the resulting `DataFrame` will effectively call `add_it` on each value of `pt` in the
        sequence.

        There are a lot of limitations in this prototype!
    '''
    def emulate_function_call_in_DF(*args):
        f_sig = inspect.signature(f)
        if len(f_sig.parameters) != len(args):
            raise Exception(f'Function {f.__name__} was called with {len(args)} arguments '
                            f'- but needs {len(f_sig.parameters)}')
        f_args = [_term_to_ast(a, None) for a in args]
        call = ast.Call(func=ast_FunctionPlaceholder(f), args=f_args)
        return DataFrame(expr=call)

    return emulate_function_call_in_DF


T = TypeVar('T')


def exclusive_class(o_class: T) -> T:
    '''
    A class that will extend the object model can only access properties that
    are explicitly defined.
    '''
    orig_init = o_class.__init__

    def __init__(self, *args, **kws):
        # The `__no_arb_attr` is a magic string and appears elsewhere in the code
        # as a flag (its value does not matter)
        self.__no_arb_attr = True
        orig_init(self, *args, **kws)  # Call the original __init__

    o_class.__init__ = __init__  # Set the class' __init__ to the new one
    return o_class
