import ast
import pytest

from dataframe_expressions import DataFrame, render, exclusive_class

from .utils_for_testing import reset_var_counter  # NOQA


class multi_leaf_object(DataFrame):
    def __init__(self, df: DataFrame):
        DataFrame.__init__(self, df)

    @property
    def x1(self):
        return self.x_new_1


class leaf_object(DataFrame):
    def __init__(self, df: DataFrame):
        DataFrame.__init__(self, df)

    @property
    def x2(self):
        return self.x1


def test_collection_object():
    df = DataFrame()
    mlo = multi_leaf_object(df)
    df1 = mlo.x1

    expr, _ = render(df1)
    assert ast.dump(expr) == "Attribute(value=ast_DataFrame(), attr='x_new_1', ctx=Load())"


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
        DataFrame.__init__(self, df)

    @property
    def x1(self):
        return self.x_new_1


@exclusive_class
class leaf_object_excl(DataFrame):
    def __init__(self, df: DataFrame):
        DataFrame.__init__(self, df)

    @property
    def x2(self):
        return self.x1


def test_collection_object_excl():
    df = DataFrame()
    mlo = multi_leaf_object_excl(df)
    df1 = mlo.x1

    expr, _ = render(df1)
    assert ast.dump(expr) == "Attribute(value=ast_DataFrame(), attr='x_new_1', ctx=Load())"


def test_collection_object_other_excl():
    with pytest.raises(Exception) as e:
        df = DataFrame()
        mlo = multi_leaf_object_excl(df)
        df1 = mlo.x12

        expr, _ = render(df1)

    assert 'not such property' in str(e.value())


def test_collection_nested_excl():
    df = DataFrame()
    mlo = multi_leaf_object_excl(df)
    ml1 = leaf_object_excl(mlo)
    df1 = ml1.x2

    expr, _ = render(df1)
    assert ast.dump(expr) == "Attribute(value=ast_DataFrame(), attr='x_new_1', ctx=Load())"


class vec(DataFrame):
    def __init__(self, df: DataFrame) -> None:
        DataFrame.__init__(self, df)

    @property
    def xy(self):
        from numpy import sqrt
        return sqrt(self.x*self.x + self.y*self.y)


def test_xy():
    df = DataFrame()
    v = vec(df)
    df1 = v.xy

    expr, _ = render(df1)
    assert ast.dump(expr) == 'boom'


def test_add_xy():
    df = DataFrame()
    x1 = vec(df.x)
    x2 = vec(df.y)
    df1 = (x1 + x2).xy

    expr, _ = render(df1)
    assert ast.dump(expr) == 'boom'
