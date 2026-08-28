# Ведро заявок "Порцион" (Java)

Класс Task с внутренним классом или отдельным: создай `public static final class TokenBucket` (внутри Task.java):

- конструктор `TokenBucket(long rate, long burst)` — старт: burst токенов;
- `void tick()` — +rate, не выше burst;
- `boolean allow(long cost)` — списывает при достатке (true), иначе false без списания; cost <= 0 — IllegalArgumentException;
- `long tokens()`.

Файл Task.java с `class Task { public static final class TokenBucket {...} }`; TestMain обращается Task.TokenBucket.
