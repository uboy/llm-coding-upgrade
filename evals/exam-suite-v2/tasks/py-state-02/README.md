# Ведро заявок "Порцион"

Класс `TokenBucket(rate: int, burst: int)` — burst токенов, пополняется на `rate` токенов за каждый вызов `tick()` (не больше burst).

- `tick()` — пополнение;
- `allow(cost: int = 1) -> bool` — если токенов >= cost, списать и True, иначе False (без списания);
- `tokens` — текущее число токенов (float до burst).

Старт: ровно burst токенов. cost <= 0 — ValueError.
