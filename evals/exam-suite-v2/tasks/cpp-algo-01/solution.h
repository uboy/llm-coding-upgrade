#pragma once
#include <optional>
#include <vector>
struct Interval { int start; int end; };
// Самый ранний [t, t+duration], свободный внутри [day_start, day_end); нет - std::nullopt.
// duration <= 0 - std::invalid_argument. Слоты нулевой длины занятостью не считаются.
std::optional<Interval> first_free_slot(const std::vector<Interval>& busy, int duration, int day_start, int day_end);
