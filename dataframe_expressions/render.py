# Methods to render the DataFrame chain as a set of expressions.
import ast
from typing import Optional, Tuple, Dict

from .DataFrame import Column, DataFrame, ast_DataFrame


class _parent_subs(ast.NodeTransformer):
    def __init__(self, parent: ast.AST):
        self._parent = parent

    def visit_Name(self, a: ast.Name):
        'If this name is p, then we need to replace with parent'
        if a.id == 'p':
            return self._parent
        else:
            return a


def _render_filter(f: Column, seen_datasources: Optional[Dict[DataFrame, ast_DataFrame]] = None) -> ast.AST:
    'Render a filter as a result'

    # Get the info from the parent.
    if isinstance(f.parent, Column):
        raise Exception("yeah, not yet... fork!")
    else:
        expr, filter = render(f.parent, seen_datasources)
        child_filter = _parent_subs(expr).visit(f.child_expr)
        return child_filter if filter is None else \
            ast.BoolOp(op=ast.And(), values=[filter, child_filter])


def render(d: DataFrame, seen_datasources: Optional[Dict[DataFrame, ast_DataFrame]] = None) \
        -> Tuple[ast.AST, Optional[ast.AST]]:
    '''
    Follows the data frame back to the start and renders it in a complete AST.

    Arguments:
        d           DataFrame rendered from the start

    Returns:
        expr        A python ast.AST that contains the complete expression for whatever this
                    dDataFrame is meant to represent.
        filter      A filter to be applied to remove anything that is expected to be removed.
                    It will be set None if there is no filter applied

    Notes:
        In many cases, expressions are repeated. For example, `df[(df.x > 10) & (df.y > 10)]`,
        implies iterating over df. The `ast.AST` that represents `df` will be the same object
        in this case. That means the object hash will be the same. This can be used as a
        poor-person's way of doing common sub-expression elminiation.
    '''
    datasources = {} if seen_datasources is None else seen_datasources

    # If we are at the top of the chain, then our return is easy.
    if d.parent is None:
        if d not in datasources:
            datasources[d] = ast_DataFrame(d)
        return datasources[d], None

    # get the parent info
    p_expr, p_filter = render(d.parent, datasources)

    # now we need to tack on our info.
    expr = p_expr if d.child_expr is None \
        else _parent_subs(p_expr).visit(d.child_expr)  # type: ast.AST
    filter = p_filter if d.filter is None else _render_filter(d.filter, datasources)

    return expr, filter
