# Баг: счётчик вхождений "Ловец" (Java)

Task.java: `public static int countOverlapping(String haystack, String needle)` - число вхождений needle в haystack С ПЕРЕКРЫТИЕМ ("aaa" / "aa" -> 2). Баг: после найденного вхождения индекс сдвигается на длину needle (без перекрытия) и теряются соседние. Почини, сигнатуру не менять. Пустая needle - 0.
