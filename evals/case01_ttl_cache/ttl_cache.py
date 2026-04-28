from collections import OrderedDict
import time


class TTLCache:
    def __init__(self, maxsize: int, ttl_seconds: float, now_func=None):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self.now_func = now_func or time.time
        self._cache = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    def _is_expired(self, key: str) -> bool:
        entry = self._cache.get(key)
        if entry is None:
            return True
        expires_at, _ = entry
        return self.now_func() > expires_at

    def _remove_expired(self, key: str) -> bool:
        if key in self._cache:
            if self._is_expired(key):
                del self._cache[key]
                self._expirations += 1
                return True
        return False

    def _evict_if_needed(self):
        while len(self._cache) >= self.maxsize:
            oldest_key = next(iter(self._cache))
            if self._remove_expired(oldest_key):
                continue
            del self._cache[oldest_key]
            self._evictions += 1

    def _touch(self, key: str):
        if key in self._cache:
            self._cache.move_to_end(key)

    def get(self, key: str, default=None):
        if key not in self._cache:
            self._misses += 1
            return default
        
        if self._is_expired(key):
            del self._cache[key]
            self._expirations += 1
            self._misses += 1
            return default
        
        self._touch(key)
        self._hits += 1
        _, value = self._cache[key]
        return value

    def set(self, key: str, value, ttl_seconds=None):
        if ttl_seconds is None:
            ttl_seconds = self.ttl_seconds
        
        self._remove_expired(key)
        
        if key in self._cache:
            del self._cache[key]
        
        self._evict_if_needed()
        
        expires_at = self.now_func() + ttl_seconds
        self._cache[key] = (expires_at, value)

    def has(self, key: str) -> bool:
        if key not in self._cache:
            return False
        
        if self._is_expired(key):
            del self._cache[key]
            self._expirations += 1
            return False
        
        return True

    def __len__(self):
        expired_keys = [k for k in self._cache if self._is_expired(k)]
        for key in expired_keys:
            del self._cache[key]
            self._expirations += 1
        return len(self._cache)

    def delete(self, key: str) -> bool:
        if key not in self._cache:
            return False
        
        if self._is_expired(key):
            del self._cache[key]
            self._expirations += 1
            return False
        
        del self._cache[key]
        return True

    def clear(self):
        self._cache.clear()

    def stats(self):
        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "expirations": self._expirations,
        }
