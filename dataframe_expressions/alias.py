import ast
from typing import Callable, Optional

from .DataFrame import DataFrame


def _reset_alias_catalog():
    'For testing - reset to ground state'
    global _alias_catalog
    _alias_catalog = {}


class _alias_info:
    '''
    Hold onto all info we need to resolve an alias
    '''
    def __init__(self, base_obj: str, name: str, func_define: Callable[[DataFrame], DataFrame]):
        self._base_obj = base_obj
        self._func = func_define
        self._name = name

    def apply(self, df: DataFrame) -> DataFrame:
        return self._func(df)


# List of the known aliases
_alias_catalog = {}


def define_alias(base_obj: str, name: str, func_define: Callable[[DataFrame], DataFrame]):
    '''
    Define an alias that can be used as a short cut for a reference later on. For example:

        ```
        df = DataFrame()
        define_alias (".jets", "pts", lambda o: o.pt/1000.0)
        ```

    When you write `df.jets.pts` it is the same as writing `df.jets.pt/1000.0`.

    ## Adding aliases of the same name

    This implementation does no checking as things are added. You can have different base names,
    and if the base_obj's are different they will match differently, as you would expect.
    But they are evaluated last one entered first, so if you enter a complete wildcard, nothing
    else will ever get looked at. If this wasn't a prototype perhaps I'd not allow this.

    ## How `base_obj` works

        - The leading `.` indicates a reference from the root dataframe
        - Without the leading `.` it will just match from the current position. For example,
        if `base_obj` is `""`, then anytime you write `xxx.pts` it will become `xxx.pt/1000.0`.\
        This allows some level of wildcard.

    ## Restrictions on `func_define`

        - This function is called with a DataFrame as its argument. You may only do what you
          would normally do. So not loops, etc. It must return a new DataFrame!! Not even
          constant returns are supported just yet!

    Arguments:
        base_obj            Base objects, starting with a `.` indicating path to where this should
                            be applied.
        name                Name of the new functions
        func_define         Lambda that returns the modified DAG. See restrictions above for rules
                            on this lambda.
    '''
    a_info = _alias_info(base_obj, name, func_define)
    if name in _alias_catalog:
        _alias_catalog[name].append(a_info)
    else:
        _alias_catalog[name] = [a_info]


def _matches_pattern_str(df: DataFrame, a: str) -> bool:
    '''
    Return true if this matches the pattern specificed in a
    '''
    # Simple cases first
    if a is None or len(a) == 0:
        return True
    if a == '.':
        return df.parent is None
    if df.parent is None:
        return False

    # We don't do total expression replacement, sadly
    if not isinstance(df.child_expr, ast.Attribute):
        return False

    # Ok - so we need to split and go down a level
    parts = a.split('.')
    name = parts[-1]
    if name != df.child_expr.attr:
        return False

    a_minus = '.'.join(parts[:-1])
    if len(parts) == 2 and parts[0] == '':
        a_minus = '.'
    return _matches_pattern_str(df.parent, a_minus)


def _matches_pattern(df: DataFrame, a: _alias_info) -> bool:
    '''
    Return true if this matches the patter specified in a.
    '''
    return _matches_pattern_str(df, a._base_obj)


def lookup_alias(df: DataFrame, name: str) -> Optional[_alias_info]:
    if name not in _alias_catalog:
        return None

    # Now see if they pattern match
    for a in _alias_catalog[name]:
        if _matches_pattern(df, a):
            return a

    return None
