#include "../solution.h"
#include <cstdio>
#include <stdexcept>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    Buffer a(2);
    a.byte(0) = 1;
    Buffer b(a);
    CHECK(b.byte(0) == 1);
    b.byte(0) = 9;
    CHECK(a.byte(0) == 1);
    CHECK(b.byte(0) == 9);
    Buffer c(1);
    c = a;
    c.byte(1) = 5;
    CHECK(a.byte(1) == 0);
    bool threw = false;
    try { Buffer(1).byte(1); } catch (const std::out_of_range&) { threw = true; }
    CHECK(threw);
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
