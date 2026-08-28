#include "solution.h"
#include <cctype>

bool valid_inventory(const std::string& code) {
    if (code.size() != 10) return false;
    int sum = 0;
    for (size_t i = 0; i < 9; ++i) {
        if (!std::isdigit(static_cast<unsigned char>(code[i]))) return false;
        sum += (code[i] - '0') * static_cast<int>(10 - i);
    }
    int rem = sum % 11;
    char expected = rem == 10 ? 'X' : static_cast<char>('0' + rem);
    return std::toupper(static_cast<unsigned char>(code[9])) == expected;
}
