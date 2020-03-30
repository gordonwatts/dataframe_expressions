# Test the render method
import ast
from typing import Optional

from dataframe_expressions import DataFrame, ast_DataFrame, ast_Filter, render


def test_render_easy():
    d = DataFrame()
    expr = render(d)
    assert isinstance(expr, ast_DataFrame)
    assert expr.dataframe is d


def test_render_single_collection():
    d = DataFrame()
    d1 = d.jets
    expr = render(d1)
    assert isinstance(expr, ast.Attribute)
    assert expr.attr == 'jets'
    ast_df = expr.value  # type: ast.AST
    assert isinstance(ast_df, ast_DataFrame)
    assert ast_df.dataframe is d


def test_render_base_call():
    d = DataFrame()
    d1 = d.count()
    expr = render(d1)
    assert isinstance(expr, ast.Call)
    assert len(expr.args) == 0
    e_func = expr.func
    assert isinstance(e_func, ast.Attribute)
    e_val = e_func.value  # type: ast.AST
    assert isinstance(e_val, ast_DataFrame)
    assert e_val.dataframe is d


def test_render_func_with_args():
    d = DataFrame()
    d1 = d.count(10)
    expr = render(d1)
    assert isinstance(expr, ast.Call)
    assert len(expr.args) == 1
    arg1 = expr.args[0]
    assert isinstance(arg1, ast.Num)
    assert arg1.n == 10


def test_render_func_with_df_arg():
    d = DataFrame()
    d1 = d.count(d)
    expr = render(d1)
    assert isinstance(expr, ast.Call)
    assert len(expr.args) == 1
    arg1 = expr.args[0]  # type: ast.AST
    assert isinstance(arg1, ast_DataFrame)
    assert arg1.dataframe is d


def test_render_func_with_dfattr_arg():
    d = DataFrame()
    d1 = d.jets.count(d.jets)
    expr = render(d1)
    assert isinstance(expr, ast.Call)
    assert len(expr.args) == 1
    arg1 = expr.args[0]  # type: ast.AST
    assert isinstance(arg1, ast.Attribute)
    assert isinstance(expr.func, ast.Attribute)
    root_of_call = expr.func.value
    assert isinstance(root_of_call, ast.Attribute)
    assert arg1 is root_of_call


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
    expr = render(d1)

    assert isinstance(expr, ast_Filter)
    l_value = check_col_comp(expr.filter)
    assert l_value.dataframe is d

    assert isinstance(expr.expr, ast_DataFrame)
    assert expr.expr.dataframe is d
    # This line assures that the sub-expressions are the same, allowing
    # render code to take advantage of this.str()
    assert expr.expr is l_value


def test_filter_chaining():
    d = DataFrame()
    d1 = d[d.x > 0]
    d2 = d1[d1.y > 0]
    expr = render(d2)

    assert isinstance(expr, ast_Filter)
    assert isinstance(expr.expr, ast_Filter)
    assert isinstance(expr.expr.expr, ast_DataFrame)
    assert expr.expr.expr.dataframe is d

    assert isinstance(expr.filter, ast.Compare)
    assert isinstance(expr.expr.filter, ast.Compare)

    # Make sure the ast object is re-used here. This
    # will be key for the API when trying to render this.
    left_op = expr.filter.left
    assert isinstance(left_op, ast.Attribute)
    assert left_op.value is expr.expr


def test_filter_and():
    d = DataFrame()
    d1 = d[(d.y > 0) & (d.y < 10)]
    expr = render(d1)

    assert isinstance(expr, ast_Filter)
    assert isinstance(expr.expr, ast_DataFrame)
    assert expr.expr.dataframe is d

    assert isinstance(expr.filter, ast.BoolOp)
    assert isinstance(expr.filter.op, ast.And)
    assert len(expr.filter.values) == 2
    left = expr.filter.values[0]
    right = expr.filter.values[1]
    assert isinstance(left, ast.Compare)
    assert isinstance(right, ast.Compare)

    check_col_comp(left)
    check_col_comp(right)


def test_subexpr_filter_same():
    d = DataFrame()
    d1 = d[d.x > 0]
    d2 = d1[(d1.y > 0) & (d1.y < 10)]
    expr = render(d2)

    # The ast that refers to d[d.x>0] should be the same.
    class df_finder(ast.NodeVisitor):
        def __init__(self):
            self.found_frames = []

        def visit_ast_DataFrame(self, a: ast_DataFrame):
            self.found_frames.append(a.dataframe)

    scanner = df_finder()
    scanner.visit(expr)

    assert len(scanner.found_frames) == scanner.found_frames.count(scanner.found_frames[0])


def test_multilevel_subexpr():
    d = DataFrame()
    d1 = d.jets.pt[d.jets.pt > 30.0]
    expr = render(d1)

    assert isinstance(expr, ast_Filter)
    assert isinstance(expr.filter, ast.Compare)
    ref_in_filter = expr.filter.left
    ref_in_root = expr.expr
    assert ref_in_filter is ref_in_root


# def test_subexpr_2filter_same():
# TODO: See the line in the readme - it isn't clear what this means - to take the count of a column.
#       The semantics are clear, but it is also obvious this is a, from a code point of view, a different
#       way of thinking about things. So we need to be careful here to make sure that we aren't accidentally
#       adding some new meaning that will get confusing. So think this through before deciding this test
#       makes sense!
#     d = DataFrame()
#     d1 = d[d.x > 0].jets
#     d2 = d1[(d[d.x > 0].jets.pt > 20).count()].pt
#     expr = render(d2)

#     # d[d.x > 0].jets are the same, and should refer to the same ast.
#     class find_attr(ast.NodeVisitor):
#         def __init__(self):
#             self.found = []

#         def visit_Attribute(self, a: ast.Attribute):
#             if a.attr == 'jets':
#                 self.found.append(a)

#     finder = find_attr()
#     finder.visit(expr)
#     assert len(finder.found) == 2
