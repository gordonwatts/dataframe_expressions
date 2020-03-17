# Test the render method
import ast
from typing import Optional

from dataframe_expressions import DataFrame, ast_DataFrame, render


def test_render_easy():
    d = DataFrame()
    expr, filter = render(d)
    assert filter is None
    assert isinstance(expr, ast_DataFrame)
    assert expr.dataframe is d


def test_render_single_collection():
    d = DataFrame()
    d1 = d.jets
    expr, filter = render(d1)
    assert filter is None
    assert isinstance(expr, ast.Attribute)
    assert expr.attr == 'jets'
    ast_df = expr.value  # type: ast.AST
    assert isinstance(ast_df, ast_DataFrame)
    assert ast_df.dataframe is d


def test_render_base_call():
    d = DataFrame()
    d1 = d.count()
    expr, filter = render(d1)
    assert filter is None
    assert isinstance(expr, ast.Call)
    assert len(expr.args) == 0
    e_func = expr.func
    assert isinstance(e_func, ast.Attribute)
    e_val = e_func.value  # type: ast.AST
    assert isinstance(e_val, ast_DataFrame)
    assert e_val.dataframe is d


def check_col_comp(a: Optional[ast.AST]) -> ast_DataFrame:
    '''Check for a simple column that is a comparison, with df.x on one side'''
    assert a is not None
    assert isinstance(a, ast.Compare)
    l_operand = a.left
    assert isinstance(l_operand, ast.Attribute)
    l_value = l_operand.value  # type: ast.AST
    assert isinstance(l_value, ast_DataFrame)
    return l_value


def test_simple_filter():
    d = DataFrame()
    d1 = d[d.x > 0]
    expr, filter = render(d1)

    l_value = check_col_comp(filter)
    assert l_value.dataframe is d

    assert isinstance(expr, ast_DataFrame)
    assert expr.dataframe is d
    # This line assures that the sub-expressions are the same, allowing
    # render code to take advantage of this.str()
    assert expr is l_value


def test_filter_chaining():
    d = DataFrame()
    d1 = d[d.x > 0]
    d2 = d1[d1.y > 0]
    expr, filter = render(d2)

    assert isinstance(expr, ast_DataFrame)
    assert expr.dataframe is d

    assert isinstance(filter, ast.BoolOp)
    assert isinstance(filter.op, ast.And)
    assert len(filter.values) == 2
    left = filter.values[0]
    right = filter.values[1]
    assert isinstance(left, ast.Compare)
    assert isinstance(right, ast.Compare)
    pass


def check_and_compare(a: ast.AST):
    assert isinstance(a, ast.BoolOp)
    assert isinstance(a.op, ast.And)
    _ = check_col_comp(a.values[0])
    _ = check_col_comp(a.values[1])


def test_filter_chained_and():
    d = DataFrame()
    d1 = d[d.x > 0]
    d2 = d1[(d1.y > 0) & (d1.y < 10)]
    expr, filter = render(d2)

    assert isinstance(expr, ast_DataFrame)
    assert expr.dataframe is d

    assert isinstance(filter, ast.BoolOp)
    assert isinstance(filter.op, ast.And)
    assert len(filter.values) == 2
    left = filter.values[0]
    right = filter.values[1]
    assert isinstance(left, ast.Compare)
    assert isinstance(right, ast.BoolOp)

    check_col_comp(left)
    check_and_compare(right)


def test_subexpr_filter_same():
    d = DataFrame()
    d1 = d[d.x > 0]
    d2 = d1[(d1.y > 0) & (d1.y < 10)]
    expr, filter = render(d2)

    # The ast that refers to d[d.x>0] should be the same.
    class df_finder(ast.NodeVisitor):
        def __init__(self):
            self.found_frames = []

        def visit_ast_DataFrame(self, a: ast_DataFrame):
            self.found_frames.append(a.dataframe)

    assert filter is not None
    scanner = df_finder()
    scanner.visit(filter)

    assert len(scanner.found_frames) == scanner.found_frames.count(scanner.found_frames[0])
