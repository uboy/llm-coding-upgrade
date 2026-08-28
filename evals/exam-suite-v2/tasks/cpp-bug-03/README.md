# Баг: trim "Аппрет" (C++)

solution.h менять нельзя. Реализация в solution.cpp падает (std::out_of_range от substr(npos)) на строках целиком из пробелов: find_first_not_of возвращает npos, а код это не различает. Исправь.
