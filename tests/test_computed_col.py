import ast
from typing import cast

import pytest

from dataframe_expressions import DataFrame, user_func
from dataframe_expressions.asts import ast_Callable, ast_DataFrame

from .utils_for_testing import reset_var_counter  # NOQA


def test_create_col_with_text():
    df = DataFrame()
    df.jets['ptgev'] = df.jets.pt / 1000
    d1 = df.jets.ptgev

    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == "BinOp(left=ast_DataFrame(), op=Div(), right=Num(n=1000))"


def test_create_col_access_with_text():
    df = DataFrame()
    df.jets['ptgev'] = df.jets.pt / 1000
    d1 = df.jets['ptgev']

    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == "BinOp(left=ast_DataFrame(), op=Div(), right=Num(n=1000))"


def test_create_col_twice():
    df = DataFrame()
    df.jets['ptgev'] = df.jets.pt / 1000.0

    # This should generate a warning, but nothing else.
    df.jets['ptgev'] = df.jets.pt / 1001
    d1 = df.jets.ptgev

    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == "BinOp(left=ast_DataFrame(), op=Div(), right=Num(n=1001))"


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
    assert isinstance(d1.child_expr, ast.BinOp)
    assert ast.dump(d1.child_expr) == "BinOp(left=ast_DataFrame(), op=Div(), right=Num(n=1000))"
    assert isinstance(d1.child_expr.left, ast_DataFrame)
    d1_parent = cast(ast_DataFrame, d1.child_expr.left).dataframe
    assert d1_parent.child_expr is not None
    assert ast.dump(d1_parent.child_expr) == "Attribute(value=ast_DataFrame(), attr='pt', ctx=Load())"
    assert isinstance(d1_parent.child_expr, ast.Attribute)
    assert isinstance(d1_parent.child_expr.value, ast_DataFrame)
    p_df = cast(ast_DataFrame, d1_parent.child_expr.value).dataframe
    assert isinstance(p_df.child_expr, ast_DataFrame)
    assert p_df.filter is not None
    assert ast.dump(p_df.filter.child_expr) == "Compare(left=ast_DataFrame(), ops=[Lt()], comparators=[Num(n=2.4)])"


def test_create_col_yuck_doesnot_track():
    df = DataFrame()
    df.jets['ptgev'] = df.met
    d1 = df.jets[df.jets.eta < 2.4].ptgev

    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == "Attribute(value=ast_DataFrame(), attr='met', ctx=Load())"
    assert isinstance(d1.child_expr, ast.Attribute)
    d1_parent = d1.child_expr.value
    assert isinstance(d1_parent, ast_DataFrame)
    p_df = cast(ast_DataFrame, d1_parent).dataframe
    assert p_df is df


def test_create_col_no_confusion():
    df = DataFrame()
    df.jets['ptgev'] = df.jets.pt / 1000.0
    d1 = df.jets.pt.ptgev
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == "Attribute(value=ast_DataFrame(), attr='ptgev', ctx=Load())"


def test_create_col_with_filter_access():
    df = DataFrame()
    good_jets = df.jets[df.jets.pt > 30]
    good_jets['ptgev'] = good_jets.pt / 1000
    d1 = good_jets.ptgev

    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == "BinOp(left=ast_DataFrame(), op=Div(), right=Num(n=1000))"


def test_create_col_with_filter_early_access():
    df = DataFrame()
    good_jets = df.jets[df.jets.pt > 30]
    good_jets['ptgev'] = good_jets.pt / 1000.0
    d1 = df.jets.ptgev

    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == "Attribute(value=ast_DataFrame(), attr='ptgev', ctx=Load())"


def test_create_col_with_lambda():
    df = DataFrame()
    df.jets['ptgev'] = lambda j: j.pt / 1000
    d1 = df.jets.ptgev

    assert d1.child_expr is not None
    assert isinstance(d1.child_expr, ast.Call)
    assert len(d1.child_expr.args) == 1
    assert isinstance(d1.child_expr.args[0], ast_DataFrame)
    p = cast(ast_DataFrame, d1.child_expr.args[0]).dataframe
    assert isinstance(p.child_expr, ast.Attribute)

    assert isinstance(d1.child_expr.func, ast_Callable)
    assert cast(ast_Callable, d1.child_expr.func).dataframe is p


def test_col_twice_nested():
    df = DataFrame()
    df.jets['ptgev'] = lambda j: j.pt / 1000.0
    good_jets = df.jets[df.jets.pt > 35]
    d1 = good_jets.ptgev

    # Make sure correct df is referenced here
    assert d1.child_expr is not None
    assert "Call(func=ast_Callable(name='lambda" in ast.dump(d1.child_expr)
    assert d1.filter is None

    assert isinstance(d1.child_expr, ast.Call)
    assert len(d1.child_expr.args) == 1
    assert isinstance(d1.child_expr.args[0], ast_DataFrame)
    p = cast(ast_DataFrame, d1.child_expr.args[0]).dataframe
    assert p.filter is not None


def test_nested_col_access():
    df = DataFrame()

    @user_func
    def DeltaR(p1_eta: float) -> float:
        '''
        Calculate the DeltaR between two particles given their `eta` and `phi` locations.
        Implemented on the back end.
        '''
        assert False, 'This should never be called'

    mc_part = df.TruthParticles('TruthParticles')
    eles = df.Electrons('Electrons')

    def dr(e, mc):
        'Make calculating DR easier as I have a hard-to-use DR calculation function on the back end'
        return DeltaR(e.eta())

    def very_near2(mcs, e):
        'Return all particles in mcs that are DR less than 0.5'
        return mcs[lambda m: dr(e, m) < 0.1]

    eles['near_mcs'] = lambda reco_e: very_near2(mc_part, reco_e)

    eles['hasMC'] = lambda e: e.near_mcs.Count() > 0
    good_eles_with_mc = eles[eles.hasMC]
    good_eles_with_mc['mc'] = lambda e: e.near_mcs.First().ptgev

    d1 = good_eles_with_mc.mc

    assert d1.filter is None
    assert d1.child_expr is not None
    assert isinstance(d1.child_expr, ast.Call)
    assert isinstance(d1.child_expr.func, ast_Callable)

    assert isinstance(d1.child_expr, ast.Call)
    assert len(d1.child_expr.args) == 1
    assert isinstance(d1.child_expr.args[0], ast_DataFrame)
    p = cast(ast_DataFrame, d1.child_expr.args[0]).dataframe

    assert cast(ast_Callable, d1.child_expr.func).dataframe is p
