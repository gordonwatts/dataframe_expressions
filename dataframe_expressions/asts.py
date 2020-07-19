import ast
from typing import Callable, cast


class ast_DataFrame(ast.AST):
    '''
    Hold onto a dataframe reference
    '''
    _fields = ()

    def __init__(self, dataframe=None):
        ast.AST.__init__(self)
        from dataframe_expressions import DataFrame
        assert dataframe is None or isinstance(dataframe, DataFrame)
        self.dataframe = cast(DataFrame, dataframe)


class ast_Column(ast.AST):
    '''Ast that holds onto a DataFrame reference'''
    _fields = ()

    def __init__(self, col=None):
        ast.AST.__init__(self)
        from dataframe_expressions import Column
        assert col is None or isinstance(col, Column)
        self.column = cast(Column, col)


class ast_Callable(ast.AST):
    'An AST node that is some sort of python callable, along with the df it was called from.'

    _fields = ('name',)

    def __init__(self, callable: Callable = None, relative_to=None):
        '''
        relative_to is optional - in which case this is a function call, not an
        extension method!
        '''
        ast.AST.__init__(self)
        if callable is not None:
            if callable.__name__ == '<lambda>':
                self.name = f'lambda-{callable.__code__.co_filename}:' \
                            f'{callable.__code__.co_firstlineno}'
            else:
                self.name = callable.__name__
        self.callable = callable
        self.dataframe = relative_to


class ast_FunctionPlaceholder(ast.AST):
    'An AST node that represents a function to be called, that is a placeholder'

    _fields = ('name',)

    def __init__(self, callable: Callable = None):
        ast.AST.__init__(self)
        self.name = callable.__name__
        self.callable = callable
