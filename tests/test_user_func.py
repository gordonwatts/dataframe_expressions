import ast
import inspect

import pytest

from dataframe_expressions import (
    DataFrame, ast_FunctionPlaceholder, ast_DataFrame, render, user_func)


def test_DF_user_func():
    @user_func
    def func1(x: float) -> float:
        assert False

    d = DataFrame()
    d1 = func1(d)

    assert isinstance(d1, DataFrame)
    assert d1.child_expr is not None
    assert isinstance(d1.child_expr, ast.Call)

    f_c = d1.child_expr.func
    assert isinstance(f_c, ast_FunctionPlaceholder)
    f_sig = inspect.signature(f_c.callable)
    assert str(f_sig) == "(x: float) -> float"

    args = d1.child_expr.args
    assert len(args) == 1
    a1 = args[0]
    assert isinstance(a1, ast_DataFrame)


def test_DF_user_number_arg():
    @user_func
    def func1(x: float, y: float) -> float:
        assert False

    d = DataFrame()
    d1 = func1(d, 10.0)

    assert isinstance(d1, DataFrame)
    assert d1.child_expr is not None
    assert isinstance(d1.child_expr, ast.Call)

    f_c = d1.child_expr.func
    assert isinstance(f_c, ast_FunctionPlaceholder)
    f_sig = inspect.signature(f_c.callable)
    assert str(f_sig) == "(x: float, y: float) -> float"

    args = d1.child_expr.args
    assert len(args) == 2
    a1 = args[0]
    assert isinstance(a1, ast_DataFrame)
    a2 = args[1]
    assert isinstance(a2, ast.Num)
    assert a2.n == 10.0


def test_DF_user_wrong_number_args():
    @user_func
    def func1(x: float, y: float) -> float:
        assert False

    d = DataFrame()
    with pytest.raises(Exception):
        func1(d)


def test_DF_user_two_funcs():
    @user_func
    def func1(x: float) -> float:
        assert False

    @user_func
    def func2(x: float, y: float) -> float:
        assert False

    # There should be no confusion between the two functions due to
    # some funny lambda semantics
    d = DataFrame()
    func2(func1(d), func1(d))


def test_DF_user_render():
    @user_func
    def func1(x: float) -> float:
        assert False

    d = DataFrame()
    d1 = func1(d)
    chain, context = render(d1)
    assert chain is not None
    assert context is not None
    assert isinstance(chain, ast.Call)
    call = chain  # type: ast.Call
    assert len(call.args) == 1
    a1 = call.args[0]  # type: ast.AST
    assert isinstance(a1, ast_DataFrame)
    assert a1.dataframe is d

    assert isinstance(call.func, ast_FunctionPlaceholder)
    callable = call.func  # type: ast_FunctionPlaceholder
    f = callable.callable
    assert f.__name__ == 'func1'


# Test expressions in args are not just ast_DataFrames!
