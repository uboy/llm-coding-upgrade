#include "../solution.h"
#include <cstdio>
#include <stdexcept>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    CHECK(calc("light", 10) == 0);
    CHECK(calc("light", 40) == 1500);
    CHECK(calc("standard", 150) == 5000);
    CHECK(calc("premium", 400) == 8000);
    CHECK(calc("light", 0) == 0);
    CHECK(!PLANS.empty() && PLANS.at("light").first == 30);
    { bool threw = false; try { calc("ultra", 10); } catch (const std::invalid_argument&) { threw = true; } CHECK(threw); }
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
