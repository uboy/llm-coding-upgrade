#include "../solution.h"
#include <cstdio>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    { auto r = parse_talka("a,b\n1,2\n"); CHECK(r.size() == 1 && r[0].at("a") == "1" && r[0].at("b") == "2"); }
    { auto r = parse_talka("a;b\n1;2"); CHECK(r.size() == 1 && r[0].at("a") == "1"); }
    { auto r = parse_talka("a,b\n\"x\",\"y\""); CHECK(r[0].at("a") == "x" && r[0].at("b") == "y"); }
    { auto r = parse_talka("a\n\"say \"\"hi\"\"\"\n"); CHECK(r[0].at("a") == "say \"hi\""); }
    { auto r = parse_talka("a\n\n1\n\n"); CHECK(r.size() == 1 && r[0].at("a") == "1"); }
    { auto r = parse_talka(""); CHECK(r.empty()); }
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
