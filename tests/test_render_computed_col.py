import ast
from typing import Optional, Tuple

from dataframe_expressions import (
    DataFrame, ast_Callable, render, render_context,
    render_callable)


def test_lambda_for_computed_col():
    df = DataFrame()
    df.jets['ptgev'] = lambda j: j.pt / 1000
    d1 = df.jets.ptgev

    expr_1, context_1 = render(d1)

    assert isinstance(expr_1, ast.Call)
    assert isinstance(expr_1.func, ast_Callable)
    assert len(expr_1.args) == 1
    a = expr_1.args[0]
    assert isinstance(a, ast.Attribute)

    expr_2, _ = render_callable(expr_1.func, context_1, expr_1.func.dataframe)
    assert isinstance(expr_2, ast.BinOp)
    assert isinstance(expr_2.left, ast.Attribute)
    assert expr_2.left.value is a


def test_nested_computed_col():
    # This is returning a recursive reference sometimes, for reasons not understood.
    df = DataFrame()

    mc_part = df.TruthParticles('TruthParticles')
    eles = df.Electrons('Electrons')

    # This gives us a list of events, and in each event, good electrons, and then for each good electron, all good MC electrons that are near by
    eles['near_mcs'] = lambda reco_e: mc_part
    eles['hasMC'] = lambda e: e.near_mcs.Count() > 0

    expr, context = render(eles[~eles.hasMC].pt)

    class find_callable(ast.NodeVisitor):
        def __init__(self):
            ast.NodeVisitor.__init__(self)
            self.callable: Optional[ast_Callable] = None

        def visit_ast_Callable(self, a: ast_Callable):
            assert self.callable is None
            self.callable = a

    def find_callable_and_render(expr: ast.AST, ctx: render_context) -> Tuple[ast.AST, render_context]:
        ff = find_callable()
        ff.visit(expr)
        assert ff.callable is not None
        return render_callable(ff.callable, context, ff.callable.dataframe)

    expr2, context_2 = find_callable_and_render(expr, context)

    expr3, _ = find_callable_and_render(expr2, context_2)

    assert ast.dump(expr2) != ast.dump(expr3)
