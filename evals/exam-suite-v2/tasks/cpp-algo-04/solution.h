#pragma once
#include <optional>
#include <string>
#include <utility>
#include <vector>
struct Span { int begin; int end; }; // полуоткрытый [begin, end)
// Кратчайший [i, j), покрывающий каждый тег required хотя бы раз; при равной длине - меньший i.
// Пустой required - {0, 0}. Нет покрытия - nullopt.
std::optional<Span> min_window(const std::vector<std::string>& events, const std::vector<std::string>& required);
