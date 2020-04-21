import ast

import pytest

from dataframe_expressions import DataFrame

from .utils_for_testing import reset_var_counter  # NOQA


def test_create_col_with_text():
    df = DataFrame()
    df.jets['ptgev'] = df.jets.pt / 1000
    d1 = df.jets.ptgev

    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == "BinOp(left=Name(id='p', ctx=Load()), op=Div(), right=Num(n=1000))"


def test_create_col_twice():
    df = DataFrame()
    df.jets['ptgev'] = df.jets.pt / 1000.0

    # This should generate a warning, but nothing else.
    df.jets['ptgev'] = df.jets.pt / 1001
    d1 = df.jets.ptgev

    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == "BinOp(left=Name(id='p', ctx=Load()), op=Div(), right=Num(n=1001))"


def test_create_access_col_twice():
    df = DataFrame()
    df.jets.ptgev
    with pytest.raises(Exception):
        df.jets['ptgev'] = df.jets.pt / 1000.0


def test_create_col_with_text_filtered():
    df = DataFrame()
    df.jets['ptgev'] = df.jets.pt / 1000
    d1 = df.jets[df.jets.eta < 2.4].ptgev

    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == "BinOp(left=Name(id='p', ctx=Load()), op=Div(), right=Num(n=1000))"
    assert d1.parent is not None
    assert isinstance(d1.parent, DataFrame)
    assert d1.parent.parent is not None
    assert isinstance(d1.parent.parent, DataFrame)
    p_df = d1.parent.parent
    assert p_df.child_expr is None
    assert p_df.filter is not None
    assert ast.dump(p_df.filter.child_expr) == "Compare(left=ast_DataFrame(), ops=[Lt()], comparators=[Num(n=2.4)])"


def test_create_col_yuck_doesnot_track():
    df = DataFrame()
    df.jets['ptgev'] = df.met
    d1 = df.jets[df.jets.eta < 2.4].ptgev

    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == "Attribute(value=Name(id='p', ctx=Load()), attr='met', ctx=Load())"
    assert d1.parent is not None
    assert isinstance(d1.parent, DataFrame)
    p_df = d1.parent
    assert p_df is df


def test_create_col_no_confusion():
    df = DataFrame()
    df.jets['ptgev'] = df.jets.pt / 1000.0
    d1 = df.jets.pt.ptgev
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == "Attribute(value=Name(id='p', ctx=Load()), attr='ptgev', ctx=Load())"


def test_create_col_with_filter_access():
    df = DataFrame()
    good_jets = df.jets[df.jets.pt > 30]
    good_jets['ptgev'] = good_jets.pt / 1000
    d1 = good_jets.ptgev

    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == "BinOp(left=Name(id='p', ctx=Load()), op=Div(), right=Num(n=1000))"


def test_create_col_with_filter_early_access():
    df = DataFrame()
    good_jets = df.jets[df.jets.pt > 30]
    good_jets['ptgev'] = good_jets.pt / 1000.0
    d1 = df.jets.ptgev

    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == "Attribute(value=Name(id='p', ctx=Load()), attr='ptgev', ctx=Load())"


def test_create_col_with_lambda():
    df = DataFrame()
    df.jets['ptgev'] = lambda j: j.pt / 1000
    d1 = df.jets.ptgev

    assert d1.child_expr is not None
    assert isinstance(d1.child_expr, ast.Call)
    assert len(d1.child_expr.args) == 1
    assert isinstance(d1.child_expr.args[0], ast.Name)
    p = d1.parent
    assert isinstance(p, DataFrame)
    assert p.parent is not None
    assert isinstance(p.parent, DataFrame)
    assert p.parent is df
