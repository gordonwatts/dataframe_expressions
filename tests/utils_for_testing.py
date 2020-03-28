import pytest


@pytest.fixture(autouse=True)
def reset_var_counter():
    from dataframe_expressions.alias import _reset_alias_catalog
    _reset_alias_catalog()
    yield None
    _reset_alias_catalog()
