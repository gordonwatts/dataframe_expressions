import ast

from dataframe_expressions import DataFrame, define_alias
from dataframe_expressions.alias import lookup_alias

from .utils_for_testing import reset_var_counter  # NOQA

# TODO: Multiple definitions are not tested or protected against


def test_define_alias_no_error():
    define_alias(".jets", "pts", lambda j: j.pt / 1000.0)


def test_define_alias_no_name_no_err():
    define_alias("", "pts", lambda j: j.pt / 1000.0)


def test_resolve_well_specified_good():
    define_alias(".jets", "pts", lambda j: j.pt / 1000.0)
    df = DataFrame()
    df = df.jets
    r = lookup_alias(df, "pts")
    assert r is not None


def test_resolve_well_specified_nogood_1():
    define_alias(".jets", "pts", lambda j: j.pt / 1000.0)
    df = DataFrame()
    df = df.jets
    r = lookup_alias(df, "pt")
    assert r is None


def test_resolve_root_good():
    define_alias(".", "pts", lambda j: j.pt / 1000.0)
    df = DataFrame()
    df = df
    r = lookup_alias(df, "pts")
    assert r is not None


def test_resolve_well_specified_nogood_2():
    define_alias(".jets", "pts", lambda j: j.pt / 1000.0)
    df = DataFrame()
    df = df
    r = lookup_alias(df, "pts")
    assert r is None


def test_resolve_well_specified_nogood_3():
    define_alias(".jets", "pts", lambda j: j.pt / 1000.0)
    df = DataFrame()
    df = df.eles
    r = lookup_alias(df, "pts")
    assert r is None


def test_resolve_wilecard_good_1():
    define_alias("", "pts", lambda j: j.pt / 1000.0)
    df = DataFrame()
    df = df.jets
    r = lookup_alias(df, "pts")
    assert r is not None


def test_resolve_wilecard_good_2():
    define_alias("", "pts", lambda j: j.pt / 1000.0)
    df = DataFrame()
    r = lookup_alias(df, "pts")
    assert r is not None


def test_resolve_wilecard_ngood():
    define_alias("", "pts", lambda j: j.pt / 1000.0)
    df = DataFrame()
    r = lookup_alias(df, "pt")
    assert r is None


def test_resolve_partial_wildcard_good_1():
    define_alias("jets", "pts", lambda j: j.pt / 1000.0)
    df = DataFrame()
    df = df.jets
    r = lookup_alias(df, "pts")
    assert r is not None


def test_resolve_partial_wildcard_good_2():
    define_alias("jets", "pts", lambda j: j.pt / 1000.0)
    df = DataFrame()
    df = df.eles.jets
    r = lookup_alias(df, "pts")
    assert r is not None


def test_resolve_partial_wildcard_nogood_1():
    define_alias("jets", "pts", lambda j: j.pt / 1000.0)
    df = DataFrame()
    df = df.eles
    r = lookup_alias(df, "pts")
    assert r is None


def test_resolve_partial_wildcard_good_3():
    define_alias("jets", "pts", lambda j: j.pt / 1000.0)
    df = DataFrame()
    df = df.jets
    r = lookup_alias(df, "pts")
    assert r is not None


def test_resolve_two_names_good_1():
    define_alias("jets", "pts", lambda j: j.pt / 1000.0)
    define_alias("eles", "pts", lambda j: j.pt / 2000.0)
    df = DataFrame()
    df = df.jets
    r = lookup_alias(df, "pts")
    assert r is not None
    df1 = r.apply(df)
    assert df1.child_expr is not None
    t = ast.dump(df1.child_expr)
    assert '1000' in t


def test_resolve_two_names_good_2():
    define_alias("jets", "pts", lambda j: j.pt / 1000.0)
    define_alias("eles", "pts", lambda j: j.pt / 2000.0)
    df = DataFrame()
    df = df.eles
    r = lookup_alias(df, "pts")
    assert r is not None
    df1 = r.apply(df)
    assert df1.child_expr is not None
    t = ast.dump(df1.child_expr)
    assert '2000' in t


def test_resolve_hidden_name():
    define_alias("jets", "pt", lambda j: j.pt / 1000.0)

    df = DataFrame()
    df = df.jets
    r = lookup_alias(df, "pt")
    assert r is not None
    df1 = r.apply(df)
    assert df1.child_expr is not None
    t = ast.dump(df1.child_expr)
    assert '1000' in t


# def test_run_with_alias_specified():
#     define_alias(".jets", "pts", lambda j: j.pt / 1000.0)
#     df = DataFrame()
#     d1 = df.jets.pts
#     assert isinstance(d1, DataFrame)
#     assert d1.filter is None
#     assert d1.child_expr is not None
#     assert ast.dump(d1.child_expr) == "BinOp(left=Name(id='p', ctx=Load()), op=Div(), right=Num(n=1000))"
#     assert isinstance(d1.parent.child_expr, ast.Attribute)


# def test_run_with_alias_generic():
#     define_alias("", "pts", lambda j: j.pt / 1000.0)
#     df = DataFrame()
#     d1 = df.jets.pts
#     assert isinstance(d1, DataFrame)
#     assert d1.filter is None
#     assert d1.child_expr is not None
#     assert ast.dump(d1.child_expr) == "BinOp(left=Name(id='p', ctx=Load()), op=Div(), right=Num(n=1000))"
#     assert isinstance(d1.parent.child_expr, ast.Attribute)


# def test_run_with_alias_generic_with_path():
#     define_alias("jets", "pts", lambda j: j.pt / 1000.0)
#     df = DataFrame()
#     d1 = df.jets.pts
#     assert isinstance(d1, DataFrame)
#     assert d1.filter is None
#     assert d1.child_expr is not None
#     assert ast.dump(d1.child_expr) == "BinOp(left=Name(id='p', ctx=Load()), op=Div(), right=Num(n=1000))"
#     assert isinstance(d1.parent.child_expr, ast.Attribute)


# def test_run_with_alias_generic_with_path_nomatch():
#     define_alias("jets", "pts", lambda j: j.pt / 1000.0)
#     df = DataFrame()
#     d1 = df.Electrons.pts
#     assert isinstance(d1, DataFrame)
#     assert d1.filter is None
#     assert d1.child_expr is not None
#     assert isinstance(d1.parent, ast.Attribute)
