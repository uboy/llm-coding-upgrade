#include "solution.h"
#include <map>

std::optional<Span> min_window(const std::vector<std::string>& events, const std::vector<std::string>& required) {
    if (required.empty()) return Span{0, 0};
    std::map<std::string, long> need;
    for (const auto& t : required) need[t] += 1;
    long missing = static_cast<long>(required.size());
    std::optional<Span> best;
    size_t i = 0;
    for (size_t j = 0; j < events.size(); ++j) {
        auto it = need.find(events[j]);
        if (it != need.end()) {
            if (it->second > 0) --missing;
            it->second -= 1;
        }
        while (missing == 0) {
            long len = static_cast<long>(j + 1 - i);
            if (!best || len < best->end - best->begin) best = Span{static_cast<int>(i), static_cast<int>(j + 1)};
            auto it2 = need.find(events[i]);
            if (it2 != need.end()) {
                it2->second += 1;
                if (it2->second > 0) ++missing;
            }
            ++i;
        }
    }
    return best;
}
