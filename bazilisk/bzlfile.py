import ast
import inspect
import functools
import operator

def parse(fin):
    mod = ast.parse(fin.read())
    assert isinstance(mod, ast.Module)
    return mod

class _Lvalue:
    def __init__(self, dict, key):
        self.dict = dict
        self.key = key

    def store(self, value):
        self.dict[self.key] = value

def builtin(fn, name=None):
    if name is None:
        name = fn.__name__.lstrip('_')
    fn._bzl_builtin = name
    return fn

def make_builtins(obj, ctx):
    r = {}
    for _, fn in inspect.getmembers(obj):
        name = getattr(fn, '_bzl_builtin', None)
        if name is None:
            continue
        r[name] = functools.partial(fn, ctx)
    return r

def evaluate(ast, builtins, ctx, loader):
    e = _Evaluator(builtins, ctx, loader)
    e.visit(ast)
    return e._globals

_binops = {
    ast.Add: operator.add,
    }

class _Evaluator(ast.NodeVisitor):
    def __init__(self, builtins, ctx, loader):
        self._builtins = builtins
        self._ctx = ctx
        self._loader = loader
        self._globals = {}

    def visit_Call(self, e):
        fn = self.visit(e.func)
        return fn(self._ctx, *[self.visit(arg) for arg in e.args], **{ kw.arg: self.visit(kw.value) for kw in e.keywords })

    def visit_Expr(self, e):
        return self.visit(e.value)

    def visit_Assign(self, stmt):
        if len(stmt.targets) != 1:
            err('only a single target is allowed in an assignment', stmt)
        lhs = self.visit(stmt.targets[0])
        rhs = self.visit(stmt.value)
        lhs.store(rhs)

    def visit_Name(self, e):
        if isinstance(e.ctx, ast.Load):
            if e.id in self._globals:
                return self._globals[e.id]
            return self._builtins[e.id]
        elif isinstance(e.ctx, ast.Store):
            return _Lvalue(self._globals, e.id)
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

    def visit_Dict(self, e):
        return { self.visit(k): self.visit(v) for k, v in zip(e.keys, e.values) }

    def visit_Module(self, node):
        for stmt in node.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == 'load':
                # special handling for `load`, instead of calling load(*args),
                # we'll call load(arg0), expect it to return a dict and then introduce
                # the requested names into the global scope
                if len(stmt.value.args) == 0:
                   raise RuntimeError('`load` takes a string argument')

                if not all(isinstance(arg, ast.Str) for arg in stmt.value.args):
                    raise RuntimeError('the arguments to `load` must be string literals')

                bzl = self._loader(stmt.value.args[0].s)

                for arg in stmt.value.args[1:]:
                    self._globals[arg.s] = bzl[arg.s]
                for k, v_expr in stmt.value.keywords:
                    self._globals[k] = bzl[v_expr.s]
            else:
                self.visit(stmt)

    def visit_BinOp(self, e):
        return _binops[type(e.op)](self.visit(e.left), self.visit(e.right))

    def visit_Num(self, e):
        return e.n

    def visit_FunctionDef(self, stmt):
        args = stmt.args
        body = stmt.body
        def user_fn(pkg, *args, **kw):
            pass

        self._globals[stmt.name] = user_fn

    def visit_NameConstant(self, e):
        return e.value

    def visit_Attribute(self, e):
        if not isinstance(e.ctx, ast.Load):
            raise RuntimeError('only reads from structures')
        lhs = self.visit(e.value)
        return getattr(lhs, e.attr)

    def generic_visit(self, node):
        raise RuntimeError('Unknown expression')
