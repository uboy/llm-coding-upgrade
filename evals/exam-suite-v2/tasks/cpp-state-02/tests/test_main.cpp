#include "../solution.h"
#include <cstdio>
#include <stdexcept>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    { TokenBucket b(2, 5); CHECK(b.tokens() == 5); }
    { TokenBucket b(2, 3); CHECK(b.allow() && b.allow() && b.allow()); CHECK(!b.allow()); }
    { TokenBucket b(5, 4); b.allow(4); b.tick(); b.tick(); CHECK(b.tokens() == 4); }
    { TokenBucket b(0, 10); CHECK(b.allow(7)); CHECK(!b.allow(7)); CHECK(b.allow(3)); }
    { bool threw = false; try { TokenBucket(1, 5).allow(0); } catch (const std::invalid_argument&) { threw = true; } CHECK(threw); }
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
