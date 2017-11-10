import os

def parse_label(label, base=None):
    toks = label.split(':', 1)
    if len(toks) == 1:
        if base is None:
            raise RuntimeError('full path is required')
        return (base, label)

    pkg, target = toks
    if not pkg.startswith('//'):
        raise RuntimeError('absolute package path is needed')

    pkg = pkg[2:]
    if pkg.startswith('/'):
        raise RuntimeError('invalid package')

    return pkg, target

class Rule:
    def __init__(self, pkg, kind, name, params):
        self.pkg = pkg
        self.kind = kind
        self.name = name
        self.params = params

    def full_name(self):
        return '//{}:{}'.format(self.pkg.dir(), self.name)

class Package:
    def __init__(self, ps, name):
        self.ps = ps
        self.name = name
        self.rules = {}

    def dir(self):
        return os.path.join(self.ps.wrk, self.name)

class PackageSet:
    def __init__(self, wrk, schemas):
        self.wrk = wrk
        self._pkgs = {}
        self._schemas = schemas
        self._unresolved = []

    def _load_raw(self, pkg_name):
        if pkg_name in self._pkgs:
            return self._pkgs[pkg_name]
        with open(os.path.join(self.wrk, pkg_name, 'BUILD'), 'r') as fin:
            rules = parse_bzl(fin)

        pkg = Package(self, pkg_name)
        for rule_name, params in rules:
            name = params['name']
            del params['name']
            pkg.rules[name] = Rule(pkg, rule_name, name, params)
        self._pkgs[pkg_name] = pkg
        self._unresolved.append(pkg)
        return pkg

    def _resolve_value(self, value, sch, base_pkg):
        if sch['type'] == 'array':
            if not isinstance(value, tuple):
                raise RuntimeError('expected array')
            return tuple(self._resolve_value(item, sch['items'], base_pkg) for item in value)
        if sch['type'] == 'string':
            if not isinstance(value, str):
                raise RuntimeError('expected string')
            return value
        if sch['type'] == 'label':
            if not isinstance(value, str):
                raise RuntimeError('expected label')
            pkg, target = parse_label(value, base_pkg)
            pkg = self._load_raw(pkg)
            return pkg.rules[target]

    def _resolve(self, pkg):
        for rule in pkg.rules.values():
            sch = self._schemas[rule.kind]
            new_params = {}
            for name in sch:
                if name not in rule.params:
                    value = sch[name]['default']
                else:
                    value = rule.params[name]
                new_params[name] = self._resolve_value(value, sch[name], pkg.name)

            rule.params = new_params

        return pkg

    def _resolve_all(self):
        while self._unresolved:
            pkg = self._unresolved.pop()
            self._resolve(pkg)

    def load_pkg(self, name):
        r = self._load_raw(name)
        self._resolve_all()
        return r

    def load_target(self, name):
        pkg, target = parse_label(name)
        pkg = self.load_pkg(pkg)
        return pkg.rules[target]
