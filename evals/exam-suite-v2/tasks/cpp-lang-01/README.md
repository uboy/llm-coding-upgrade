# RAII-файл "Секретарь" (C++)

solution.h менять нельзя. Реализуй FileGuard в solution.cpp: move-семантика (перемещённый объект теряет файл), деструктор закрывает, write без открытого файла — std::runtime_error.
