# Длительность "Хронос" (Java)

Класс Task: `public static long parseDuration(String s)` — те же правила, что в C++-варианте: единицы d/h/m/s, положительные целые без ведущих нулей, строго в порядке d>h>m>s, каждая один раз, h<=23, m<=59, s<=59; нарушение - IllegalArgumentException. Итог в секундах.
