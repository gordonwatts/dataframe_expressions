# Test the render method
import ast

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


def test_simple_filter():
    d = DataFrame()
    d1 = d[d.x > 0]
    expr, filter = render(d1)

    assert filter is not None
    assert isinstance(filter, ast.Compare)
    l_operand = filter.left
    assert isinstance(l_operand, ast.Attribute)
    l_value = l_operand.value  # type: ast.AST
    assert isinstance(l_value, ast_DataFrame)
    assert l_value.dataframe is d

    assert isinstance(expr, ast_DataFrame)
    assert expr.dataframe is d
    # This line assures that the sub-expressions are the same, allowing
    # render code to take advantage of this.str()
    assert expr is l_value
