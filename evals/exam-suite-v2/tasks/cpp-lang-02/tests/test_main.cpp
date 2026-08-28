#include "../solution.h"
#include <cstdio>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    CHECK(render(std::vector<int>{1, 2, 3}) == "1, 2, 3");
    CHECK(render(std::vector<int>{}) == "");
    CHECK(render(std::vector<long>{7}) == "7");
    CHECK(render(std::vector<double>{1.5, 2.0}) == "1.500000, 2.000000");
    CHECK(render(std::vector<std::string>{"a", "b"}) == "\"a\", \"b\"");
    // Раскомментирование следующей строки должно давать ошибку компиляции "unsupported type":
    // CHECK(render(std::vector<char>{'x'}) == "x");
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
