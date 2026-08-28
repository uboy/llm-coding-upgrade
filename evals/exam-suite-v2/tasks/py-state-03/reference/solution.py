class DepCache:
    def __init__(self):
        self._data = {}
        self._deps = {}
        self._rdeps = {}

    def put(self, key, value, deps=None):
        deps = list(deps or [])
        self._drop(key)
        self._data[key] = value
        self._deps[key] = deps
        for d in deps:
            self._rdeps.setdefault(d, set()).add(key)

    def _drop(self, key):
        self._data.pop(key, None)
        for d in self._deps.pop(key, []):
            s = self._rdeps.get(d)
            if s:
                s.discard(key)
                if not s:
                    self._rdeps.pop(d, None)

    def get(self, key):
        return self._data[key]

    def keys(self):
        return sorted(self._data)

    def invalidate(self, prefix):
        to_kill = [k for k in self._data if k.startswith(prefix)]
        while to_kill:
            k = to_kill.pop()
            if k not in self._data:
                continue
            dependents = list(self._rdeps.get(k, ()))
            self._drop(k)
            to_kill.extend(dependents)
