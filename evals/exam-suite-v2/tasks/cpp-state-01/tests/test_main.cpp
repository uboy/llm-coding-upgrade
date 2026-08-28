#include "../solution.h"
#include <cstdio>
#include <stdexcept>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    { RingBuffer r(3); r.push(1); r.push(2); CHECK((r.snapshot() == std::vector<int>{1, 2})); }
    { RingBuffer r(3); for (int x : {1,2,3,4}) r.push(x); CHECK((r.snapshot() == std::vector<int>{2,3,4})); CHECK(r.last() == 4); }
    { RingBuffer r(2); for (int x : {1,2,3,4,5}) r.push(x); CHECK((r.snapshot() == std::vector<int>{4,5})); CHECK(r.last() == 5); }
    { bool threw = false; try { RingBuffer(2).last(); } catch (const std::out_of_range&) { threw = true; } CHECK(threw); }
    { bool threw = false; try { RingBuffer r(0); r.push(1); } catch (const std::invalid_argument&) { threw = true; } CHECK(threw); }
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
