from __future__ import annotations

import ast
from typing import Any, Callable, Optional, cast

import pytest

from dataframe_expressions import (DataFrame, ast_DataFrame, exclusive_class,
                                   render)

from .utils_for_testing import reset_var_counter  # NOQA


class multi_leaf_object(DataFrame):
    def __init__(self, df: DataFrame):
        DataFrame.__init__(self, expr=ast_DataFrame(df))

    @property
    def x1(self) -> DataFrame:
        return self.x_new_1


class leaf_object(DataFrame):
    def __init__(self, df: DataFrame):
        DataFrame.__init__(self, expr=ast_DataFrame(df))

    @property
    def x2(self) -> DataFrame:
        return self.x1


def test_collection_object():
    df = DataFrame()
    mlo = multi_leaf_object(df)
    df1 = mlo.x1

    expr, _ = render(df1)
    assert ast.dump(expr) == "Attribute(value=ast_DataFrame(), attr='x_new_1', ctx=Load())"


def test_collection_subtract():
    df = DataFrame()
    mlo1 = multi_leaf_object(df.m1)
    mlo2 = multi_leaf_object(df.m2)
    df1 = mlo1-mlo2

    expr, _ = render(df1)
    assert ast.dump(expr) == "BinOp(left=Attribute(value=ast_DataFrame(), attr='m1', " \
        "ctx=Load()), op=Sub(), right=Attribute(value=ast_DataFrame(), attr='m2', ctx=Load()))"


def test_collection_object_other():
    df = DataFrame()
    mlo = multi_leaf_object(df)
    df1 = mlo.x12

    expr, _ = render(df1)
    assert ast.dump(expr) == "Attribute(value=ast_DataFrame(), attr='x12', ctx=Load())"


def test_collection_nested():
    df = DataFrame()
    mlo = multi_leaf_object(df)
    ml1 = leaf_object(mlo)
    df1 = ml1.x2

    expr, _ = render(df1)
    assert ast.dump(expr) == "Attribute(value=ast_DataFrame(), attr='x_new_1', ctx=Load())"


@exclusive_class
class multi_leaf_object_excl(DataFrame):
    def __init__(self, df: DataFrame):
        DataFrame.__init__(self, expr=ast_DataFrame(df))
        self.__p = df

    @property
    def x1(self) -> DataFrame:
        return self.__p.x_new_1


@exclusive_class
class leaf_object_excl(DataFrame):
    def __init__(self, df: DataFrame):
        DataFrame.__init__(self, expr=ast_DataFrame(df))
        self.__p = df

    @property
    def x2(self) -> DataFrame:
        return self.__p.x1


def test_collection_object_excl():
    df = DataFrame()
    mlo = multi_leaf_object_excl(df)
    df1 = mlo.x1

    expr, _ = render(df1)
    assert ast.dump(expr) == "Attribute(value=ast_DataFrame(), attr='x_new_1', ctx=Load())"


def test_collection_subtract_excl():
    df = DataFrame()
    mlo1 = multi_leaf_object_excl(df.m1)
    mlo2 = multi_leaf_object_excl(df.m2)
    with pytest.raises(Exception) as e:
        mlo1-mlo2

    assert "operator" in str(e.value)
    assert "multi_leaf_object" in str(e.value)


def test_collection_object_other_excl():
    with pytest.raises(Exception) as e:
        df = DataFrame()
        mlo = multi_leaf_object_excl(df)
        df1 = mlo.x12

        expr, _ = render(df1)

    assert 'No such attribute' in str(e.value)


def test_collection_nested_excl():
    df = DataFrame()
    mlo = multi_leaf_object_excl(df)
    ml1 = leaf_object_excl(mlo)
    df1 = ml1.x2

    expr, _ = render(df1)
    assert ast.dump(expr) == "Attribute(value=ast_DataFrame(), attr='x_new_1', ctx=Load())"


class op_base:
    def render(self, f: Callable[[vec], Any]) -> Any:
        assert False, 'not implemented'


class op_bin(op_base):
    def __init__(self, a: op_base, b: op_base):
        self._a = a
        self._b = b

    def render(self, f: Callable[[vec], Any]) -> Any:
        return self._a.render(f) + self._b.render(f)


class op_vec(op_base):
    def __init__(self, a: vec):
        self._a = a

    def render(self, f: Callable[[vec], Any]) -> Any:
        return f(self._a)


class vec(DataFrame):
    def __init__(self, df: Optional[DataFrame], compound: Optional[op_base] = None) -> None:
        DataFrame.__init__(self, expr=ast_DataFrame(df))
        self._ref: op_base = compound if compound is not None else op_vec(self)

    @property
    def xy(self) -> DataFrame:
        from numpy import sqrt
        bx = self._ref.render(lambda v: v.x)
        by = self._ref.render(lambda v: v.y)
        return sqrt(bx*bx + by*by)

    def __add__(self, other: vec) -> vec:
        'Do the addition'
        return vec(None, op_bin(self._ref, other._ref))


def test_xy():
    df = DataFrame()
    v = vec(df)
    df1 = v.xy

    expr, _ = render(df1)
    assert isinstance(expr, ast.Call)
    assert isinstance(expr.func, ast.Name)
    assert expr.func.id == 'sqrt'
    assert len(expr.args) == 1
    assert isinstance(expr.args[0], ast.BinOp)
    assert isinstance(cast(ast.BinOp, expr.args[0]).op, ast.Add)


def test_add_xy():
    df = DataFrame()
    x1 = vec(df.x)
    x2 = vec(df.y)
    df1 = (x1 + x2).xy

    expr, _ = render(df1)
    assert isinstance(expr, ast.Call)
    assert isinstance(expr.func, ast.Name)
    assert expr.func.id == 'sqrt'
    assert isinstance(expr.args[0], ast.BinOp)
    assert isinstance(cast(ast.BinOp, expr.args[0]).op, ast.Add)

    x_component2 = cast(ast.BinOp, expr.args[0]).left
    assert isinstance(x_component2, ast.BinOp)
    assert isinstance(x_component2.op, ast.Mult)

    x_component = x_component2.left
    assert isinstance(x_component, ast.BinOp)
    assert ast.dump(x_component) == "BinOp(left=Attribute(value=Attribute(value=ast_DataFrame()," \
        " attr='x', ctx=Load()), attr='x', ctx=Load()), " \
        "op=Add(), " \
        "right=Attribute(value=Attribute(value=ast_DataFrame(), attr='y', ctx=Load()), " \
        "attr='x', ctx=Load()))"
