import ast
from typing import Optional

import pytest

from dataframe_expressions import (
    DataFrame, ast_Callable, ast_DataFrame, ast_Filter, render, render_context,
    render_callable)


def test_render_easy():
    d = DataFrame()
    expr, _ = render(d)
    assert isinstance(expr, ast_DataFrame)
    assert expr.dataframe is d


def test_render_single_collection():
    d = DataFrame()
    d1 = d.jets
    expr, _ = render(d1)
    assert isinstance(expr, ast.Attribute)
    assert expr.attr == 'jets'
    ast_df = expr.value  # type: ast.AST
    assert isinstance(ast_df, ast_DataFrame)
    assert ast_df.dataframe is d


def test_render_base_call():
    d = DataFrame()
    d1 = d.count()
    expr, _ = render(d1)
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
    expr, _ = render(d1)
    assert isinstance(expr, ast.Call)
    assert len(expr.args) == 1
    arg1 = expr.args[0]
    assert isinstance(arg1, ast.Num)
    assert arg1.n == 10


def test_render_func_with_df_arg():
    d = DataFrame()
    d1 = d.count(d)
    expr, _ = render(d1)
    assert isinstance(expr, ast.Call)
    assert len(expr.args) == 1
    arg1 = expr.args[0]  # type: ast.AST
    assert isinstance(arg1, ast_DataFrame)
    assert arg1.dataframe is d


def test_render_compare():
    d = DataFrame()
    d1 = d.jet.pt > 500
    expr, _ = render(d1)
    assert isinstance(expr, ast.Compare)


def test_render_func_with_dfattr_arg():
    d = DataFrame()
    d1 = d.jets.count(d.jets)
    expr, _ = render(d1)
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
    expr, _ = render(d1)

    assert isinstance(expr, ast_Filter)
    l_value = check_col_comp(expr.filter)
    assert l_value.dataframe is d

    assert isinstance(expr.expr, ast_DataFrame)
    assert expr.expr.dataframe is d
    # This line assures that the sub-expressions are the same, allowing
    # render code to take advantage of this.str()
    assert expr.expr is l_value


def test_simple_slice():
    d = DataFrame()
    d1 = d[0]
    expr, _ = render(d1)

    assert isinstance(expr, ast.Subscript)
    assert isinstance(expr.value, ast_DataFrame)


def test_simple_filter_func():
    def test(j):
        return j.x > 0

    d = DataFrame()
    d1 = d[test]
    expr, _ = render(d1)
    assert isinstance(expr, ast_Filter)
    l_value = check_col_comp(expr.filter)
    assert l_value.dataframe is d

    assert isinstance(expr.expr, ast_DataFrame)
    assert expr.expr.dataframe is d
    assert expr.expr is l_value


def test_simple_filter_lambda():
    d = DataFrame()
    d1 = d[lambda j: j.x > 0]
    expr, _ = render(d1)
    assert isinstance(expr, ast_Filter)
    l_value = check_col_comp(expr.filter)
    assert l_value.dataframe is d

    assert isinstance(expr.expr, ast_DataFrame)
    assert expr.expr.dataframe is d
    assert expr.expr is l_value


def test_filter_chaining():
    d = DataFrame()
    d1 = d[d.x > 0]
    d2 = d1[d1.y > 0]
    expr, _ = render(d2)

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
    expr, _ = render(d1)

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


def test_filter_with_attribute():
    d = DataFrame()
    d1 = d.jets[d.jets.pt > 30].pt
    expr, _ = render(d1)

    assert isinstance(expr, ast.Attribute)
    assert isinstance(expr.value, ast_Filter)


def test_subexpr_filter_same():
    d = DataFrame()
    d1 = d[d.x > 0]
    d2 = d1[(d1.y > 0) & (d1.y < 10)]
    expr, _ = render(d2)

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
    expr, _ = render(d1)

    assert isinstance(expr, ast_Filter)
    assert isinstance(expr.filter, ast.Compare)
    ref_in_filter = expr.filter.left
    ref_in_root = expr.expr
    assert ref_in_filter is ref_in_root


def test_callable_reference():
    d = DataFrame()
    d1 = d.jets.apply(lambda b: b)
    expr, _ = render(d1)

    assert isinstance(expr, ast.Call)
    assert len(expr.args) == 1
    arg1 = expr.args[0]  # type: ast.AST
    assert isinstance(arg1, ast_Callable)


def test_callable_simple_call():
    d = DataFrame()
    d1 = d.apply(lambda b: b)
    expr, ctx = render(d1)

    assert isinstance(expr, ast.Call)
    arg1 = expr.args[0]  # type: ast.AST
    assert isinstance(arg1, ast_Callable)

    expr1, new_ctx = render_callable(arg1, ctx, d)
    assert isinstance(expr1, ast_DataFrame)
    assert expr1.dataframe is d


def test_callable_context_no_update():
    d = DataFrame()
    d1 = d.apply(lambda b: b.jets.pt)
    expr, ctx = render(d1)

    assert isinstance(expr, ast.Call)
    arg1 = expr.args[0]  # type: ast.AST
    assert isinstance(arg1, ast_Callable)

    seen_ds = len(ctx._seen_datasources)
    resolved = len(ctx._resolved)

    expr1, new_ctx = render_callable(arg1, ctx, d)

    assert len(new_ctx._seen_datasources) != len(ctx._seen_datasources) \
        or len(new_ctx._resolved) != len(ctx._resolved)

    assert seen_ds == len(ctx._seen_datasources) \
        or resolved == len(ctx._resolved)


def test_callable_wrong_number_args():
    d = DataFrame()
    d1 = d.apply(lambda b: b)
    expr, ctx = render(d1)

    assert isinstance(expr, ast.Call)
    arg1 = expr.args[0]  # type: ast.AST
    assert isinstance(arg1, ast_Callable)

    with pytest.raises(Exception):
        render_callable(arg1, ctx, d, d)


def test_callable_function():
    def test_func(b):
        return b

    d = DataFrame()
    d1 = d.apply(test_func)
    expr, ctx = render(d1)

    assert isinstance(expr, ast.Call)
    arg1 = expr.args[0]  # type: ast.AST
    assert isinstance(arg1, ast_Callable)

    expr1, new_ctx = render_callable(arg1, ctx, d)
    assert isinstance(expr1, ast_DataFrame)
    assert expr1.dataframe is d


def test_callable_returns_const():
    d = DataFrame()
    d1 = d.apply(lambda b: 20)
    expr, ctx = render(d1)

    assert isinstance(expr, ast.Call)
    arg1 = expr.args[0]  # type: ast.AST
    assert isinstance(arg1, ast_Callable)

    expr1, new_ctx = render_callable(arg1, ctx, d)
    assert isinstance(expr1, ast.Num)
    assert expr1.n == 20


def test_callable_returns_matched_ast():
    d = DataFrame()
    d1 = d.jets.apply(lambda b: b)
    expr, ctx = render(d1)

    assert isinstance(expr, ast.Call)
    assert isinstance(expr.func, ast.Attribute)
    root_of_call = expr.func.value
    assert isinstance(root_of_call, ast.Attribute)

    arg1 = expr.args[0]  # type: ast.AST
    assert isinstance(arg1, ast_Callable)
    expr1, new_ctx = render_callable(arg1, ctx, d.jets)

    assert root_of_call is expr1


def test_callable_context():
    d = DataFrame()
    d1 = d.jets.apply(lambda b: b)
    expr, ctx = render(d1)

    assert isinstance(expr, ast.Call)
    arg1 = expr.args[0]  # type: ast.AST
    assert isinstance(arg1, ast_Callable)

    expr1, _ = render_callable(arg1, ctx, arg1.dataframe)

    assert isinstance(expr.func, ast.Attribute)
    root_of_call = expr.func.value
    assert isinstance(root_of_call, ast.Attribute)

    assert root_of_call is expr1


def test_callable_captures_dataframe():
    d = DataFrame()
    d1 = d.jets.apply(lambda b: d.jets)
    expr, ctx = render(d1)

    assert isinstance(expr, ast.Call)
    assert isinstance(expr.func, ast.Attribute)
    root_of_call = expr.func.value
    assert isinstance(root_of_call, ast.Attribute)

    arg1 = expr.args[0]  # type: ast.AST
    assert isinstance(arg1, ast_Callable)
    expr1, _ = render_callable(arg1, ctx, d.jets)

    assert root_of_call is expr1


def test_callable_captures_column():
    d = DataFrame()
    d1 = d.jets.apply(lambda b: d.met > 20.0)
    expr, ctx = render(d1)

    assert isinstance(expr, ast.Call)
    assert isinstance(expr.func, ast.Attribute)
    root_of_call = expr.func.value
    assert isinstance(root_of_call, ast.Attribute)

    arg1 = expr.args[0]  # type: ast.AST
    assert isinstance(arg1, ast_Callable)
    expr1, _ = render_callable(arg1, ctx, d.jets)

    assert isinstance(expr1, ast.Compare)


def test_render_callable_captured():
    d = DataFrame()
    jets = d.jets
    mcs = d.mcs
    near_a_jet = mcs[mcs.map(lambda mc: jets.pt.Count() == 2)]

    expr1, ctx = render(near_a_jet)
    assert expr1 is not None
    assert isinstance(expr1, ast_Filter)


def test_render_twice():
    d = DataFrame()
    jets = d.jets.pt

    expr1, ctx1 = render(jets)
    expr2, ctx2 = render(jets)

    assert ast.dump(expr1) == ast.dump(expr2)


def test_render_twice_with_filter():
    d = DataFrame()
    jets = d.jets[d.jets.pt > 10].pt

    expr1, ctx1 = render(jets)
    expr2, ctx2 = render(jets)

    assert ast.dump(expr1) == ast.dump(expr2)


def test_render_context_clone_df():
    r1 = render_context()
    r1._seen_datasources[1] = ast_DataFrame(DataFrame())

    r2 = render_context(r1)
    assert 1 in r2._seen_datasources
    assert r2._seen_datasources[1] is r1._seen_datasources[1]

    del r1._seen_datasources[1]
    assert 1 in r2._seen_datasources


def test_render_context_clone_resolved():
    r1 = render_context()
    r1._resolved[1] = ast_DataFrame(DataFrame())

    r2 = render_context(r1)
    assert 1 in r2._resolved
    assert r2._resolved[1] is r1._resolved[1]

    del r1._resolved[1]
    assert 1 in r2._resolved


def test_render_twice_for_same_results():

    df = DataFrame()
    eles = df.Electrons()
    mc_part = df.TruthParticles()
    mc_ele = mc_part[mc_part.pdgId == 11]
    good_mc_ele = mc_ele[mc_ele.ptgev > 20]

    ele_mcs = eles.map(lambda reco_e: good_mc_ele)

    expr1, context1 = render(ele_mcs)
    expr2, context2 = render(ele_mcs)

    assert ast.dump(expr1) == ast.dump(expr2)
    assert len(context1._resolved) == len(context2._resolved)
    assert len(context1._seen_datasources) == len(context2._seen_datasources)


def test_render_callable_twice_for_same_results():

    df = DataFrame()
    eles = df.Electrons()
    mc_part = df.TruthParticles()
    mc_ele = mc_part[mc_part.pdgId == 11]
    good_mc_ele = mc_ele[mc_ele.ptgev > 20]

    ele_mcs = eles.map(lambda reco_e: good_mc_ele)

    expr, context = render(ele_mcs)

    class find_callable(ast.NodeVisitor):
        @classmethod
        def findit(cls, a: ast.AST) -> Optional[ast_Callable]:
            f = find_callable()
            f.visit(a)
            return f._callable

        def __init__(self):
            ast.NodeVisitor.__init__(self)
            self._callable: Optional[ast_Callable] = None

        def visit_ast_Callable(self, a: ast_Callable):
            self._callable = a

    callable = find_callable.findit(expr)
    assert callable is not None

    c_expr1, c_context1 = render_callable(callable, context, callable.dataframe)
    c_expr2, c_context2 = render_callable(callable, context, callable.dataframe)

    assert ast.dump(c_expr1) == ast.dump(c_expr2)
    assert len(c_context1._seen_datasources) == len(c_context2._seen_datasources)
    assert len(c_context1._resolved) == len(c_context2._resolved)

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
