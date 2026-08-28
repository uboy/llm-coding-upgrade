#include "../solution.h"
#include <cstdio>
#include <stdexcept>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    { auto r = first_free_slot({{60, 120}}, 30, 0, 240); CHECK(r && r->start == 0 && r->end == 30); }
    { auto r = first_free_slot({{0, 60}, {90, 240}}, 30, 0, 240); CHECK(r && r->start == 60 && r->end == 90); }
    { auto r = first_free_slot({{0, 100}, {50, 150}}, 50, 0, 240); CHECK(r && r->start == 150 && r->end == 200); }
    { auto r = first_free_slot({{0, 240}}, 10, 0, 240); CHECK(!r); }
    { auto r = first_free_slot({{30, 30}}, 40, 0, 100); CHECK(r && r->start == 0 && r->end == 40); }
    { auto r = first_free_slot({}, 10, 0, 100); CHECK(r && r->start == 0 && r->end == 10); }
    bool threw = false;
    try { first_free_slot({}, 0, 0, 100); } catch (const std::invalid_argument&) { threw = true; }
    CHECK(threw);
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n");
    return 0;
}
