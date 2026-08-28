#include "solution.h"
#include <algorithm>
#include <stdexcept>

std::optional<Interval> first_free_slot(const std::vector<Interval>& busy, int duration, int day_start, int day_end) {
    if (duration <= 0) throw std::invalid_argument("duration");
    std::vector<Interval> iv;
    for (const auto& p : busy) if (p.end > p.start) iv.push_back(p);
    std::sort(iv.begin(), iv.end(), [](const Interval& a, const Interval& b) { return a.start < b.start; });
    std::vector<Interval> merged;
    for (const auto& p : iv) {
        if (!merged.empty() && p.start <= merged.back().end) merged.back().end = std::max(merged.back().end, p.end);
        else merged.push_back(p);
    }
    int t = day_start;
    for (const auto& m : merged) {
        if (m.start - t >= duration) return Interval{t, t + duration};
        t = std::max(t, m.end);
    }
    if (day_end - t >= duration) return Interval{t, t + duration};
    return std::nullopt;
}
