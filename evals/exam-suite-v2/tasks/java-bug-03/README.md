# Баг: имя месяца "Лунник" (Java)

Task.java: `public static String monthName(String isoDate)` - из "YYYY-MM-DD" имя месяца по-русски (именительный). Баг: используется java.util.Calendar с конструктором new GregorianCalendar(year, month, day), где месяц передан как число из строки БЕЗ поправки на нулевой базовый месяц Calendar (0 = январь). Вдобавок день 0-базовый. Почини (используй java.time.LocalDate.parse или поправь индексы). Неверный формат/несуществующая дата - IllegalArgumentException.
