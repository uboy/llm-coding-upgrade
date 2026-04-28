#include <cassert>
#include <optional>
#include <string>

#include "../lru_cache.hpp"

int main() {
    LRUCache cache(2);
    assert(cache.size() == 0);
    assert(!cache.get(1).has_value());

    cache.put(1, "one");
    cache.put(2, "two");
    assert(cache.size() == 2);
    assert(cache.get(1) == std::optional<std::string>("one"));

    cache.put(3, "three");
    assert(!cache.get(2).has_value());
    assert(cache.get(1) == std::optional<std::string>("one"));
    assert(cache.get(3) == std::optional<std::string>("three"));

    cache.put(1, "ONE");
    assert(cache.get(1) == std::optional<std::string>("ONE"));
    assert(cache.size() == 2);

    LRUCache zero_cache(0);
    zero_cache.put(10, "ignored");
    assert(zero_cache.size() == 0);
    assert(!zero_cache.get(10).has_value());

    return 0;
}
