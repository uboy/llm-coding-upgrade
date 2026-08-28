#include "../solution.h"
#include <cstdio>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    { auto r = check_numbers({"G123-45"}); CHECK(r.valid.size() == 1 && r.invalid.empty()); }
    { auto r = check_numbers({"X1-2", "G1", "G1-"}); CHECK(r.valid.empty() && r.invalid.size() == 3); }
    { auto r = check_numbers({"G123-01"}); CHECK(r.invalid.size() == 1); }
    { auto r = check_numbers({"g1-2"}); CHECK(r.invalid.size() == 1); }
    { auto r = check_numbers({"G12-3", "bad", "G123456-78901"}); CHECK(r.valid.size() == 1 && r.invalid.size() == 2); }
    { auto r = check_numbers({}); CHECK(r.valid.empty() && r.invalid.empty()); }
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
