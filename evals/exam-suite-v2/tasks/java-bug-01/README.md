# Баг: кэш заказов "Переплёт" (Java)

Task.java содержит `public static boolean sameOrder(Integer a, Integer b)` - сравнивает номера заказов. Классический баг: сравнение Integer через == работает до 127 и ломается с 128+ (кэш бокса). Почини (equals), не меняя сигнатуру. Второй метод `public static int countMatches(java.util.List<Integer> orders, Integer probe)` - считает, сколько заказов равны probe (должен использовать sameOrder и работать на любых значениях).
