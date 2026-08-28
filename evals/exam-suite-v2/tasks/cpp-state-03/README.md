# Move-only буфер "Копилка" (C++)

solution.h менять нельзя. Реализуй IntBuffer в solution.cpp (внутренний буфер через new[]/delete[], счётчик живых аллокаций - статический). Перемещённый объект: size() == 0, at() кидает out_of_range.
