# LRU "Антиквар" (Java)

Task.java: `public static final class LRUCache`:
- конструктор LRUCache(int capacity);
- `get(String key)` / `put(String key, String value)`; вытеснение LRU при переполнении; put существующего обновляет без роста;
- `int size()`; `java.util.List<String> keys()` — от свежих к старым;
- слушатель вытеснения: конструктор `LRUCache(int capacity, java.util.function.BiConsumer<String, String> onEvict)` (вызывается с key/value).
