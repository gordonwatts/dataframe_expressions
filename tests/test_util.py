from dataframe_expressions.utils import DataFrameTypeError, _term_to_ast
import pytest
import ast


@pytest.mark.parametrize("the_term, the_type", [
    (1, ast.Num),
    (1.5, ast.Num),
    ((-1.0, 50.0), ast.Tuple),
    ([1, 2], ast.List),
    ])
def test_term_to_ast_type_check(the_term, the_type):
    assert isinstance(_term_to_ast(the_term, None), the_type)


def test_term_to_ast_bad():
    with pytest.raises(DataFrameTypeError):
        _term_to_ast(complex(1, 10), None)  # type: ignore
