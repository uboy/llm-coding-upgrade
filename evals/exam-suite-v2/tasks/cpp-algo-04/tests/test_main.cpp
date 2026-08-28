#include "../solution.h"
#include <cstdio>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    { auto r = min_window({"a","x","b","y","a","b"}, {"a","b"}); CHECK(r && r->begin == 4 && r->end == 6); }
    { auto r = min_window({"a"}, {}); CHECK(r && r->begin == 0 && r->end == 0); }
    { auto r = min_window({"a","b"}, {"a","c"}); CHECK(!r); }
    { auto r = min_window({"a","b","a","b"}, {"a","b"}); CHECK(r && r->begin == 0 && r->end == 2); }
    { auto r = min_window({"z","q","z"}, {"z"}); CHECK(r && r->begin == 0 && r->end == 1); }
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
