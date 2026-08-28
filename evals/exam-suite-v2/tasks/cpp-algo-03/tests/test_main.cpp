#include "../solution.h"
#include <cstdio>
#include <stdexcept>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    CHECK((cooking_order({{"b", {"a"}}, {"a", {}}}) == std::vector<std::string>{"a", "b"}));
    CHECK((cooking_order({{"z", {}}, {"a", {}}, {"m", {"a"}}}) == std::vector<std::string>{"a", "m", "z"}));
    {
        auto got = cooking_order({{"d", {"b", "c"}}, {"b", {"a"}}, {"c", {"a"}}, {"a", {}}});
        CHECK(got.size() == 4);
        size_t ia = 0, ib = 0, ic = 0, id = 0;
        for (size_t k = 0; k < 4; ++k) {
            if (got[k] == "a") ia = k; if (got[k] == "b") ib = k;
            if (got[k] == "c") ic = k; if (got[k] == "d") id = k;
        }
        CHECK(ia < ib && ia < ic && ib < id && ic < id);
    }
    { bool threw = false; try { cooking_order({{"a", {"b"}}, {"b", {"a"}}}); } catch (const std::invalid_argument&) { threw = true; } CHECK(threw); }
    CHECK((cooking_order({{"a", {"x"}}}) == std::vector<std::string>{"x", "a"}));
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
