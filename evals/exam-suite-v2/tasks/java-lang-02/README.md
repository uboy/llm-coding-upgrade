# Обобщения "Сортировщик" (Java)

Task.java, два статических обобщённых метода:
1. `public static <T extends Comparable<? super T>> T minOf(java.util.List<T> items)` — минимум; пустой список - IllegalArgumentException.
2. `public static <T> T minOf(java.util.List<T> items, java.util.Comparator<? super T> cmp)` — минимум по компаратору; пустой - IllegalArgumentException.

Тесты: Integer/String (естественный порядок) и компаратор наоборот (reverseOrder).
