#include "solution.h"
#include <stdexcept>

const std::map<std::string, std::pair<long long, long long>> PLANS = {
    {"light", {30, 150}}, {"standard", {100, 100}}, {"premium", {300, 80}},
};

long long calc(const std::string& plan, long long minutes) {
    if (plan == "light") {
        if (minutes <= 30) return 0;
        return (minutes - 30) * 150;
    } else if (plan == "standard") {
        if (minutes <= 100) return 0;
        return (minutes - 100) * 100;
    } else if (plan == "premium") {
        if (minutes <= 300) return 0;
        return (minutes - 300) * 80;
    }
    throw std::invalid_argument("plan");
}
