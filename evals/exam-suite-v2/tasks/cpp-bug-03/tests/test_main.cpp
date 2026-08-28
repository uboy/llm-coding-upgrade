#include "../solution.h"
#include <cstdio>
#include <stdexcept>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    CHECK(trim("  x  ") == "x");
    CHECK(trim("\tx") == "x");
    CHECK(trim("x\t ") == "x");
    CHECK(trim("x") == "x");
    CHECK(trim("") == "");
    CHECK(trim("   ") == "");
    CHECK(trim("\t \t") == "");
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
