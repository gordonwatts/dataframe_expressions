# Methods to render the DataFrame chain as a set of expressions.
import ast
from typing import Dict, Optional, Union

from .DataFrame import Column, DataFrame, ast_Column, ast_DataFrame


class ast_Filter (ast.AST):
    '''
    Represents a filter - the previous expression, which should be a
    sequence, needs to be filtered on this
    '''
    def __init__(self, expr: ast.AST, filter: ast.AST):
        '''
        Create a filter expression.

        Arguments:
            expr        AST of the filter expression
            filter      An expression that evaluates to bool, to be applied
                        on each item of the `expr`'s sequence.
        '''
        self.expr = expr
        self.filter = filter
        self._fields = ('expr', 'filter')
        pass


class _parent_subs(ast.NodeTransformer):
    def __init__(self, parent: Optional[ast.AST],
                 seen_datasources: Dict[int, ast_DataFrame],
                 resolved: Dict[int, ast.AST]):
        self._parent = parent
        self._seen = seen_datasources
        self._resolved = resolved

    def visit_Name(self, a: ast.Name):
        'If this name is p, then we need to replace with parent'
        if a.id == 'p':
            assert self._parent is not None, "Internal programming error"
            return self._parent
        else:
            return a

    def visit_ast_Column(self, a: ast_Column):
        'We have a column embeded here. Sort it out'
        return _render_filter(a.column, self._seen, self._resolved)

    def visit_ast_DataFrame(self, a: ast_DataFrame):
        'Sort out an embded column'
        expr = render(a.dataframe, self._seen, self._resolved)
        return expr


def _get_parent_expression(f: Union[Column, DataFrame],
                           seen_datasources: Dict[int, ast_DataFrame],
                           resolved: Dict[int, ast.AST]) \
        -> ast.AST:
    '''
    Fetch the parent expression. This doesn't feel like we need this somehow. That it should be
    in the below code, integrated
    '''
    if isinstance(f, Column):
        child_filter = _parent_subs(None, seen_datasources, resolved).visit(f.child_expr)
        return child_filter
    else:
        return render(f, seen_datasources, resolved)


def _render_filter(f: Column, seen_datasources: Dict[int, ast_DataFrame],
                   resolved: Dict[int, ast.AST]) \
         -> ast.AST:
    'Render a filter/Mask as a result'
    v = _get_parent_expression(f, seen_datasources, resolved)
    assert v is not None
    return v


def _build_optional_and(a1: Optional[ast.AST], a2: Optional[ast.AST]) -> Optional[ast.AST]:
    'Build an and if necessary'
    if a1 is None and a2 is None:
        return None
    if a1 is None:
        return a2
    if a2 is None:
        return a1
    return ast.BoolOp(op=ast.And(), values=[a1, a2])


def render(d: DataFrame, seen_datasources: Optional[Dict[int, ast_DataFrame]] = None,
           resolved_dataframes: Optional[Dict[int, ast.AST]] = None) \
        -> ast.AST:
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
    datasources: Dict[int, ast_DataFrame] = {} if seen_datasources is None else seen_datasources
    resolved: Dict[int, ast.AST] = {} if resolved_dataframes is None else resolved_dataframes

    # If we are at the top of the chain, then our return is easy.
    if d.parent is None:
        h = hash(str(d))
        if h not in datasources:
            datasources[h] = ast_DataFrame(d)
        return datasources[h]

    # get the parent info
    p_expr = render(d.parent, datasources, resolved)

    # now we need to tack on our info.
    expr = p_expr if d.child_expr is None \
        else _parent_subs(p_expr, datasources, resolved).visit(d.child_expr)  # type: ast.AST
    if d.filter is not None:
        filter_expr = _render_filter(d.filter, datasources, resolved)
        expr = ast_Filter(expr, filter_expr)

    h = hash(ast.dump(expr))
    if h not in resolved:
        resolved[h] = expr
    return resolved[h]
