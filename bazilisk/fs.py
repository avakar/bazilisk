import os, os.path

class _Path:
    def __init__(self, elems):
        self._elems = elems

    def __repr__(self):
        return 'Path({!r})'.format(os.path.join(*self._elems))

    def __truediv__(self, rhs):
        if not isinstance(rhs, str):
            raise TypeError('only strings can be attached to paths')

        return _Path(self._elems + (rhs,))

    def __add__(self, rhs):
        if not isinstance(rhs, (tuple, list)) or any(not isinstance(it, str) for it in rhs):
            raise TypeError('only tuples of strings can be attached to paths')

        return _Path(self._elems + tuple(el for el in rhs if el))

class Fs:
    def make_path(self, path):
        path = os.path.abspath(path)

        r = []
        while True:
            path, tail = os.path.split(path)
            if not tail:
                r.append(path)
                break

            r.append(tail)

        r.reverse()
        return _Path(tuple(r))

    def open(self, path, mode):
        return open(os.path.join(*path._elems), mode)
