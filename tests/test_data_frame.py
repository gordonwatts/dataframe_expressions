import ast
from typing import Optional, List, cast

from dataframe_expressions import Column, DataFrame, ast_DataFrame, define_alias
from dataframe_expressions import ast_Callable, ast_Column

from .utils_for_testing import reset_var_counter  # NOQA

#  numpy math functions (??)
#  Advanced math operators
#  (https://docs.python.org/3/reference/datamodel.html?highlight=__add__#emulating-numeric-types)
#  the operator "in" (contains)? to see if one jet is in another collection?
#  the operator len
#  Make sure if d1 and d2 are two different sized,sourced DataFrames, then d1[d2.x] fails
#  Filter functions - so pass a filter that gets called with whatever you are filtering on, and
#   returns.
#                   https://stackoverflow.com/questions/847936/how-can-i-find-the-number-of-arguments-of-a-python-function
#  Aliases allow some recursion, but with total flexability. If there is a circle and you want
#       things done a second time, they
#          won't be. Perhaps when we have an actual problem we can resolve this.


def find_df(a: Optional[ast.AST]) -> List[ast_DataFrame]:
    result: List[ast_DataFrame] = []

    class find_it(ast.NodeVisitor):
        def visit_ast_DataFrame(self, a: ast_DataFrame):
            result.append(a)

    if a is None:
        return []

    find_it().visit(a)
    return result


def test_empty_ctor():
    DataFrame()


def test_dataframe_attribute():
    d = DataFrame()
    ref = d.x
    assert isinstance(ref, DataFrame)
    assert isinstance(ref.child_expr, ast.AST)
    assert ast.dump(ref.child_expr) == "Attribute(value=ast_DataFrame(), attr='x', ctx=Load())"


def test_mask_operator_const_lt_const():
    d = DataFrame()
    ref = d.x < 10
    assert isinstance(ref, Column)
    assert ref.type == type(bool)
    assert ast.dump(ref.child_expr) == \
        "Compare(left=ast_DataFrame(), ops=[Lt()], comparators=[Num(n=10)])"
    assert isinstance(ref.child_expr, ast.Compare)
    df = ref.child_expr.left  # type: ast.AST
    assert isinstance(df, ast_DataFrame)
    parents = find_df(df.dataframe.child_expr)
    assert len(parents) == 1

    assert parents[0].dataframe is d


def test_mask_operator_2nd_dataframe():
    d = DataFrame()
    ref = d.x < d.y
    assert isinstance(ref, Column)
    assert ref.type == type(bool)
    assert ast.dump(ref.child_expr) == \
        "Compare(left=ast_DataFrame(), ops=[Lt()], comparators=[ast_DataFrame()])"
    assert isinstance(ref.child_expr, ast.Compare)
    df = ref.child_expr.left  # type: ast.AST
    assert isinstance(df, ast_DataFrame)
    parents = find_df(df.dataframe.child_expr)
    assert len(parents) == 1
    assert parents[0].dataframe is d


def test_mask_operator_const_le():
    d = DataFrame()
    ref = d.x <= 10
    assert ast.dump(ref.child_expr) == \
        "Compare(left=ast_DataFrame(), ops=[LtE()], comparators=[Num(n=10)])"


def test_mask_operator_const_gt():
    d = DataFrame()
    ref = d.x > 10
    assert ast.dump(ref.child_expr) == \
        "Compare(left=ast_DataFrame(), ops=[Gt()], comparators=[Num(n=10)])"


def test_mask_operator_const_ge():
    d = DataFrame()
    ref = d.x >= 10
    assert ast.dump(ref.child_expr) == \
        "Compare(left=ast_DataFrame(), ops=[GtE()], comparators=[Num(n=10)])"


def test_mask_operator_const_eq():
    d = DataFrame()
    ref = d.x == 10
    assert ast.dump(ref.child_expr) == \
        "Compare(left=ast_DataFrame(), ops=[Eq()], comparators=[Num(n=10)])"


def test_mask_operator_const_ne():
    d = DataFrame()
    ref = d.x != 10
    assert ast.dump(ref.child_expr) == \
        "Compare(left=ast_DataFrame(), ops=[NotEq()], comparators=[Num(n=10)])"


def test_mask_operator_and():
    d = DataFrame()
    ref1 = d.x != 10
    ref2 = d.x != 8
    ref3 = ref1 & ref2
    assert ast.dump(ref3.child_expr) == \
        "BoolOp(op=And(), values=[ast_Column(), ast_Column()])"


def test_mask_operator_and_attributes():
    d = DataFrame()
    ref1 = d.x
    ref2 = d.x
    ref3 = ref1 & ref2
    assert ast.dump(ref3.child_expr) == \
        "BoolOp(op=And(), values=[ast_DataFrame(), ast_DataFrame()])"


def test_mask_operator_or_attributes():
    d = DataFrame()
    ref1 = d.x
    ref2 = d.x
    ref3 = ref1 | ref2
    assert ast.dump(ref3.child_expr) == \
        "BoolOp(op=Or(), values=[Name(id='p', ctx=Load()), ast_DataFrame()])"


def test_mask_operator_and_attribute():
    d = DataFrame()
    ref1 = d.x
    ref2 = d.x > 10
    ref3 = ref1 & ref2
    assert ast.dump(ref3.child_expr) == \
        "BoolOp(op=And(), values=[ast_DataFrame(), ast_Column()])"


def test_mask_operator_invert_attributes():
    d = DataFrame()
    ref1 = d.x
    ref3 = ~ref1
    assert ref3.child_expr is not None
    assert ast.dump(ref3.child_expr) == \
        "UnaryOp(op=Invert(), operand=ast_DataFrame())"


def test_mask_operator_or():
    d = DataFrame()
    ref1 = d.x != 10
    ref2 = d.x != 8
    ref3 = ref1 | ref2
    assert ast.dump(ref3.child_expr) == \
        "BoolOp(op=Or(), values=[ast_Column(), ast_Column()])"


def test_mask_operator_not():
    d = DataFrame()
    ref1 = d.x != 10
    ref3 = ~ref1
    assert ast.dump(ref3.child_expr) == \
        "UnaryOp(op=Invert(), operand=ast_Column())"


def test_invert_dataframe():
    d = DataFrame()
    ref1 = ~d
    assert ref1.child_expr is not None
    assert ast.dump(ref1.child_expr) == \
        "UnaryOp(op=Invert(), operand=ast_DataFrame())"
    assert ref1.filter is None


def test_masking_df():
    d = DataFrame()
    d1 = d[d.x > 10]
    assert isinstance(d1, DataFrame)
    assert isinstance(d1.filter, Column)
    assert ast.dump(d1.filter.child_expr) == \
        "Compare(left=ast_DataFrame(), ops=[Gt()], comparators=[Num(n=10)])"


def test_slicing_df():
    d = DataFrame()
    d1 = d[10]
    assert isinstance(d1, DataFrame)
    assert isinstance(d1.child_expr, ast.Subscript)
    assert isinstance(d1.child_expr.slice, ast.Index)
    assert isinstance(d1.child_expr.value, ast_DataFrame)
    assert d1.child_expr.slice.value == 10


def test_math_division():
    d = DataFrame()
    d1 = d.x/1000
    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "BinOp(left=ast_DataFrame(), op=Div(), right=Num(n=1000))"


def test_math_mult():
    d = DataFrame()
    d1 = d.x*1000
    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "BinOp(left=ast_DataFrame(), op=Mult(), right=Num(n=1000))"


def test_math_sub():
    d = DataFrame()
    d1 = d.x-1000
    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "BinOp(left=ast_DataFrame(), op=Sub(), right=Num(n=1000))"


def test_math_add():
    d = DataFrame()
    d1 = d.x+1000
    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "BinOp(left=ast_DataFrame(), op=Add(), right=Num(n=1000))"


def test_np_sin():
    import numpy as np
    d = DataFrame()
    d1 = cast(DataFrame, np.sin(d.x))  # type: ignore
    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "Call(func=Attribute(value=ast_DataFrame(), attr='sin', ctx=Load()), args=[], keywords=[])"


def test_python_abs():
    d = DataFrame()
    d1 = abs(d.x)
    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "Call(func=Attribute(value=ast_DataFrame(), attr='abs', ctx=Load()), args=[], keywords=[])"


def test_np_sin_kwargs():
    import numpy as np
    d = DataFrame()
    d1 = cast(DataFrame, np.sin(d.x, bogus=22.0))  # type: ignore
    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "Call(func=Attribute(value=ast_DataFrame(), attr='sin', ctx=Load()), args=[], "\
        "keywords=[keyword(arg='bogus', value=Num(n=22.0))])"


def test_np_arctan2_with_args():
    import numpy as np
    d = DataFrame()
    d1 = cast(DataFrame, np.arctan2(d.x, 100.0))  # type: ignore
    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "Call(func=Attribute(value=ast_DataFrame(), attr='arctan2', ctx=Load()), " \
        "args=[Num(n=100.0)], keywords=[])"


def test_fluent_function_no_args():
    d = DataFrame()
    d1 = d.count()
    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "Call(func=Attribute(value=ast_DataFrame(), attr='count', ctx=Load()), args=[], " \
        "keywords=[])"


def test_fluent_function_pos_arg():
    d = DataFrame()
    d1 = d.count(22.0)
    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "Call(func=Attribute(value=ast_DataFrame(), attr='count', ctx=Load()), " \
        "args=[Num(n=22.0)], keywords=[])"


def test_fluent_function_kwarg():
    d = DataFrame()
    d1 = d.count(dude=22.0)
    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "Call(func=Attribute(value=ast_DataFrame(), attr='count', ctx=Load()), args=[], " \
        "keywords=[keyword(arg='dude', value=Num(n=22.0))])"


def test_test_fluent_function_df_arg():
    d = DataFrame()
    d1 = d.count(d)

    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "Call(func=Attribute(value=ast_DataFrame(), attr='count', ctx=Load()), " \
        "args=[ast_DataFrame()], keywords=[])"


def test_test_fluent_function_dfattr_arg():
    d = DataFrame()
    d1 = d.count(d.jets)

    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "Call(func=Attribute(value=ast_DataFrame(), attr='count', ctx=Load()), " \
        "args=[ast_DataFrame()], keywords=[])"


def test_test_fluent_function_dfattrattr_arg():
    d = DataFrame()
    d1 = d.jets.count(d.jets)

    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "Call(func=Attribute(value=ast_DataFrame(), attr='count', ctx=Load()), " \
        "args=[ast_DataFrame()], keywords=[])"


def test_test_fluent_function_dfattr1_arg():
    d = DataFrame()
    d1 = d.jets.count(d)

    assert d1.filter is None
    assert d1.child_expr is not None
    assert ast.dump(d1.child_expr) == \
        "Call(func=Attribute(value=ast_DataFrame(), attr='count', ctx=Load()), " \
        "args=[ast_DataFrame()], keywords=[])"


def test_resolve_simple_alias():
    define_alias("jets", "pts", lambda j: j.pt / 1000.0)
    df = DataFrame()
    df1 = df.jets.pts
    assert df1.filter is None
    assert df1.child_expr is not None
    assert '1000' in ast.dump(df1.child_expr)


def test_resolve_hidden_alias():
    define_alias("jets", "pt", lambda j: j.pt / 1000.0)
    df = DataFrame()
    df1 = df.jets.pt
    assert df1.filter is None
    assert df1.child_expr is not None
    assert '1000' in ast.dump(df1.child_expr)


def test_resolve_dependent():
    define_alias("jets", "pts", lambda j: j.pt / 1000.0)
    define_alias("jets", "pt", lambda j: j.pt / 2000.0)

    df = DataFrame()
    df1 = df.jets.pts
    assert df1.filter is None
    assert df1.child_expr is not None
    assert '1000' in ast.dump(df1.child_expr)
    assert isinstance(df1.child_expr, ast.BinOp)
    assert df1.child_expr.left is not None
    assert isinstance(df1.child_expr.left, ast_DataFrame)
    df2 = cast(ast_DataFrame, df1.child_expr.left)
    assert df2.dataframe.child_expr is not None
    assert '2000' in ast.dump(df2.dataframe.child_expr)


def check_for_compare(e: ast.AST, check: str):
    assert isinstance(e, ast.Compare)
    left = e.left  # type: ast.AST
    assert isinstance(left, ast_DataFrame)
    assert left.dataframe.child_expr is not None
    t = ast.dump(left.dataframe.child_expr)
    assert check in t


def test_resolve_in_filter():
    define_alias("jets", "pt", lambda j: j.pt / 2000.0)

    df = DataFrame()
    df1 = df.jets.pt[df.jets.pt > 50.0]

    assert df1.filter is not None
    assert isinstance(df1.filter, Column)
    check_for_compare(df1.filter.child_expr, '2000')


def test_resolve_in_filter_twice():
    define_alias("jets", "pt", lambda j: j.pt / 2000.0)

    df = DataFrame()
    df1 = df.jets.pt[(df.jets.pt > 50.0) & (df.jets.pt < 60.0)]

    assert df1.filter is not None
    assert isinstance(df1.filter.child_expr, ast.BoolOp)
    bool_op = df1.filter.child_expr
    assert len(bool_op.values) == 2

    op_1 = bool_op.values[0]  # type: ast.AST
    op_2 = bool_op.values[1]  # type: ast.AST

    assert isinstance(op_1, ast_Column)
    assert isinstance(op_2, ast_Column)

    check_for_compare(op_1.column.child_expr, '2000')
    check_for_compare(op_1.column.child_expr, '2000')


def test_lambda_argument():
    df = DataFrame()
    df1 = df.apply(lambda e: e)

    assert df1.child_expr is not None
    assert isinstance(df1.child_expr, ast.Call)
    assert len(df1.child_expr.args) == 1
    arg1 = df1.child_expr.args[0]
    assert isinstance(arg1, ast_Callable)


def test_lambda_in_filter():
    df = DataFrame()
    df1 = df[df.apply(lambda e: e == 1)]

    assert isinstance(df1.child_expr, ast_DataFrame)
    assert df1.filter is not None
    assert isinstance(df1.filter, Column)
    assert isinstance(df1.filter.child_expr, ast.Call)


def test_shallow_copy():
    df = DataFrame()
    import copy
    df1 = copy.copy(df)

    assert df1 is not df
    assert df1.child_expr is None
    assert df1.filter is None


def test_shallow_copy_1():
    df = DataFrame()
    df1 = df.x
    import copy
    df2 = copy.copy(df1)

    assert df2 is not df1
    assert df2.child_expr is not None
    assert df2.filter is None


def test_deep_copy():
    df = DataFrame()
    import copy
    df1 = copy.deepcopy(df)

    assert df1 is not df
    assert df1.child_expr is None
    assert df1.filter is None


def test_deep_copy_1():
    df = DataFrame()
    df1 = df.x
    import copy
    df2 = copy.deepcopy(df1)

    assert df2 is not df1

    assert df2.child_expr is not None
    assert df2.filter is None

    assert isinstance(df2.child_expr, ast.Attribute)
    assert isinstance(df2.child_expr.value, ast_DataFrame)
    df2_parent = cast(ast_DataFrame, df2.child_expr.value)

    assert df2_parent is not df
