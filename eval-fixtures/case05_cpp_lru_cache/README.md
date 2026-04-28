# Case 05: Header-only C++ LRU Cache

Implement `lru_cache.hpp` so that the test suite passes.

Requirements:

- Export a class `LRUCache`.
- Constructor:
  - `explicit LRUCache(std::size_t capacity);`
- Methods:
  - `std::optional<std::string> get(int key);`
  - `void put(int key, std::string value);`
  - `std::size_t size() const;`
- Behavior:
  - average `O(1)` get and put;
  - least-recently-used eviction;
  - reading an item refreshes recency;
  - updating an existing key replaces the value and refreshes recency;
  - capacity `0` ignores inserts;
  - use only the C++ standard library.

Constraints:

- Do not modify tests.
- Keep the implementation in a single file: `lru_cache.hpp`.
