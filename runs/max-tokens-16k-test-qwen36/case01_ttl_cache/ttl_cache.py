import time
from collections import OrderedDict

class TTLCache:
    def __init__(self, maxsize: int, ttl_seconds: float, now_func=None):
        self.maxsize = maxsize
        self.default_ttl = ttl_seconds
        self.now_func = now_func or time.time
        self._cache = OrderedDict()
        self._stats = {'hits': 0, 'misses': 0, 'evictions': 0, 'expirations': 0}

    def _now(self):
        return self.now_func()

    def _clean_expired(self):
        now = self._now()
        expired_keys = [k for k, (v, expire, ttl) in self._cache.items() if expire <= now]
        for k in expired_keys:
            del self._cache[k]
            self._stats['expirations'] += 1

    def set(self, key, value, ttl_seconds=None):
        self._clean_expired()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expire = self._now() + ttl
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.maxsize:
                self._cache.popitem(last=False)
                self._stats['evictions'] += 1
        self._cache[key] = (value, expire, ttl)

    def get(self, key):
        self._clean_expired()
        if key in self._cache:
            value, expire, ttl = self._cache[key]
            if expire > self._now():
                self._cache.move_to_end(key)
                self._stats['hits'] += 1
                return value
            else:
                del self._cache[key]
                self._stats['expirations'] += 1
                self._stats['misses'] += 1
                return None
        self._stats['misses'] += 1
        return None

    def has(self, key):
        self._clean_expired()
        if key in self._cache:
            _, expire, _ = self._cache[key]
            if expire > self._now():
                return True
            else:
                del self._cache[key]
                self._stats['expirations'] += 1
                return False
        return False

    def delete(self, key):
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self):
        self._cache.clear()
        self._stats = {'hits': 0, 'misses': 0, 'evictions': 0, 'expirations': 0}

    def __len__(self):
        self._clean_expired()
        return len(self._cache)

    def stats(self):
        return self._stats.copy()