from . import bzlfile
from .bzlfile import builtin, make_builtins
from .label import parse_label, abslabel
import errno, ast
import functools

class Rule:
    def __init__(self, implementation, name, pre_attrs):
        self.impl = implementation
        self.name = name
        self._pre_attrs = pre_attrs

    def resolve_attrs(self, base_pkg):
        if not hasattr(self, '_pre_attrs'):
            return

        attrs = {}
        for k, (spec, value) in self._pre_attrs.items():
            if isinstance(value, _Lazy):
                value = value.resolve(base_pkg)
            value = spec.parse(value, base_pkg)
            attrs[k] = value

        self.attrs = attrs
        del self._pre_attrs

def _make_rule(*, implementation=None, attrs={}, outputs=()):
    attrs = dict(attrs)

    attrs.update({
        'features': _attr.string_list(),
        'licenses': _attr.string_list(),
        'data': _attr.label_list(),
        'visibility': _attr.label_list(),
        'compatible_with': _attr.label_list(),
        'distribs': _attr.string_list(),
        'deps': _attr.label_list(),
        'deprecation': _attr.string(),
        'restricted_to': _attr.label_list(),
        'tags': _attr.string_list(),
        'testonly': _attr.bool()
        })

    def rule(pkg, name, visibility=None, **kw):
        if pkg is None:
            raise RuntimeError('Rules can only be called inside the BUILD file')

        for k, spec in attrs.items():
            if spec.mandatory and k not in kw:
                raise RuntimeError('missing mandatory attribute {}'.format(k))

        pre_attrs = {}
        for k, value in kw.items():
            if k not in attrs:
                raise RuntimeError('unknown attribute: {}'.format(k))

            pre_attrs[k] = (attrs[k], value)

        r = Rule(implementation, name, pre_attrs)
        pkg.add_rule(r)

    return rule

class Attr:
    def __init__(self, default, doc, mandatory, parser):
        self.default = default
        self.doc = doc
        self.mandatory = mandatory
        self._parser = parser

    def parse(self, value, base_pkg):
        return self._parser.parse(value, base_pkg)

class SimpleParser:
    def __init__(self, type, values=set()):
        self._type = type
        self._values = values

    def parse(self, value, base_pkg):
        if not isinstance(value, self._type):
            raise RuntimeError('invalid type')

        if self._values and value not in self._values:
            raise RuntimeError('invalid value')

        return value

class LabelParser:
    def __init__(self, executable, allow_files, allow_single_file,
            providers, allow_rules, single_file, cfg, aspects):
        self._executable = executable
        self._allow_files = allow_files
        self._allow_single_file = allow_single_file
        self._providers = providers
        self._allow_rules = allow_rules
        self._single_file = single_file
        self._cfg = cfg
        self._aspects = aspects

    def parse(self, value, base_pkg):
        if not isinstance(value, str):
            raise RuntimeError('invalid type')

        repo_name, pkg_name, target_name = parse_label(value)
        pkg = base_pkg.get_package(pkg_name, repo_name)
        return pkg.get_target(target_name)

class ListParser:
    def __init__(self, non_empty, allow_empty, nested):
        if allow_empty is None:
            allow_empty = not non_empty

        self._allow_empty = allow_empty
        self._nested = nested

    def parse(self, value, base_pkg):
        if not isinstance(value, tuple):
            raise RuntimeError('invalid type')
        if not self._allow_empty and not value:
            raise RuntimeError('expected non-empty list')
        return tuple(self._nested.parse(el, base_pkg) for el in value)

class DictParser:
    def __init__(self, non_empty, allow_empty, key_parser, value_parser):
        if allow_empty is None:
            allow_empty = not non_empty

        self._allow_empty = allow_empty
        self._key_parser = key_parser
        self._value_parser = value_parser

    def parse(self, value, base_pkg):
        if not isinstance(value, dict):
            raise RuntimeError('invalid type')
        if not self._allow_empty and not value:
            raise RuntimeError('expected non-empty list')

        return { self._key_parser.parse(k, base_pkg): self._value_parser.parse(v, base_pkg) for k, v in value.items() }

class _Attr:
    def bool(self, default=False, doc='', mandatory=False, values=[]):
        return Attr(default, doc, mandatory, SimpleParser(bool, values))

    def int(self, default=0, doc='', mandatory=False, values=[]):
        return Attr(default, doc, mandatory, SimpleParser(int, values))

    def string(self, default=0, doc='', mandatory=False, values=[]):
        return Attr(default, doc, mandatory, SimpleParser(str, values))

    def label(self, default=None, doc='', executable=False, allow_files=None, allow_single_file=None,
            mandatory=False, providers=[], allow_rules=None, single_file=False, cfg=None, aspects=[]):
        return Attr(default, doc, mandatory, LabelParser(executable, allow_files, allow_single_file, providers, allow_rules, single_file, cfg, aspects))

    def int_list(self, default=[], doc='', mandatory=False, non_empty=False, allow_empty=None):
        return Attr(default, doc, mandatory, ListParser(non_empty, allow_empty, SimpleParser(int)))

    def string_list(self, default=[], doc='', mandatory=False, non_empty=False, allow_empty=None):
        return Attr(default, doc, mandatory, ListParser(non_empty, allow_empty, SimpleParser(str)))

    def label_list(self, default=None, doc='', allow_files=None, allow_rules=None, providers=[], flags=[],
            mandatory=False, non_empty=False, allow_empty=None, cfg=None, aspects=[]):
        return Attr(default, doc, mandatory, ListParser(non_empty, allow_empty, LabelParser(False, allow_files, False, providers, allow_rules, False, cfg, aspects)))

    def string_dict(self, default=None, doc='', mandatory=False, non_empty=False, allow_empty=None):
        return Attr(default, doc, mandatory, DictParser(non_empty, allow_empty,
            SimpleParser(str),
            SimpleParser(str)))

_attr = _Attr()

def _bld_package(pkg, default_deprecation=None, default_testonly=0, default_visibility=(), features=()):
    pass

def _bld_licenses(pkg, license_types):
    pass

class _Lazy:
    def __add__(self, rhs):
        return _LazyBinOp(self, rhs)

    def __radd__(self, lhs):
        return _LazyBinOp(lhs, self)

class _LazyBinOp(_Lazy):
    def __init__(self, lhs, rhs):
        self._lhs = lhs
        self._rhs = rhs

    def resolve(self, pkg):
        lhs = self._lhs
        rhs = self._rhs

        if isinstance(lhs, _Lazy):
            lhs = lhs.resolve(pkg)
        if isinstance(rhs, _Lazy):
            rhs = rhs.resolve(pkg)

        return lhs + rhs

class _Select(_Lazy):
    def __init__(self, mapping):
        self._mapping = mapping

    def resolve(self, pkg):
        matching = []
        default = None

        for k, v in self._mapping.items():
            repo_name, pkg_name, target_name = parse_label(k)
            if (repo_name, pkg_name, target_name) == (None, 'conditions', 'default'):
                default = v
                continue

            pkg = pkg.get_package(pkg_name, repo_name)

            m = pkg.get_config_setting(target_name)
            if m is not None:
                matching.append((m, v))

        if not matching and default is None:
            raise RuntimeError('no matching case in a select')

        if not matching:
            return default

        mm, vv = matching[0]
        for m, v in matching[1:]:
            if m >= mm:
                mm = m
                vv = v
            elif not m <= mm:
                raise RuntimeError('can\'t select: not largest matching condition')

        return vv

def _bld_select(pkg, mapping):
    return _Select(mapping)

def _bld_config_setting(pkg, *, name, values, visibility):
    pkg.add_config_setting(name, values)

_build_builtins = {
    'package': _bld_package,
    'licenses': _bld_licenses,
    'select': _bld_select,

    'config_setting': _bld_config_setting,

    'cc_library': _make_rule(
        implementation=None,
        attrs={
            'alwayslink': _attr.bool(),
            'srcs': _attr.label_list(),
            'hdrs': _attr.label_list(),
            'copts': _attr.string_list(),
            'defines': _attr.string_list(),
            'textual_hdrs': _attr.label_list(),
            'linkopts': _attr.string_list(),
            },
        outputs=['%(name)']
        ),
    'cc_binary': _make_rule(
        implementation=None,
        attrs={
            'srcs': _attr.label_list(),
            'hdrs': _attr.label_list(),
            'copts': _attr.string_list(),
            'defines': _attr.string_list(),
            'linkopts': _attr.string_list(),
            },
        outputs=['%(name)']
        ),
    'cc_test': _make_rule(
        implementation=None,
        attrs={
            'srcs': _attr.label_list(),
            'hdrs': _attr.label_list(),
            'copts': _attr.string_list(),
            'size': _attr.string(values=['enormous', 'large', 'medium', 'small'], default='medium'),
            'defines': _attr.string_list(),
            'linkopts': _attr.string_list(),
            },
        outputs=['%(name)']
        ),
    }

_bzl_builtins = {
    'select': _bld_select,
    }

class Package:
    """
    A single package.

    Every package has a parent repo. Packages are containers
    for target (i.e. rules and files). Packages also cache
    the parse contents of .bzl files.
    """

    def __init__(self, repo, path):
        self._repo = repo
        self._path = path
        self._bzls = {}
        self._rules = {}
        self._config_settings = {}

    def parse_build_file(self, fin):
        parsed = bzlfile.parse(fin)
        bzlfile.evaluate(parsed, _build_builtins, self, self._load_bzl)

    def get_config_setting(self, name):
        return self._config_settings.get(name)

    def get_package(self, pkg_name=None, repo_name=None):
        if pkg_name is None:
            return self

        return self._repo.get_package(pkg_name, repo_name)

    def add_rule(self, rule):
        self._rules[rule.name] = rule

    def get_target(self, name):
        if name in self._rules:
            rule = self._rules[name]
            rule.resolve_attrs(self)
            return rule
        return File(self._path + name.split('/'))

    def get_file(self, path):
        return self._path + path.split('/')

    def get_bzl(self, name):
        r = self._bzls.get(name)
        if r is None:
            self._bzls[name] = {}

            path = self.get_file(name)
            with self._repo._ws._fs.open(path, 'r') as fin:
                parsed = bzlfile.parse(fin)
                r = bzlfile.evaluate(parsed, _bzl_builtins, self, self._load_bzl)

            self._bzls[name] = r

        return r

    def add_config_setting(self, name, values):
        if self._repo._ws.is_config_matching(values):
            self._config_settings[name] = set(values)
        else:
            self._config_settings[name] = None

    def _load_bzl(self, label):
        repo_name, pkg_name, target_name = parse_label(label)
        pkg = self.get_package(pkg_name, repo_name)
        return pkg.get_bzl(target_name)

class Repo:
    """
    A repository is a collection of packages.

    This is an abstract class from which all repository types derive from.
    The idea is that repository rule does not immediately cause the repo
    to appear in the filesystem. Instead, it is only materialized when
    first access to a package is performed.
    """
    def __init__(self, ws):
        self._ws = ws
        self._packages = {}

    def get_repo(self, name):
        return self._ws.get_repo(name)

    def get_package(self, pkg_name, repo_name=None):
        if repo_name is None:
            pkg = self._packages.get(pkg_name)
            if pkg is None:
                path = self._materialize()
                full_package_path = path + pkg_name.split('/')

                try:
                    fin = self._ws._fs.open(full_package_path / 'BUILD.bazel', 'r')
                except IOError:
                    fin = self._ws._fs.open(full_package_path / 'BUILD', 'r')

                with fin:
                    pkg = Package(self, full_package_path)
                    self._packages[pkg_name] = pkg
                    pkg.parse_build_file(fin)
        else:
            repo = self._ws.get_repo(repo_name)
            pkg = repo.get_package(pkg_name)

        return pkg

class LocalRepo(Repo):
    """
    A repository located somewhere in the filesystem.

    The root repository and repos defined using the `local_repository` rule
    are `LocalRepo`s.
    """

    def __init__(self, ws, path):
        Repo.__init__(self, ws)
        self._path = path

    def _materialize(self):
        return self._path

class File:
    def __init__(self, path):
        self._path = path

class _LoadCtx:
    pass

class Workspace:
    """
    Workspace is mostly a collection of repositories. It also serves as a holder
    for injected dependencies.
    """

    def __init__(self, base_dir, config, *, fs, http):
        self._fs = fs
        self._http = http

        self._config = config
        self._root_dir, ws_file = self._find_workspace_file(base_dir)
        self._repos = {
            '': LocalRepo(self, self._root_dir)
            }

        self._ws_bzl = self._real_load(ws_file, '', '')

    def _real_load(self, fin, cur_repo, cur_pkg):
        with fin:
            mod = bzlfile.parse(fin)

        ctx = _LoadCtx()
        ctx.repo = cur_repo
        ctx.pkg = cur_pkg

        def load(label):
            repo_name, pkg_name, target_name = parse_label(label)
            if pkg_name is None:
                pkg = self._repos[''].get_package('')
            elif repo_name is None:
                pkg = self._repos[''].get_package(pkg_name)
            else:
                pkg = self._repos[repo_name].get_package(pkg_name)

            return pkg.get_bzl(target_name)

        return bzlfile.evaluate(mod, self._make_builtins(), ctx, load)

    def _make_builtins(self):
        def local_repository(ctx, name, path):
            self._repos[name] = LocalRepo(self, self._fs.make_path(path))

        def http_archive(ctx, name, sha256=None, strip_prefix=None, type=None, url=None, urls=None):
            pass

        return vars()

    def is_config_matching(self, match_set):
        return all(self._config.get(k) == v for k, v in match_set.items())

    def load_package(self, repo, package):
        pass

    def get_repo(self, name):
        return self._repos.get(name)

    def resolve_target(self, label, cur_repo, cur_pkg):
        repo, pkg_name, tgt = parse_label(label, cur_repo, cur_pkg)
        pkg = self._repos[repo].get_package(pkg_name)
        return pkg.get_target(tgt)

    def _find_workspace_file(self, base):
        cur = self._fs.make_path(base)
        while True:
            try:
                return cur, self._fs.open(cur / 'WORKSPACE', 'r')
            except IOError as e:
                if e.errno != errno.ENOENT:
                    raise

            cur, tail = self._fs.split(cur)
            if tail == '':
                raise RuntimeError('failed to find WORKSPACE')
