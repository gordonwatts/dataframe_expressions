from dataframe_expressions.utils_ast import CloningNodeTransformer
import ast


def test_clone_simple_ast():

    class my_clone (CloningNodeTransformer):
        def visit_Name(self, a: ast.Name):
            return a

    a = ast.Name(id='hi')
    new_a = my_clone().visit(a)

    assert a is new_a


def test_clone_new_ast():

    class my_clone (CloningNodeTransformer):
        def visit_Name(self, a: ast.Name):
            return ast.Name(id='there')

    a = ast.Name(id='hi')
    new_a = my_clone().visit(a)

    assert a is not new_a
    assert new_a.id == 'there'
    assert a.id == 'hi'


def test_no_mod_in_place():
    class my_clone (CloningNodeTransformer):
        def visit_Name(self, a: ast.Name):
            return ast.Name(id='there')

    c1 = ast.Name(id='hi')
    c2 = ast.Num(n=10)
    a = ast.Compare(ops=[ast.Gt()], left=c1, comparators=[c2])

    new_a = my_clone().visit(a)

    assert a is not new_a
    assert ast.dump(new_a) != ast.dump(a)
    assert ast.dump(a).replace('hi', 'there') == ast.dump(new_a)
