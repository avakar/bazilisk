import sys, argparse
from .bzlfile import parse as parse_bzl
from .package import PackageSet, parse_label
from .msvc import gen_msvc

import os
def _find_workspace_dir(base):
    cur = os.path.abspath(base)
    while True:
        if os.path.isfile(os.path.join(cur, 'WORKSPACE')):
            return cur
        cur, tail = os.path.split(cur)
        if tail == '':
            raise RuntimeError('failed to find WORKSPACE')

def _find_packages(wrk):
    for top, dirnames, filenames in os.walk(wrk):
        if 'BUILD' in filenames:
            yield os.path.relpath(top, wrk)
        dirnames[:] = [dir for dir in dirnames if not dir.startswith('.')]

list_of_labels = {
    'type': 'array',
    'items': {
        'type': 'label',
        },
    'default': (),
    }

list_of_strings = {
    'type': 'array',
    'items': {
        'type': 'string',
        },
    'default': (),
    }

_schemas = {
    'cc_library': {
        'deps': list_of_labels,
        'srcs': list_of_strings,
        'hdrs': list_of_strings,
        'includes': list_of_strings,
        },
    'cc_test': {
        'deps': list_of_labels,
        'srcs': list_of_strings,
        'hdrs': list_of_strings,
        'includes': list_of_strings,
        },
    }

def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workspace', '-w', default='.')
    ap.add_argument('target', nargs='*')
    args = ap.parse_args()

    wrk = _find_workspace_dir(args.workspace)

    ps = PackageSet(wrk, _schemas)

    if not args.target:
        targets = []
        for label in _find_packages(wrk):
            pkg = ps.load_pkg(label)
            targets.extend(pkg.rules.values())
    else:
        targets = [ps.load_target(label) for label in args.target]

    target_dir = os.path.join(wrk, '_build')

    try:
        os.mkdir(target_dir)
    except OSError:
        pass

    gen_msvc(target_dir, targets)
    return 0

if __name__ == '__main__':
    sys.exit(_main())
