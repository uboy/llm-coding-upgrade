# Гроссбух "Счёт-Копейка" (Java)

Класс Task: `public static java.util.Map<String, Long> balance(java.util.List<String> entries)` (и второй метод `skipped` не нужен - верни оба из одного:

`public static java.util.Map<String, Object> process(java.util.List<String> entries)` с ключами "balances" (Map<String,Long>) и "skipped" (List<String>).

Строка: "<dd.mm.yyyy>|<account>|<D|C>|<amount>", amount - целые копейки без знака; D уменьшает, C увеличивает. Неверные записи (формат, дата, тип, отрицательное/нецелое) - в skipped как есть. Високосность учитывать.
