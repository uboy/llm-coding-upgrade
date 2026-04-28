# Case 01: TTL Cache

Implement `ttl_cache.py` so that the test suite passes.

Requirements:

- Export a class `TTLCache`.
- Constructor:
  - `TTLCache(maxsize: int, ttl_seconds: float, now_func=None)`
- Behavior:
  - store key/value pairs with a default TTL;
  - optional per-item TTL override in `set(key, value, ttl_seconds=None)`;
  - expired entries are removed lazily on `get`, `has`, `set`, and `len`;
  - cache eviction policy is LRU among live entries;
  - `get()` updates recency but does not extend TTL;
  - `has(key)` returns `True` only for live entries;
  - `delete(key)` removes an item and returns `True` when the key existed;
  - `clear()` removes all entries;
  - `stats()` returns a dict with `hits`, `misses`, `evictions`, and `expirations`.

Constraints:

- Use only the Python standard library.
- Do not modify tests.
- Keep the implementation in a single file: `ttl_cache.py`.
