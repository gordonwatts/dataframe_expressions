import ast

from dataframe_expressions import DataFrame
from dataframe_expressions import ast_Callable, ast_FunctionPlaceholder
from dataframe_expressions import ast_DataFrame


def test_func_place_different():
    def callme1():
        pass

    def callme2():
        pass

    fp1 = ast_FunctionPlaceholder(callme1)
    fp2 = ast_FunctionPlaceholder(callme2)

    assert ast.dump(fp1) != ast.dump(fp2)


def test_func_place_same():
    def callme():
        pass

    fp1 = ast_FunctionPlaceholder(callme)
    fp2 = ast_FunctionPlaceholder(callme)

    assert ast.dump(fp1) == ast.dump(fp2)


def test_callable_same():
    def do_call():
        pass

    d = DataFrame()

    c1 = ast_Callable(do_call, d)
    c2 = ast_Callable(do_call, d)

    assert ast.dump(c1) == ast.dump(c2)


def test_callable_diff():
    def do_call1():
        pass

    def do_call2():
        pass

    d = DataFrame()

    c1 = ast_Callable(do_call1, d)
    c2 = ast_Callable(do_call2, d)

    assert ast.dump(c1) != ast.dump(c2)


def test_callable_lambda_diff():
    d = DataFrame()

    c1 = ast_Callable(lambda b1: b1+1, d)
    c2 = ast_Callable(lambda b2: b2+1, d)

    assert ast.dump(c1) != ast.dump(c2)


def test_callable_lambda_same():
    d = DataFrame()

    f = lambda b1: b1+1  # NOQA

    c1 = ast_Callable(f, d)
    c2 = ast_Callable(f, d)

    assert ast.dump(c1) == ast.dump(c2)


def test_df_none():
    'Need to make sure the blank ctor is legal for deep copy reasons'
    _ = ast_DataFrame()
