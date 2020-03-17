# Methods to render the DataFrame chain as a set of expressions.
from ast import AST, Name, NodeTransformer
from typing import Optional, Tuple

from .DataFrame import DataFrame, ast_DataFrame


class _parent_subs(NodeTransformer):
    def __init__(self, parent: AST):
        self._parent = parent

    def visit_Name(self, a: Name):
        'If this name is p, then we need to replace with parent'
        if a.id == 'p':
            return self._parent
        else:
            return a


def render(d: DataFrame) -> Tuple[AST, Optional[AST]]:
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
    # If we are at the top of the chain, then our return is easy.
    if d.parent is None:
        return ast_DataFrame(d), None

    # get the parent info
    p_expr, p_filter = render(d.parent)

    # now we need to tack on our info.
    expr = p_expr if d.child_expr is None \
        else _parent_subs(p_expr).visit(d.child_expr)  # type: AST
    filter = p_filter if d.filter is None \
        else _parent_subs(p_expr).visit(d.filter)

    return expr, filter
