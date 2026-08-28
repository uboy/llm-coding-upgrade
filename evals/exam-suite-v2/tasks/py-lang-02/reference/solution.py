class Cached:
    """Значение вычисляется один раз и кэшируется в obj.__dict__["_cached_<attr>"]."""

    def __init__(self, dependency):
        self.dependency = dependency

    def __set_name__(self, owner, name):
        self.name = name

    @property
    def _cache_key(self):
        return "_cached_" + self.name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        key = self._cache_key
        if key not in obj.__dict__:
            obj.__dict__[key] = getattr(obj, self.dependency)()
        return obj.__dict__[key]

    def __set__(self, obj, value):
        raise AttributeError("read-only")

    def invalidate(self, obj):
        obj.__dict__.pop(self._cache_key, None)
