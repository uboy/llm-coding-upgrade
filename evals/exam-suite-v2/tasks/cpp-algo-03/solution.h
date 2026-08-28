#pragma once
#include <map>
#include <string>
#include <vector>
// deps: блюдо -> что должно быть готово раньше. Вернуть ВСЕ узлы (включая листья) в порядке
// приготовления; при равных возможностях - лексикографически минимальный (std::string<).
// Цикл - std::invalid_argument.
std::vector<std::string> cooking_order(const std::map<std::string, std::vector<std::string>>& deps);
