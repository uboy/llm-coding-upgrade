#include "solution.h"
#include <algorithm>
#include <numeric>

std::string report(const std::vector<int>& v) {
    const long long sum = std::accumulate(v.begin(), v.end(), 0LL);
    const int max = v.empty() ? 0 : *std::max_element(v.begin(), v.end());
    const long long avg = v.empty() ? 0 : sum / static_cast<long long>(v.size());
    return "sum=" + std::to_string(sum) + ";max=" + std::to_string(max) +
           ";avg=" + std::to_string(avg);
}
