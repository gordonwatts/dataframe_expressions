from __future__ import annotations
# Methods to render the DataFrame chain as a set of expressions.
import ast
from typing import Dict, Optional, Union, Tuple

from dataframe_expressions import Column, DataFrame, ast_Callable, ast_Column, ast_DataFrame
from .utils_ast import CloningNodeTransformer


class ast_Filter (ast.AST):
    '''
    Represents a filter - the previous expression, which should be a
    sequence, needs to be filtered on this
    '''

    _fields = ('expr', 'filter')

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


class render_context:
    '''
    Class for internal use - maintains context and references as we move
    through the resolution. While this is returned to user code, it should
    not be accessed by user code!
    '''
    def __init__(self, template: Optional[render_context] = None):
        if template is None:
            self._seen_datasources: Dict[int, ast_DataFrame] = {}
            self._resolved: Dict[int, ast.AST] = {}
        else:
            self._seen_datasources = template._seen_datasources.copy()
            self._resolved = template._resolved.copy()

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


class _parent_subs(CloningNodeTransformer):
    @classmethod
    def transform(cls, a: ast.AST,
                  context: render_context) -> ast.AST:
        v = _parent_subs(context)
        return v.visit(a)

    def __init__(self,
                 context: render_context):
        ast.NodeTransformer.__init__(self)
        self._context = context

    def visit_ast_Column(self, a: ast_Column):
        'We have a column embedded here. Sort it out'
        return _render_filter(a.column, self._context)

    def visit_ast_DataFrame(self, a: ast_DataFrame):
        'Sort out an embedded column'
        expr = render(a.dataframe, self._context)[0]
        return expr


def _render_filter(f: Column, context: render_context) \
         -> ast.AST:
    'Render a filter/Mask as a result'
    v = _parent_subs.transform(f.child_expr, context)
    assert v is not None
    return v


def render(d: Union[DataFrame, Column], in_context: Optional[render_context] = None) \
        -> Tuple[ast.AST, render_context]:
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
        poor-person's way of doing common sub-expression elimination.
    '''
    context = render_context() if in_context is None else in_context

    # Simple out
    if isinstance(d, DataFrame) and d.child_expr is None:
        return context._lookup_dataframe(d), context

    # If this is a column, then it is a comparison expression.
    if isinstance(d, Column):
        return _render_filter(d, context), context

    # now we need to tack on our info.
    assert d.child_expr is not None
    expr = _parent_subs.transform(d.child_expr, context)
    if d.filter is not None:
        filter_expr = _render_filter(d.filter, context)
        expr = ast_Filter(expr, filter_expr)

    return context._resolve_ast(expr), context


def render_callable(callable: ast_Callable, context: render_context, *args) \
        -> Tuple[ast.AST, render_context]:
    '''
    A callable is invoked with the given list of arguments.

    Arguments:
        callable            The parsed out function all (lambda, or a function proper)
        context             The context to use when parsing. Will not be touched or updated.
        args                List of positional arguments to be passed to the lambda. They can
                            be any type, including data frame arguments.

    Returns:
        expr                A python `ast.AST` that contains the complete expression for whatever
                            this function returns. The expression follows the same rules as the
                            return for the `render` function.
        context             New context which are things already seen plus anything new.
    '''
    # Invoke the call
    d_result = callable.callable(*args)
    new_context = render_context(context)

    # Render it
    if isinstance(d_result, DataFrame):
        return render(d_result, new_context)[0], new_context
    elif isinstance(d_result, Column):
        return _render_filter(d_result, new_context), new_context
    else:
        from .utils import _term_to_ast
        return _term_to_ast(d_result,  DataFrame()), new_context
