# Methods to render the DataFrame chain as a set of expressions.
import ast
from typing import Dict, Optional, Union, Tuple

from .DataFrame import Column, DataFrame, ast_Callable, ast_Column, ast_DataFrame


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


class _render_context:
    '''
    Class for internal use - maintains context and references as we move
    through the resolution. While this is returned to user code, it should
    not be accessed by user code!
    '''
    def __init__(self):
        self._seen_datasources: Dict[int, ast_DataFrame] = {}
        self._resolved: Dict[int, ast.AST] = {}

    def _lookup_dataframe(self, df: DataFrame) -> ast_DataFrame:
        '''
        See if a raw dataframe has already been tagged. If so, make sure
        we return the same object.
        '''
        h = hash(str(df))
        if h not in self._seen_datasources:
            self._seen_datasources[h] = ast_DataFrame(df)
        return self._seen_datasources[h]

    def _resolve_ast(self, a: ast.AST) -> ast.AST:
        '''
        Look to see if this `ast.AST` has already been run, and if so, return
        the same object to make downstream processing (and loop connection)
        easier.
        '''
        h = hash(ast.dump(a))
        if h not in self._resolved:
            self._resolved[h] = a
        return self._resolved[h]


class _parent_subs(ast.NodeTransformer):
    def __init__(self, parent: Optional[ast.AST],
                 context: _render_context):
        self._parent = parent
        self._context = context

    def visit_Name(self, a: ast.Name):
        'If this name is p, then we need to replace with parent'
        if a.id == 'p':
            assert self._parent is not None, "Internal programming error"
            return self._parent
        else:
            return a

    def visit_ast_Column(self, a: ast_Column):
        'We have a column embeded here. Sort it out'
        return _render_filter(a.column, self._context)

    def visit_ast_DataFrame(self, a: ast_DataFrame):
        'Sort out an embded column'
        expr = render(a.dataframe, self._context)[0]
        return expr


def _get_parent_expression(f: Union[Column, DataFrame],
                           context: _render_context) \
        -> ast.AST:
    '''
    Fetch the parent expression. This doesn't feel like we need this somehow. That it should be
    in the below code, integrated
    '''
    if isinstance(f, Column):
        child_filter = _parent_subs(None, context).visit(f.child_expr)
        return child_filter
    else:
        return render(f, context)[0]


def _render_filter(f: Column, context: _render_context) \
         -> ast.AST:
    'Render a filter/Mask as a result'
    v = _get_parent_expression(f, context)
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


def render(d: DataFrame, in_context: Optional[_render_context] = None) \
        -> Tuple[ast.AST, _render_context]:
    '''
    Follows the data frame back to the start and renders it in a complete AST.

    Arguments:
        d           DataFrame rendered from the start

    Returns:
        expr        A python ast.AST that contains the complete expression for whatever this
                    dDataFrame is meant to represent. It will include the special `ast_Filter`
                    nodes that indicate a filtering operation is to take place

    Notes:
        In many cases, expressions are repeated. For example, `df[(df.x > 10) & (df.y > 10)]`,
        implies iterating over df. The `ast.AST` that represents `df` will be the same object
        in this case. That means the object hash will be the same. This can be used as a
        poor-person's way of doing common sub-expression elminiation.
    '''
    context = _render_context() if in_context is None else in_context

    # If we are at the top of the chain, then our return is easy.
    if d.parent is None:
        return context._lookup_dataframe(d), context

    # get the parent info
    p_expr, _ = render(d.parent, context)

    # now we need to tack on our info.
    expr = p_expr if d.child_expr is None \
        else _parent_subs(p_expr, context).visit(d.child_expr)  # type: ast.AST
    if d.filter is not None:
        filter_expr = _render_filter(d.filter, context)
        expr = ast_Filter(expr, filter_expr)

    return context._resolve_ast(expr), context


def render_callable(callable: ast_Callable, context: _render_context, *args) -> ast.AST:
    '''
    A callable is invoked with the given list of arguments.

    Arguments:
        callable            The parsed out function all (labmda, or a funciton proper)
        args                List of positional arguments to be passed to the lambda. They can
                            be any type, including data frame arguments.

    Returns:
        expr                A python `ast.AST` that contains the complete expression for whatever
                            this function returns. The expression follows the same rules as the
                            return for the `render` function.
    '''
    # Invoke the call
    d_result = callable.callable(*args)

    # Render it
    if isinstance(d_result, DataFrame):
        return render(d_result, context)[0]
    else:
        from .utils import _term_to_ast
        return _term_to_ast(d_result,  DataFrame())
