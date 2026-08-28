#pragma once
#include <map>
#include <string>
#include <vector>
// Тарифы: light (30 мин вкл, 150 коп/мин сверх), standard (100, 100), premium (300, 80).
// calc(plan, minutes) - сумма в копейках (включённые минуты бесплатны, сверх - по тарифу).
// Итог округляется ВНИЗ до целой копейки. Неизвестный план - std::invalid_argument.
long long calc(const std::string& plan, long long minutes);
extern const std::map<std::string, std::pair<long long, long long>> PLANS; // plan -> {included, коп_за_мин}
