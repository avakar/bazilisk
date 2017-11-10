import argparse
import os
import uuid
import sys

from . import msvc_ccproj
from .fs import Fs
from .label import parse_label
from .msvc import gen_msvc
from .package import PackageSet
from .workspace import Workspace

def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workspace', '-w', default='.')
    ap.add_argument('--output', '-o', default='.')
    ap.add_argument('targets', nargs='*', default=[])
    args = ap.parse_args()

    config = {}
    labels = []

    for tgt in args.targets:
        if '=' in tgt:
            k, v = tgt.split('=', 1)
            config[k] = v
        else:
            labels.append(tgt)

    w = Workspace(args.workspace, config, fs=Fs(), http=None)
    targets = set(w.resolve_target(lbl, '', '') for lbl in labels)

    gen_projs = {}

    used_names = set()

    seen = set(targets)
    while targets:
        tgt = targets.pop()

        if isinstance(tgt, FileTarget):
            tgt = tgt.rule

        if isinstance(tgt, (CcBinary, CcLibrary, CcTest)):
            name_base = tgt.package.name.replace('/', '_') + tgt.name
            name = name_base

            name_idx = 0
            while name in used_names:
                name_idx += 1
                name = name_base + '_' + str(name_idx)

            used_names.add(name)

            gen_projs[tgt] = (os.path.join(args.output, name + '.vcxproj'), uuid.uuid4())
            for dep in tgt.deps:
                if dep not in seen:
                    seen.add(dep)
                    targets.add(dep)
        else:
            raise RuntimeError('XXX not implemented')

    for tgt, (fname_root, uuid) in gen_projs:
        with open(name + '.vcxproj', 'w') as fout:
            fout.write(msvc_ccproj.make_vcxproj(p))

    return 0

if __name__ == '__main__':
    sys.exit(_main())
