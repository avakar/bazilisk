import ast

def parse(fin):
    mod = ast.parse(fin.read())
    assert isinstance(mod, ast.Module)

    e = _Evaluator()
    e.visit(mod)

    return e._calls

class _Lvalue:
    def __init__(self, dict, key):
        self.dict = dict
        self.key = key

    def store(self, value):
        self.dict[self.key] = value

class _Evaluator(ast.NodeVisitor):
    def __init__(self):
        self._state = {}
        self._calls = []

    def visit_Expr(self, e):
        if not isinstance(e.value, ast.Call):
            raise RuntimeError('invalid statement')

        if not isinstance(e.value.func, ast.Name) or e.value.kwargs is not None or e.value.starargs is not None or e.value.args:
            raise RuntimeError('invalid statement')

        self._calls.append((e.value.func.id, { kw.arg: self.visit(kw.value) for kw in e.value.keywords }))

    def visit_Assign(self, stmt):
        if len(stmt.targets) != 1:
            err('only a single target is allowed in an assignment', stmt)
        lhs = self.visit(stmt.targets[0])
        rhs = self.visit(stmt.value)
        lhs.store(rhs)

    def visit_Name(self, name):
        if isinstance(e.ctx, ast.Load):
            return self._state[name.id]
        elif isinstance(e.ctx, ast.Store):
            return _Lvalue(self._state, name.id)
        else:
            raise RuntimeError('invalid name')

    def visit_Subscript(self, e):
        value = self.visit(e.value)
        index = self.visit(e.slice)
        if isinstance(e.ctx, ast.Load):
            return value[index]
        elif isinstance(e.ctx, ast.Store):
            return _Lvalue(value, index)
        else:
            raise RuntimeError('invalid subscript')

    def visit_Index(self, index):
        return self.visit(index.value)

    def visit_Str(self, e):
        return e.s

    def visit_List(self, e):
        if not isinstance(e.ctx, ast.Load):
            raise RuntimeError('invalid list context')
        return tuple(self.visit(elt) for elt in e.elts)

    def generic_visit(self, node):
        if isinstance(node, ast.Module):
            return ast.NodeVisitor.generic_visit(self, node)
        raise RuntimeError('Unknown expression')
