#include "../solution.h"
#include <cstdio>
#include <stdexcept>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)
#define CHECK_THROWS(expr) do { bool _t = false; try { (void)(expr); } catch (const std::invalid_argument&) { _t = true; } CHECK(_t); } while (0)

int main() {
    CHECK(parse_duration("1d") == 86400);
    CHECK(parse_duration("2h30m") == 9000);
    CHECK(parse_duration("1d2h3m4s") == 86400 + 7200 + 180 + 4);
    CHECK(parse_duration("59s") == 59);
    CHECK_THROWS(parse_duration(""));
    CHECK_THROWS(parse_duration("1d1d"));
    CHECK_THROWS(parse_duration("3h2d"));
    CHECK_THROWS(parse_duration("24h"));
    CHECK_THROWS(parse_duration("60m"));
    CHECK_THROWS(parse_duration("0s"));
    CHECK_THROWS(parse_duration("01s"));
    CHECK_THROWS(parse_duration("1 s"));
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
