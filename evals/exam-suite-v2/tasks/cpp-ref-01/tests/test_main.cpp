#include "../solution.h"
#include <cstdio>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    CHECK(report({}) == "sum=0;max=0;avg=0");
    CHECK(report({5}) == "sum=5;max=5;avg=5");
    CHECK(report({1, 2, 3}) == "sum=6;max=3;avg=2");
    CHECK(report({-4, 4}) == "sum=0;max=4;avg=0");
    CHECK(report({7, 7}) == "sum=14;max=7;avg=7");
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
