import ast

import pytest
from dataframe_expressions import dumps, user_func, DataFrame
from dataframe_expressions.asts import ast_DataFrame


def test_new_df_repeat():
    from dataframe_expressions.dump_dataframe import var_context
    v = var_context()
    df = DataFrame()
    name_1 = v.new_df(df)
    name_2 = v.new_df(df)

    assert name_1 == name_2


def test_lookup_fails():
    from dataframe_expressions.dump_dataframe import var_context
    v = var_context()
    df = DataFrame()
    with pytest.raises(Exception):
        v.lookup(df)


def test_root():
    df = DataFrame()

    r = dumps(df)

    assert len(r) == 1
    assert r[0] == 'df_1 = DataFrame()'


def test_leaf():
    df = DataFrame().x

    r = dumps(df)

    assert '\n'.join(r) == '''df_1 = DataFrame()
df_2 = df_1.x'''


@pytest.mark.parametrize("operator_text, op", [("+", lambda a, b: a+b),
                                               ("-", lambda a, b: a-b),
                                               ("*", lambda a, b: a*b),
                                               ("/", lambda a, b: a/b),
                                               ])
def test_binary_math_operator(operator_text, op):
    df = DataFrame()
    df1 = op(df.x, df.y)

    r = dumps(df1)

    assert '\n'.join(r) == f'''df_1 = DataFrame()
df_2 = df_1.x
df_3 = df_1.y
df_4 = df_2 {operator_text} df_3'''


@pytest.mark.parametrize("operator_text, op", [(">", lambda a, b: a > b),
                                               ("<", lambda a, b: a < b),
                                               (">=", lambda a, b: a >= b),
                                               ("<=", lambda a, b: a <= b),
                                               ("!=", lambda a, b: a != b),
                                               ("==", lambda a, b: a == b),
                                               ])
def test_binary_comparison_operator(operator_text, op):
    df = DataFrame()
    df1 = op(df.x, df.y)

    r = dumps(df1)

    assert '\n'.join(r) == f'''df_1 = DataFrame()
df_2 = df_1.x
df_3 = df_1.y
df_4 = df_2 {operator_text} df_3'''


@pytest.mark.parametrize("constant, output", [
    (1, "1"),
    (1.5, "1.5"),
    ("hi", "'hi'"),
    ((1, 2), "(1,2)"),
    ((), "()"),
    ([1, 2], "[1,2]")
])
def test_constant(constant, output):
    df = DataFrame()
    df1 = df[df > constant]

    r = dumps(df1)

    assert '\n'.join(r) == f'''df_1 = DataFrame()
df_2 = df_1 > {output}
df_3 = df_1[df_2]'''


def test_string():
    df = DataFrame()
    df1 = df.x == "hi"

    r = dumps(df1)

    assert '\n'.join(r) == '''df_1 = DataFrame()
df_2 = df_1.x
df_3 = df_2 == 'hi\''''


@pytest.mark.parametrize("operator_text, op", [("&", lambda a, b: a & b),
                                               ("|", lambda a, b: a | b),
                                               ])
def test_binary_logic_operator(operator_text, op):
    df = DataFrame()
    df1 = op(df.x > 1, df.y < 1)

    r = dumps(df1)

    assert '\n'.join(r) == f'''df_1 = DataFrame()
df_2 = df_1.x
df_3 = df_2 > 1
df_4 = df_1.y
df_5 = df_4 < 1
df_6 = df_3 {operator_text} df_5'''


def test_filter():
    df = DataFrame()
    df1 = df[df.x > 0]

    r = dumps(df1)

    assert '\n'.join(r) == '''df_1 = DataFrame()
df_2 = df_1.x
df_3 = df_2 > 0
df_4 = df_1[df_3]'''


def test_callback():
    df = DataFrame()
    df1 = df.map(lambda e: e.x)

    r = dumps(df1)

    assert '\n'.join(r) == '''df_1 = DataFrame()
df_2 = <lambda>(e)
df_3 = df_1.map(df_2)'''


def test_python_builtin_function():
    df = DataFrame()
    df1 = abs(df.x)

    r = dumps(df1)

    assert '\n'.join(r) == '''df_1 = DataFrame()
df_2 = df_1.x
df_3 = df_2.abs()'''


def test_python_other_function():
    @user_func
    def doit(i: float):
        assert 'do not call this'

    df = DataFrame()
    df1 = doit(df.x)

    r = dumps(df1)

    assert '\n'.join(r) == '''df_1 = DataFrame()
df_2 = df_1.x
df_3 = doit(df_2)'''


def test_python_np_function():
    import numpy
    df = DataFrame()
    df1 = numpy.histogram(df.x)

    r = dumps(df1)  # type: ignore

    assert '\n'.join(r) == '''df_1 = DataFrame()
df_2 = df_1.x
df_3 = np_histogram(df_2)'''


def test_python_kw_args():
    import numpy
    df = DataFrame()
    df1 = numpy.histogram(df.x, bins=50)

    r = dumps(df1)  # type: ignore

    assert '\n'.join(r) == '''df_1 = DataFrame()
df_2 = df_1.x
df_3 = np_histogram(df_2,bins=50)'''


def test_bogus_function_call():
    df1 = DataFrame(expr=ast.Call(func=ast.BinOp()))

    with pytest.raises(Exception) as e:
        dumps(df1)

    assert "BinOp" in str(e.value)


def test_nested_dataframe():
    df1 = DataFrame()
    df2 = DataFrame(expr=ast_DataFrame(df1))

    r = dumps(df1 + df2)

    assert '\n'.join(r) == '''df_1 = DataFrame()
df_2 = df_1 + df_1'''


def test_lambda_function():
    df = DataFrame()
    df.jets['ptgev'] = lambda j: j.pt / 1000
    df1 = df.jets.ptgev

    r = dumps(df1)

    assert '\n'.join(r) == '''df_1 = DataFrame()
df_2 = df_1.jets
df_3 = <<lambda>(j)>(df_2)'''


def test_repeated_use():
    df = DataFrame()
    df1 = df.jets("Hi")
    df2 = df1 + df1

    r = dumps(df2)

    assert '\n'.join(r) == '''df_1 = DataFrame()
df_2 = df_1.jets('Hi')
df_3 = df_2 + df_2'''
