#pragma once
#include <string>
#include <vector>
struct PhoneReport {
    std::vector<std::string> valid;      // валидные как есть
    std::vector<std::string> invalid;    // в порядке входа
};
// Номер "Гранит-фон": 'G' + 2..6 цифр + '-' + 1..4 цифр, 'G' строго верхний.
// Вторая группа не может начинаться с '0'. Вернуть валидные и невалидные (в порядке входа).
PhoneReport check_numbers(const std::vector<std::string>& numbers);
