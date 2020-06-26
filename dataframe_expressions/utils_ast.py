import ast


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
