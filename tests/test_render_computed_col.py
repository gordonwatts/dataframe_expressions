import ast
from typing import Optional, Tuple

from dataframe_expressions import (
    DataFrame, ast_Callable, render, render_context,
    render_callable, user_func)


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
    return render_callable(ff.callable, ctx, ff.callable.dataframe)


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

    expr_2, _ = render_callable(expr_1.func, context_1, expr_1.func.dataframe)  # type: ignore
    assert isinstance(expr_2, ast.BinOp)
    assert isinstance(expr_2.left, ast.Attribute)
    assert expr_2.left.value is a


def test_different_callables_look_different():
    # This is returning a recursive reference sometimes, due to a bug (every ast_Callable
    # looked the same).
    df = DataFrame()

    mc_part = df.TruthParticles('TruthParticles')
    eles = df.Electrons('Electrons')

    # This gives us a list of events, and in each event, good electrons, and then for each good electron, all good MC electrons that are near by
    eles['near_mcs'] = lambda reco_e: mc_part
    eles['hasMC'] = lambda e: e.near_mcs.Count() > 0

    expr, context = render(eles[~eles.hasMC].pt)

    expr2, context_2 = find_callable_and_render(expr, context)

    expr3, _ = find_callable_and_render(expr2, context_2)

    assert ast.dump(expr2) != ast.dump(expr3)


def test_second_dr_returns_filtered():
    df = DataFrame()

    @user_func
    def DeltaR(p1_eta: float) -> float:
        '''
        Calculate the DeltaR between two particles given their `eta` and `phi` locations.
        Implemented on the back end.
        '''
        assert False, 'This should never be called'

    mc_part = df.TruthParticles('TruthParticles')
    eles = df.Electrons('Electrons')

    def dr(e, mc):
        'Make calculating DR easier as I have a hard-to-use DR calculation function on the back end'
        return DeltaR(e.eta())

    def very_near2(mcs, e):
        'Return all particles in mcs that are DR less than 0.5'
        return mcs[lambda m: dr(e, m) < 0.1]

    eles['near_mcs'] = lambda reco_e: very_near2(mc_part, reco_e)

    eles['hasMC'] = lambda e: e.near_mcs.Count() > 0
    good_eles_with_mc = eles[eles.hasMC]
    good_eles_with_mc['mc'] = lambda e: e.near_mcs.First().ptgev

    d1 = good_eles_with_mc.mc

    expr_1, context_1 = render(d1)

    class render_in_depth(ast.NodeTransformer):
        def __init__(self, context):
            ast.NodeTransformer.__init__(self)
            self._context = context

        def visit_Call(self, a: ast.Call):
            if not isinstance(a.func, ast_Callable):
                return self.generic_visit(a)

            assert len(a.args) == 1
            # arg = self.visit(a.args[0])

            expr, new_context = render_callable(a.func, self._context, a.func.dataframe)  # type: ignore
            old_context = self._context
            try:
                self._context = new_context
                return self.visit(expr)
            finally:
                self._context = old_context

    assert isinstance(expr_1, ast.Call)

    rendered = render_in_depth(context_1).visit(expr_1)
    assert rendered is not None
