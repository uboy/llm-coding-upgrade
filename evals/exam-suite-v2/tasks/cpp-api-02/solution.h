#pragma once
#include <cstdint>
#include <string>
// Длительность "1d2h3m4s": единицы d/h/m/s, значение - положительное целое без ведущих нулей,
// единицы строго в порядке d > h > m > s, каждая максимум один раз, значение в h <= 23,
// m <= 59, s <= 59. Пробелы не допускаются. Итог - секунды. Нарушения - std::invalid_argument.
int64_t parse_duration(const std::string& s);
