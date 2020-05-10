import ast
from typing import Callable


class ast_DataFrame(ast.AST):
    '''
    Hold onto a dataframe reference
    '''

    def __init__(self, dataframe = None):
        ast.AST.__init__(self)
        self._fields = ()
        self.dataframe = dataframe


class ast_Column(ast.AST):
    '''Ast that holds onto a DataFrame reference'''
    def __init__(self, col = None):
        ast.AST.__init__(self)
        self._fields = ()
        self.column = col


class ast_Callable(ast.AST):
    'An AST node that is some sort of python callable, along with the df it was called from.'
    def __init__(self, callable: Callable = None, relative_to=None):
        '''
        relative_to is optional - in which case this is a function call, not an
        extension method!
        '''
        ast.AST.__init__(self)
        if callable.__name__ == '<lambda>':
            self.name = f'lambda-{callable.__code__.co_filename}:' \
                        f'{callable.__code__.co_firstlineno}'
        else:
            self.name = callable.__name__
        self._fields = ('name',)
        self.callable = callable
        self.dataframe = relative_to


class ast_FunctionPlaceholder(ast.AST):
    'An AST node that represents a function to be called, that is a placeholder'
    def __init__(self, callable: Callable = None):
        ast.AST.__init__(self)
        self.name = callable.__name__
        self._fields = ('name',)
        self.callable = callable
