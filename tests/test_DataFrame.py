import ast

from dataframe_expressions.DataFrame import DataFrame, Column, ast_DataFrame

# TODO:
#  Fluent function calls
#  numpy math functions (??)
#  Advanced math operators
#  (https://docs.python.org/3/reference/datamodel.html?highlight=__add__#emulating-numeric-types)
#  the operator "in" (contains)? to see if one jet is in aother collection?
#  the operator len
#  Make sure if d1 and d2 are two different sized,sourced DataFrames, then d1[d2.x] fails
#  Filter functions - so pass a filter that gets called with whatever you are filtering on, and returns.


def test_empty_ctor():
    DataFrame()


def test_dataframe_attribute():
    d = DataFrame()
    ref = d.x
    assert isinstance(ref, DataFrame)
    assert hasattr(ref, 'parent')
    assert ref.parent == d
    assert hasattr(ref, 'child_expr')
    assert isinstance(ref.child_expr, ast.AST)
    assert ast.dump(ref.child_expr) == "Attribute(value=Name(id='p', ctx=Load()), attr='x', ctx=Load())"


def test_mask_operator_const_lt_const():
    d = DataFrame()
    ref = d.x < 10
    assert isinstance(ref, Column)
    assert ref.type == type(bool)
    assert ast.dump(ref.child_expr) == "Compare(left=ast_DataFrame(), ops=[Lt()], comparators=[Num(n=10)])"
    assert isinstance(ref.child_expr, ast.Compare)
    df = ref.child_expr.left  # type: ast.AST
    assert isinstance(df, ast_DataFrame)
    assert df.dataframe.parent is d


def test_mask_operator_2nd_dataframe():
    d = DataFrame()
    ref = d.x < d.y
    assert isinstance(ref, Column)
    assert ref.type == type(bool)
    assert ast.dump(ref.child_expr) == "Compare(left=ast_DataFrame(), ops=[Lt()], comparators=[ast_DataFrame()])"
    assert isinstance(ref.child_expr, ast.Compare)
    df = ref.child_expr.left  # type: ast.AST
    assert isinstance(df, ast_DataFrame)
    assert df.dataframe.parent is d


def test_mask_operator_const_le():
    d = DataFrame()
    ref = d.x <= 10
    assert ast.dump(ref.child_expr) == "Compare(left=ast_DataFrame(), ops=[LtE()], comparators=[Num(n=10)])"


def test_mask_operator_const_gt():
    d = DataFrame()
    ref = d.x > 10
    assert ast.dump(ref.child_expr) == "Compare(left=ast_DataFrame(), ops=[Gt()], comparators=[Num(n=10)])"


def test_mask_operator_const_ge():
    d = DataFrame()
    ref = d.x >= 10
    assert ast.dump(ref.child_expr) == "Compare(left=ast_DataFrame(), ops=[GtE()], comparators=[Num(n=10)])"


def test_mask_operator_const_eq():
    d = DataFrame()
    ref = d.x == 10
    assert ast.dump(ref.child_expr) == "Compare(left=ast_DataFrame(), ops=[Eq()], comparators=[Num(n=10)])"


def test_mask_operator_const_ne():
    d = DataFrame()
    ref = d.x != 10
    assert ast.dump(ref.child_expr) == "Compare(left=ast_DataFrame(), ops=[NotEq()], comparators=[Num(n=10)])"


def test_mask_operator_and():
    d = DataFrame()
    ref1 = d.x != 10
    ref2 = d.x != 8
    ref3 = ref1 & ref2
    assert ast.dump(ref3.child_expr) == "BoolOp(op=And(), values=[ast_Column(), ast_Column()])"


def test_mask_operator_or():
    d = DataFrame()
    ref1 = d.x != 10
    ref2 = d.x != 8
    ref3 = ref1 | ref2
    assert ast.dump(ref3.child_expr) == "BoolOp(op=Or(), values=[ast_Column(), ast_Column()])"


def test_masking_df():
    d = DataFrame()
    d1 = d[d.x > 10]
    assert isinstance(d1, DataFrame)
    assert d1.child_expr is None
    assert isinstance(d1.filter, Column)
    assert ast.dump(d1.filter.child_expr) == "Compare(left=ast_DataFrame(), ops=[Gt()], comparators=[Num(n=10)])"


def test_math_division():
    d = DataFrame()
    d1 = d.x/1000
    assert d1.filter is None
    assert ast.dump(d1.child_expr) == "BinOp(left=Name(id='p', ctx=Load()), op=Div(), right=Num(n=1000))"


def test_math_mult():
    d = DataFrame()
    d1 = d.x*1000
    assert d1.filter is None
    assert ast.dump(d1.child_expr) == "BinOp(left=Name(id='p', ctx=Load()), op=Mult(), right=Num(n=1000))"


def test_math_sub():
    d = DataFrame()
    d1 = d.x-1000
    assert d1.filter is None
    assert ast.dump(d1.child_expr) == "BinOp(left=Name(id='p', ctx=Load()), op=Sub(), right=Num(n=1000))"


def test_math_add():
    d = DataFrame()
    d1 = d.x+1000
    assert d1.filter is None
    assert ast.dump(d1.child_expr) == "BinOp(left=Name(id='p', ctx=Load()), op=Add(), right=Num(n=1000))"


def test_np_sin():
    import numpy as np
    d = DataFrame()
    d1 = np.sin(d.x)
    assert d1.filter is None
    assert ast.dump(d1.child_expr) == "Call(func=Attribute(value=Name(id='p', ctx=Load()), attr='sin', ctx=Load()), args=[], keywords=[])"


def test_np_sin_kwargs():
    import numpy as np
    d = DataFrame()
    d1 = np.sin(d.x, bogus=22.0)
    assert d1.filter is None
    assert ast.dump(d1.child_expr) == "Call(func=Attribute(value=Name(id='p', ctx=Load()), attr='sin', ctx=Load()), args=[], keywords=[keyword(arg='bogus', value=Num(n=22.0))])"


def test_np_arctan2_with_args():
    import numpy as np
    d = DataFrame()
    d1 = np.arctan2(d.x, 100.0)
    assert d1.filter is None
    assert ast.dump(d1.child_expr) == "Call(func=Attribute(value=Name(id='p', ctx=Load()), attr='arctan2', ctx=Load()), args=[Num(n=100.0)], keywords=[])"


def test_fluent_function_no_args():
    d = DataFrame()
    d1 = d.count()
    assert d1.filter is None
    assert ast.dump(d1.child_expr) == "Call(func=Attribute(value=Name(id='p', ctx=Load()), attr='count', ctx=Load()), args=[], keywords=[])"


def test_fluent_function_pos_arg():
    d = DataFrame()
    d1 = d.count(22.0)
    assert d1.filter is None
    assert ast.dump(d1.child_expr) == "Call(func=Attribute(value=Name(id='p', ctx=Load()), attr='count', ctx=Load()), args=[Num(n=22.0)], keywords=[])"


def test_fluent_function_kwarg():
    d = DataFrame()
    d1 = d.count(dude=22.0)
    assert d1.filter is None
    assert ast.dump(d1.child_expr) == "Call(func=Attribute(value=Name(id='p', ctx=Load()), attr='count', ctx=Load()), args=[], keywords=[keyword(arg='dude', value=Num(n=22.0))])"
