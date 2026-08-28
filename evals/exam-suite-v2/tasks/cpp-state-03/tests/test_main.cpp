#include "../solution.h"
#include <cstdio>
#include <stdexcept>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    CHECK(IntBuffer::live_buffers() == 0);
    {
        IntBuffer a(4);
        CHECK(IntBuffer::live_buffers() == 1);
        a.at(2) = 7;
        CHECK(a.at(2) == 7);
        CHECK(a.size() == 4);
        IntBuffer b(std::move(a));
        CHECK(IntBuffer::live_buffers() == 1);
        CHECK(b.at(2) == 7);
        CHECK(a.size() == 0);
        bool threw = false;
        try { a.at(0); } catch (const std::out_of_range&) { threw = true; }
        CHECK(threw);
        b = IntBuffer(1);
        CHECK(IntBuffer::live_buffers() == 1);
    }
    CHECK(IntBuffer::live_buffers() == 0);
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
