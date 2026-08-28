#include "../solution.h"
#include <cstdio>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    CHECK((remove_evens({}) == std::vector<int>{}));
    CHECK((remove_evens({1}) == std::vector<int>{1}));
    CHECK((remove_evens({2}) == std::vector<int>{}));
    CHECK((remove_evens({1, 2, 3, 4, 5}) == std::vector<int>{1, 3, 5}));
    CHECK((remove_evens({2, 4, 6}) == std::vector<int>{}));
    CHECK((remove_evens({2, 1, 2, 3, 2}) == std::vector<int>{1, 3}));
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
