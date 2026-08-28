#include "solution.h"
#include <cctype>
#include <stdexcept>

int64_t parse_duration(const std::string& s) {
    if (s.empty()) throw std::invalid_argument("empty");
    static const int order[4] = {'d', 'h', 'm', 's'};
    static const int64_t mul[4] = {86400, 3600, 60, 1};
    static const int maxv[4] = {0, 23, 59, 59};
    int prev_unit = -1;
    int64_t total = 0;
    size_t i = 0;
    while (i < s.size()) {
        if (!std::isdigit(static_cast<unsigned char>(s[i]))) throw std::invalid_argument("digit expected");
        int64_t num = 0;
        bool leading_zero = false;
        if (s[i] == '0') leading_zero = true;
        while (i < s.size() && std::isdigit(static_cast<unsigned char>(s[i]))) {
            num = num * 10 + (s[i] - '0');
            ++i;
        }
        if (num == 0 || (leading_zero && num != 0)) throw std::invalid_argument("bad number");
        if (i >= s.size()) throw std::invalid_argument("unit expected");
        char unit = s[i++];
        int ui = -1;
        for (int k = 0; k < 4; ++k) if (order[k] == unit) ui = k;
        if (ui == -1) throw std::invalid_argument("bad unit");
        if (prev_unit != -1 && ui <= prev_unit) throw std::invalid_argument("unit order");
        if (maxv[ui] != 0 && num > maxv[ui]) throw std::invalid_argument("unit range");
        total += num * mul[ui];
        prev_unit = ui;
    }
    return total;
}
