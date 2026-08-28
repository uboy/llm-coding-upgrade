# Порядок блюд шефа (Java)

Класс Task: `public static java.util.List<String> cookingOrder(java.util.Map<String, java.util.List<String>> deps)`

Все узлы (включая листья) в порядке приготовления; при равных возможностях - лексикографически минимальный (String.compareTo). Цикл - IllegalArgumentException.
