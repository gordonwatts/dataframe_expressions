import ast
from typing import Callable, Union, Optional
import inspect

from dataframe_expressions import (
    Column, DataFrame, ast_Callable, ast_Column, ast_DataFrame, ast_FunctionPlaceholder)


# TODO: Fix the circular include triggered by _term_to_ast


class DataFrameTypeError(Exception):
    '''Thrown when we don't understand the type in an expression'''
    def __init__(self, message):
        Exception.__init__(self, message)


def _term_to_ast(term: Union[int, str, DataFrame, Column, Callable],
                 parent_df: Optional[Union[DataFrame, Column]]) \
        -> ast.AST:
    '''Return an AST that represents the current term

    Args:
        term        The term (int, string, float, DataFrame, Column, etc.)

    Returns
    '''
    other_ast = None
    if isinstance(term, int) or isinstance(term, float):
        other_ast = ast.Num(n=term)
    elif isinstance(term, str):
        other_ast = ast.Str(s=term)
    elif isinstance(term, DataFrame):
        other_ast = ast_DataFrame(term)
    elif isinstance(term, Column):
        other_ast = ast_Column(term)
    elif callable(term):
        assert parent_df is not None, \
            'Internal Error: Parent DF is required when creating a Callable'
        assert isinstance(parent_df, DataFrame)
        other_ast = ast_Callable(term, parent_df)
    else:
        raise DataFrameTypeError("Do not know how to render a term "
                                 f"of type '{type(term).__name__}'.")

    return other_ast


def user_func(f: Callable) -> Callable:
    '''
    This will allow a function to be embedded into the DataFrame call sequence. For example,

        ```
        @user_func
        def add_it(p1: float) -> float:
            assert False, 'should never be called'
        ```

        And then if you've got `df` defined as your dataframe, you can write:

        ```
        add_it(df.jets.pt)
        ```

        And the resulting `DataFrame` will effectively call `add_it` on each value of `pt` in the
        sequence.

        There are a lot of limitations in this prototype!
    '''
    def emulate_function_call_in_DF(*args):
        f_sig = inspect.signature(f)
        if len(f_sig.parameters) != len(args):
            raise Exception(f'Function {f.__name__} was called with {len(args)} arguments '
                            f'- but needs {len(f_sig.parameters)}')
        f_args = [_term_to_ast(a, None) for a in args]
        call = ast.Call(func=ast_FunctionPlaceholder(f), args=f_args)
        return DataFrame(DataFrame(), expr=call)

    return emulate_function_call_in_DF


def exclusive_class(o_class: Callable[[object], object]) -> Callable[[object], object]:
    '''
    A class that will extend the object model can only access properties that
    are explicitly defined.
    '''
    orig_init = o_class.__init__

    def __init__(self, *args, **kws):
        # The `__no_arb_attr` is a magic string and appears elsewhere in the code
        # as a flag (its value does not matter)
        self.__no_arb_attr = True
        orig_init(self, *args, **kws)  # Call the original __init__

    o_class.__init__ = __init__  # Set the class' __init__ to the new one
    return o_class


def _replace_parent_references(a: ast.AST, sub: DataFrame) -> ast.AST:
    '''
    Find Name(id='p') and replace them with sub in a.
    '''
    class replace_p(ast.NodeTransformer):
        def __init__(self, sub: DataFrame):
            ast.NodeTransformer.__init__(self)
            self._sub = ast_DataFrame(sub)

        def visit_Name(self, a: ast.Name):
            if a.id == 'p':
                return self._sub
            return self.generic_visit(a)

    return replace_p(sub).visit(a)


class CloningNodeTransformer(ast.NodeVisitor):
    """
    A :class:`NodeVisitor` subclass that walks the abstract syntax tree and
    allows modification of nodes.
    The `NodeTransformer` will walk the AST and use the return value of the
    visitor methods to replace or remove the old node.  If the return value of
    the visitor method is ``None``, the node will be removed from its location,
    otherwise it is replaced with the return value.  The return value may be the
    original node in which case no replacement takes place.
    Here is an example transformer that rewrites all occurrences of name lookups
    (``foo``) to ``data['foo']``::
       class RewriteName(NodeTransformer):
           def visit_Name(self, node):
               return Subscript(
                   value=Name(id='data', ctx=Load()),
                   slice=Constant(value=node.id),
                   ctx=node.ctx
               )
    Keep in mind that if the node you're operating on has child nodes you must
    either transform the child nodes yourself or call the :meth:`generic_visit`
    method for the node first.
    For nodes that were part of a collection of statements (that applies to all
    statement nodes), the visitor may also return a list of nodes rather than
    just a single node.
    Usually you use the transformer like this::
       node = YourTransformer().visit(node)
    """

    def _get_new_value(self, old_value):
        changed = False
        if isinstance(old_value, list):
            new_values = []
            for value in old_value:
                if isinstance(value, ast.AST):
                    old = value
                    value = self.visit(value)
                    if old is not value:
                        changed = True
                    if value is None:
                        continue
                    elif not isinstance(value, ast.AST):
                        new_values.extend(value)
                        continue
                new_values.append(value)
            return new_values, changed
        elif isinstance(old_value, ast.AST):
            new_node = self.visit(old_value)
            return new_node, new_node is not old_value
            # if new_node is None:
            #     delattr(node, field)
            # else:
            #     setattr(node, field, new_node)
        return old_value, False

    def generic_visit(self, node):
        # Get new and old values
        r = [(field, old_value, self._get_new_value(old_value))
             for field, old_value in ast.iter_fields(node)]

        if len(r) == 0:
            return node

        if all(not i[2][1] for i in r):
            return node

        # Ok - there was a modification. We need to clone the class and pass that
        # back up.

        new_node = node.__class__()
        for f in r:
            if f[1] is not None:
                setattr(new_node, f[0], f[2][0])
        return new_node
