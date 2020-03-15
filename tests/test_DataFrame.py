import ast

from dataframe_expressions.DataFrame import DataFrame, Column, DataFrameTypeError

# TODO:
#  the operator "in" (contains)? to see if one jet is in aother collection?
#  the operator len
#  Basic math operators (https://docs.python.org/3/reference/datamodel.html?highlight=__add__#emulating-numeric-types)
#  Operations between columns and dataframes
#  Operations between columns and columns
#  Fluent function calls
#  numpy math functions (??)

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
    assert isinstance (ref, Column)
    assert ref.type == type(bool)
    assert ref.parent != d
    assert ast.dump(ref.child_expr) == "Compare(left=Name(id='p', ctx=Load()), ops=[Lt()], comparators=[Num(n=10)])"

def test_mask_operator_2nd_dataframe():
    d = DataFrame()
    ref = d.x < d.y
    assert isinstance (ref, Column)
    assert ref.type == type(bool)
    assert ref.parent != d
    assert ast.dump(ref.child_expr) == "Compare(left=Name(id='p', ctx=Load()), ops=[Lt()], comparators=[ast_DataFrame()])"

def test_mask_operator_const_le():
    d = DataFrame()
    ref = d.x <= 10
    assert ast.dump(ref.child_expr) == "Compare(left=Name(id='p', ctx=Load()), ops=[LtE()], comparators=[Num(n=10)])"

def test_mask_operator_const_gt():
    d = DataFrame()
    ref = d.x > 10
    assert ast.dump(ref.child_expr) == "Compare(left=Name(id='p', ctx=Load()), ops=[Gt()], comparators=[Num(n=10)])"

def test_mask_operator_const_ge():
    d = DataFrame()
    ref = d.x >= 10
    assert ast.dump(ref.child_expr) == "Compare(left=Name(id='p', ctx=Load()), ops=[GtE()], comparators=[Num(n=10)])"

def test_mask_operator_const_eq():
    d = DataFrame()
    ref = d.x == 10
    assert ast.dump(ref.child_expr) == "Compare(left=Name(id='p', ctx=Load()), ops=[Eq()], comparators=[Num(n=10)])"

def test_mask_operator_const_ne():
    d = DataFrame()
    ref = d.x != 10
    assert ast.dump(ref.child_expr) == "Compare(left=Name(id='p', ctx=Load()), ops=[NotEq()], comparators=[Num(n=10)])"

def test_mask_operator_and():
    d = DataFrame()
    ref1 = d.x != 10
    ref2 = d.x != 8
    ref3 = ref1 & ref2
    assert ast.dump(ref3.child_expr) == "BinOp(left=Name(id='p', ctx=Load()), op=BitAnd(), right=ast_Column())"

def test_mask_operator_or():
    d = DataFrame()
    ref1 = d.x != 10
    ref2 = d.x != 8
    ref3 = ref1 | ref2
    assert ast.dump(ref3.child_expr) == "BinOp(left=Name(id='p', ctx=Load()), op=BitOr(), right=ast_Column())"

def test_masking_df():
    d = DataFrame()
    d1 = d[d.x > 10]
    assert isinstance(d1, DataFrame)
    assert d1.child_expr == None
    assert isinstance(d1.filter, Column)
    assert ast.dump(d1.filter.child_expr) == "Compare(left=Name(id='p', ctx=Load()), ops=[Gt()], comparators=[Num(n=10)])"