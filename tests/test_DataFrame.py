import ast

from dataframe_expressions.DataFrame import DataFrame, Column

# TODO:
#  the operator "in" (contains)? to see if one jet is in aother collection?
#  the operator len
#  How do we do "and" and "or" between masks (see below for operators)?
#  Basic math operators (https://docs.python.org/3/reference/datamodel.html?highlight=__add__#emulating-numeric-types)
#  Operations between columns and dataframes
#  Operations between columns and columns
#  Fluent function calls
#  Filtering
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

def test_mask_operator_const_lt():
    d = DataFrame()
    ref = d.x < 10
    assert isinstance (ref, Column)
    assert ref.type == type(bool)
    assert ref.parent != d
    assert ast.dump(ref.child_expr) == "Compare(left=Name(id='p', ctx=Load()), ops=[Lt()], comparators=[Num(n=10)])"

def test_mask_operator_2nd_col():
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
