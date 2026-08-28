#pragma once
#include <map>
#include <string>
#include <vector>
// Формат "Талка": первая строка - заголовок; разделитель ',' или ';' (детект по первой строке:
// чего больше); кавычки с "" внутри; пустые строки (вне кавычек) пропускаются.
// Вернуть вектор строк-данных как map{заголовок -> значение}. Все значения - строки.
std::vector<std::map<std::string, std::string>> parse_talka(const std::string& text);
