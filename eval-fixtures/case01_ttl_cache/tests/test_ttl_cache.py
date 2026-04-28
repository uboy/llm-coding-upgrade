import unittest

from ttl_cache import TTLCache


class FakeClock:
    def __init__(self, start=1000.0):
        self.value = float(start)

    def now(self):
        return self.value

    def advance(self, seconds):
        self.value += float(seconds)


class TTLCacheTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.cache = TTLCache(maxsize=2, ttl_seconds=5, now_func=self.clock.now)

    def test_get_returns_stored_value(self):
        self.cache.set("a", 1)
        self.assertEqual(self.cache.get("a"), 1)
        self.assertEqual(self.cache.stats()["hits"], 1)

    def test_missing_key_returns_default_and_counts_miss(self):
        self.assertEqual(self.cache.get("missing", "fallback"), "fallback")
        self.assertEqual(self.cache.stats()["misses"], 1)

    def test_expired_item_is_removed_lazily(self):
        self.cache.set("a", 1)
        self.clock.advance(5.1)
        self.assertFalse(self.cache.has("a"))
        self.assertEqual(len(self.cache), 0)
        self.assertEqual(self.cache.stats()["expirations"], 1)

    def test_lru_eviction_prefers_oldest_live_item(self):
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        self.assertEqual(self.cache.get("a"), 1)
        self.cache.set("c", 3)
        self.assertIsNone(self.cache.get("b"))
        self.assertEqual(self.cache.get("a"), 1)
        self.assertEqual(self.cache.get("c"), 3)
        self.assertEqual(self.cache.stats()["evictions"], 1)

    def test_per_item_ttl_override(self):
        self.cache.set("short", "x", ttl_seconds=1)
        self.cache.set("long", "y", ttl_seconds=10)
        self.clock.advance(1.5)
        self.assertIsNone(self.cache.get("short"))
        self.assertEqual(self.cache.get("long"), "y")

    def test_delete_and_clear(self):
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        self.assertTrue(self.cache.delete("a"))
        self.assertFalse(self.cache.delete("missing"))
        self.assertEqual(len(self.cache), 1)
        self.cache.clear()
        self.assertEqual(len(self.cache), 0)


if __name__ == "__main__":
    unittest.main()
