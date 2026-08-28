#include "../solution.h"
#include <cstdio>
static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
    // 10*0+9*4+8*5+7*2+6*3+5*1+4*7+3*6+2*0 = 159; 159 % 11 = 5 -> контрольная "5"
    CHECK(valid_inventory("0452317605"));
    CHECK(valid_inventory("0435172601") == false);
    CHECK(valid_inventory("0452317605X") == false); // длина 11
    CHECK(valid_inventory("045231760") == false);   // длина 9
    // 10+9+8+7+6+5+4+3+2 = 54; 54 % 11 = 10 -> контрольная 'X'
    CHECK(valid_inventory("111111111X"));
    CHECK(valid_inventory("111111111x")); // регистр контрольной не важен
    CHECK(valid_inventory("1111111110") == false);
    CHECK(valid_inventory("A452317601") == false); // буква в числовой части
    if (failures) { std::printf("%d failures\n", failures); return 1; }
    std::printf("OK\n"); return 0;
}
