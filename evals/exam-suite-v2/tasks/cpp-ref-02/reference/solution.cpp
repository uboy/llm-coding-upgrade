#include "solution.h"
#include <stdexcept>

const std::map<std::string, std::pair<long long, long long>> PLANS = {
    {"light", {30, 150}}, {"standard", {100, 100}}, {"premium", {300, 80}},
};

long long calc(const std::string& plan, long long minutes) {
    auto it = PLANS.find(plan);
    if (it == PLANS.end()) throw std::invalid_argument("plan");
    const long long over = minutes > it->second.first ? minutes - it->second.first : 0;
    return over * it->second.second;
}
