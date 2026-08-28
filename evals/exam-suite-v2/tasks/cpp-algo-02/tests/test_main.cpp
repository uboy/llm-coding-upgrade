#include "../solution.h"
#include <cstdio>
#include <stdexcept>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)
#define CHECK_THROWS(expr) do { bool _t = false; try { (void)(expr); } catch (const std::invalid_argument&) { _t = true; } CHECK(_t); } while (0)

int main() {
    CHECK(decode_beacon("3a2b#5") == "aaabb");
    CHECK(decode_beacon("3a!#4") == "aaaa");
    CHECK(decode_beacon("12x#12") == std::string(12, 'x'));
    CHECK(decode_beacon("1a!!#3") == "aaa");
    CHECK_THROWS(decode_beacon("3a"));
    CHECK_THROWS(decode_beacon("3a#4"));
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
