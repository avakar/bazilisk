import re

def parse_label(label, cur_repo=None, cur_pkg=None):
    '''
    Parse a label into its components. Missing components are
    represented by `None`, empty components by an empty string.

    >>> parse_label('target')
    (None, None, 'target')

    >>> parse_label(':target')
    (None, None, 'target')

    >>> parse_label(':.')
    (None, None, '.')

    >>> parse_label('//:target')
    (None, '', 'target')

    >>> parse_label('//pkg:target')
    (None, 'pkg', 'target')

    >>> parse_label('@repo//:target')
    ('repo', '', 'target')

    >>> parse_label('//pkg')
    (None, 'pkg', 'pkg')
    '''

    m = _label_re.match(label)
    if not m:
        raise RuntimeError('invalid label syntax')

    repo = m.group('repo')
    package = m.group('pkg')
    target = m.group('tgt')

    if target is None:
        if not package:
            raise RuntimeError('target name shall not be omitted in labels referring to a root package')
        target = package.rsplit('/', 1)[-1]

    if package is not None and any(c in ('.', '..') for c in package.split('/')):
        raise RuntimeError('package names shall not contain . or .. components')

    if target != '.' and any(c in ('.', '..') for c in target.split('/')):
        raise RuntimeError('target names shall not contain . or .. components')

    if repo is None:
        repo = cur_repo
    if package is None:
        package = cur_pkg

    return (repo, package, target)

def abslabel(repo, package, target):
    if repo:
        return '@{}//{}:{}'.format(repo, package, target)
    else:
        return '//{}:{}'.format(package, target)

_label_re = re.compile(
    r'('
        r'(@(?P<repo>[a-zA-Z0-9._\-]+))?'
        r'//(?P<pkg>([a-zA-Z0-9._\-]+(/[a-zA-Z0-9._\-]+)*)?)'
    r')?:?'
    r'(?P<tgt>[a-zA-Z0-9_.+\-=,@~]+(/[a-zA-Z0-9_.+\-=,@~]+)*)?'
    )
