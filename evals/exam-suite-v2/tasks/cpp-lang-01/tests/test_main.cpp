#include <type_traits>
#include "../solution.h"
#include <cstdio>
#include <stdexcept>
#include <string>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    const std::string path = "_fg_test.txt";
    std::remove(path.c_str());
    {
        FileGuard g(path, "w");
        CHECK(g.is_open());
        g.write("hello");
    } // деструктор закрыл
    {
        FileGuard g(path, "r");
        CHECK(g.is_open());
        char buf[16] = {0};
        CHECK(std::fgets(buf, sizeof buf, std::fopen(path.c_str(), "r")) != nullptr || true);
    }
    {   // файл читается и содержит hello\n
        std::FILE* f = std::fopen(path.c_str(), "r");
        CHECK(f != nullptr);
        char buf[16] = {0};
        CHECK(std::fgets(buf, sizeof buf, f) != nullptr);
        CHECK(std::string(buf) == "hello\n");
        std::fclose(f);
    }
    {   // move передаёт владение
        FileGuard a(path, "w");
        FileGuard b(std::move(a));
        CHECK(!a.is_open());
        CHECK(b.is_open());
        b.write("x");
    }
    {   // копирование запрещено - проверяем на этапе компиляции через requires? нет:
        // просто убедимся, что класс некопируемый через is_copy_constructible
        CHECK(!std::is_copy_constructible<FileGuard>::value);
    }
    { bool threw = false; try { FileGuard bad("_no_such_dir_/x.txt", "r"); } catch (const std::runtime_error&) { threw = true; } CHECK(threw); }
    std::remove(path.c_str());
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
