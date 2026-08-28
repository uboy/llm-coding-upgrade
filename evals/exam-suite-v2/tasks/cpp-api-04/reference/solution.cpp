#include "solution.h"
#include <cctype>

namespace {
bool digits(const std::string& s, size_t from, size_t to, size_t min_d, size_t max_d) {
    size_t n = to - from;
    if (n < min_d || n > max_d) return false;
    for (size_t i = from; i < to; ++i)
        if (!std::isdigit(static_cast<unsigned char>(s[i]))) return false;
    return true;
}
} // namespace

PhoneReport check_numbers(const std::vector<std::string>& numbers) {
    PhoneReport r;
    for (const auto& n : numbers) {
        size_t dash = n.find('-');
        bool ok = n.size() >= 5 && n[0] == 'G' && dash != std::string::npos;
        if (ok) ok = digits(n, 1, dash, 2, 6);
        if (ok) ok = digits(n, dash + 1, n.size(), 1, 4);
        if (ok) ok = n[dash + 1] != '0';
        if (ok) r.valid.push_back(n);
        else r.invalid.push_back(n);
    }
    return r;
}
