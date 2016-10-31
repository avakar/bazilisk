from mako.template import Template
from uuid import UUID, uuid5
from itertools import chain
import os, os.path

_dir = os.path.split(__file__)[0]
def _load_template(fname):
    with open(os.path.join(_dir, fname), 'r') as fin:
        return Template(fin.read())

_base_guid = UUID('{b98a5b3f-86a9-4065-87d6-6a0ea0627409}')

_vcxproj_templ = _load_template('vcxproj.mako')
_sln_templ = _load_template('sln.mako')

def _close(tgts):
    q = set(tgts)
    r = set(tgts)
    while q:
        cur = q.pop()
        for dep in cur.params.get('deps', ()):
            if dep not in r:
                r.add(dep)
                q.add(dep)
    return r

def _tgt_guid(tgt):
    return '{{{}}}'.format(str(uuid5(_base_guid, tgt.full_name())).upper())

def gen_msvc(target_dir, targets):
    targets = _close(targets)
    all_projs = []

    for tgt in targets:
        # XXX: names may not be unique
        proj_fname = os.path.join(target_dir, '{}.vcxproj'.format(tgt.name))

        srcs = []
        hdrs = []
        for fname in chain(tgt.params['srcs'], tgt.params['hdrs']):
            rname = os.path.relpath(os.path.join(tgt.pkg.dir(), fname), target_dir)
            if fname.rsplit('.', 1)[1] in ('h', 'hpp', 'hxx'):
                hdrs.append(rname)
            else:
                srcs.append(rname)

        guid = _tgt_guid(tgt)

        all_projs.append((tgt.name, guid))

        out = _vcxproj_templ.render(
            name=tgt.name,
            platforms=('Win32', 'x64'),
            guid=guid,
            srcs=srcs,
            hdrs=hdrs,
            )

        with open(proj_fname, 'w') as fout:
            fout.write(out)

    sln_fname = os.path.join(target_dir, 'all.sln')

    out = _sln_templ.render(
        projs=all_projs,
        sln_guid='{76261e51-ac20-4b85-8937-0e7579815166}'.upper(),
        plats=(('x64', 'x64'), ('Win32', 'x86'))
        )

    with open(sln_fname, 'w') as fout:
        fout.write(out)
