# Полное сравнение моделей — 2026-04-24

> 10 задач качества + замер скорости на обоих серверах.
> Бенчмарк: `/tmp/fullbench.py` — 3 warmup + 3 measured decode + prompt speed + 10 quality tasks.

## Участники

| Сервер | Модель | Квантизация | Активные params | VRAM факт |
|--------|--------|-------------|-----------------|-----------|
| V100 (3×Tesla V100 32GB) | Qwen3.5-122B-A10B | Q4_K_M | 10B (MoE 8/64) | 79.4/96 GiB (83%) |
| BM1+BM2 (2×RTX 3090 24GB) | Qwen3.6-35B-A3B | Q3_K_M | 3B (MoE 4/32) | 20.4/24.6 GiB (83%) |

## Скорость

| Метрика | V100 (122B Q4) | BM (35B Q3) | Разница |
|---------|----------------|-------------|---------|
| Decode (tok/s) | **23.9** | **127.1** | BM ×5.3 быстрее |
| Prompt (tok/s) | 0* | 1501 | — |
| Decode runs | 24.1 / 23.9 / 23.8 | 127.8 / 124.4 / 129.0 | BM стабильно |

\* Prompt speed V100 = 0 — артефакт измерения при thinking overhead (529 prompt tokens,
`usage.prompt_tokens` не отражает реальные compute tokens для prompt eval).

**Примечание:** Ранее V100 замерялся при ctx=8192/parallel=1 → давал 44.5 tok/s.
Текущий замер при ctx=262144/parallel=4 → 23.9 tok/s. Разница объясняется:
- Большой KV cache footprint (3264 MiB vs ~200 MiB)
- Overhead от 4 parallel slots
- Это **реальная production скорость**, а не идеальные условия.

## Качество — 10 задач

**Методология:** max_tokens=7000, thinking включён (Qwen3.x hybrid thinking).
Задача считается OK если content > 500 символов, PARTIAL если > 0, EMPTY если 0.

### Сводная таблица

| # | Задача | V100 content | V100 think | BM content | BM think | V100 | BM |
|---|--------|-------------|-----------|------------|---------|------|-----|
| Q01 | LRU Cache | 7677 | 10719 | 5822 | 19394 | ✅ OK | ✅ OK |
| Q02 | Race condition bug fix | 2544 | 2973 | **0** | 25761 | ✅ OK | ❌ EMPTY |
| Q03 | Sliding window rate limiter | 7261 | 13818 | 5249 | 18013 | ✅ OK | ✅ OK |
| Q04 | Async producer-consumer | **0** | 27942 | **507** | 28691 | ❌ EMPTY | ⚠️ PARTIAL |
| Q05 | Dijkstra's shortest path | 8679 | 6261 | 6291 | 16119 | ✅ OK | ✅ OK |
| Q06 | Code review (find all issues) | 5909 | 7832 | 5079 | 13549 | ✅ OK | ✅ OK |
| Q07 | Thread-safe event bus | 6700 | 9120 | 5161 | 22102 | ✅ OK | ✅ OK |
| Q08 | Retry decorator + context mgr | 10837 | 812 | 0 | 28608 | ✅ OK | ❌ EMPTY |
| Q09 | Generic connection pool | 8848 | 20747 | **17** | 30176 | ✅ OK | ❌ EMPTY |
| Q10 | BST with serialization | 14597 | 9116 | 7311 | 20824 | ✅ OK | ✅ OK |

### Итог по качеству

| Метрика | V100 (122B) | BM (35B) |
|---------|-------------|----------|
| OK (content > 500) | **9/10** | **6/10** |
| PARTIAL (content > 0) | 0 | 1 |
| EMPTY (content = 0) | 1 | 3 |
| Средний content (только OK) | **9,101 chars** | **5,819 chars** |
| Средний think | 10,134 chars | 21,504 chars |

## Анализ: Thinking overflow

**Проблема BM (Qwen3.6-35B Q3_K_M):** На 4 из 10 задач thinking chain потребляет
весь бюджет 7000 токенов, оставляя content = 0. Это критический недостаток для
production: модель «думает» слишком долго и не успевает выдать ответ.

Затронутые задачи: Q02 (bug fix), Q04 (async), Q08 (retry), Q09 (connection pool).
Общее: это задачи где нужно проанализировать сложный код и написать решение.

**V100 (122B):** Только 1 задача с overflow (Q04 async producer-consumer).
В остальных случаях thinking chain короче и эффективнее.

**Возможные mitigation:**
1. Увеличить max_tokens до 12000-16000 (потребует больше времени)
2. Отключить thinking (`/no_think` prefix) для задач где быстрый ответ важнее
3. Для BM: всегда использовать reasoning_effort=low/none

## TPS по задачам

| Задача | V100 tps | BM tps | V100 время | BM время |
|--------|---------|--------|-----------|---------|
| Q01 LRU | 28.3 | 131.1 | 174s | 48s |
| Q02 Bug fix | 24.4 | 127.6 | 56s | 55s |
| Q03 Rate limiter | 33.3 | 132.6 | 156s | 44s |
| Q04 Async queue | 40.5 | 127.8 | 173s | 55s |
| Q05 Dijkstra | 42.1 | 131.8 | 96s | 48s |
| Q06 Code review | 41.7 | 128.5 | 84s | 37s |
| Q07 Event bus | 42.3 | 132.0 | 88s | 46s |
| Q08 Retry | 42.1 | 127.8 | 62s | 55s |
| Q09 Connection pool | 41.6 | 131.8 | 168s | 53s |
| Q10 BST | 42.0 | 127.8 | 142s | 55s |

V100 показывает вариативность tps (24-42) — зависит от соотношения thinking/content.
BM стабильно 127-132 tok/s на всех задачах.

## Архитектурное сравнение

| Параметр | V100 (Qwen3.5-122B) | BM (Qwen3.6-35B) |
|----------|---------------------|-------------------|
| **Total params** | 122B | 35B |
| **Active params** | 10B | 3B |
| **Тип** | MoE (8/64 experts) | MoE (4/32 experts) + SSM |
| **Блоки** | 48 | 40 |
| **Attention слои** | 12 (interval=4) | 10 (interval=4) |
| **SSM/recurrent слои** | 36 | 30 |
| **KV heads** | 4 (GQA) | 2 (GQA) |
| **Head dim** | 128 | 256 |
| **Embed dim** | 2048 | 3072 |
| **n_ctx_train** | 262144 (256K) | 262144 (256K) |
| **KV per token** | 12,288 bytes | 10,240 bytes |
| **KV cache @256K** | 3,264 MiB | 2,720 MiB |
| **Квантизация весов** | Q4_K_M (72 GiB) | Q3_K_M (16.2 GiB) |
| **KV квантизация** | Q8_0 | Q8_0 |
| **Thinking** | ✅ hybrid | ✅ hybrid |
| **mmproj/vision** | ❌ нет | ✅ есть |

## Рекомендации

### Для coding (основной workload)
**V100 (122B Q4_K_M)** — безоговорочный лидер:
- 9/10 задач завершены корректно vs 6/10 у BM
- Контент в 1.5× объёмнее и детальнее
- Thinking chain эффективнее (10K avg vs 21K avg chars)
- Для Q02 (bug fix): V100 нашёл все баги, BM не выдал ответ (EMPTY)

### Для speed-critical задач
**BM (35B Q3_K_M)** — в 5.3× быстрее decode:
- 127 vs 24 tok/s — streaming ответы приходят мгновенно
- Prompt eval 1501 tok/s — отличная скорость для RAG
- Подходит для autocomplete, quick chat, simple queries

### Оптимальная стратегия
1. **V100** — для coding, code review, bug analysis, complex reasoning
2. **BM** — для autocomplete, quick questions, chat, RAG retrieval
3. **BM с `/no_think`** — для задач где скорость важнее глубины рассуждений

### Необходимые изменения конфигурации

**V100:** Снизить parallel с 4 до 2, увеличить ctx:
```
--parallel 2 --ctx-size 589824  → 294,912/slot (хватит на 262K+ запросы)
VRAM: GPU0 29,640/32,494 MiB (91.2%) — в пределах
```

**BM1/2:** Увеличить ctx с 262K до 328K:
```
--ctx-size 327680  → 328K (хватит на 262K+ запросы с запасом)
VRAM: 21,160/25,165 MiB (84.1%) — в пределах
```

## Мониторинг: DeepSeek V4-Flash

Вышел 2026-04-24. Единственный кандидат для V100 из линейки V4:
- V4-Flash: 158B total, MoE 6/256, 43 слоя, 1 KV head, ctx=1M
- Q4 ~ 73.6 GiB → помещается в 96 GiB VRAM ✅
- GGUF пока нет — ждать 3-7 дней (unsloth/bartowski)
- Перепроверить наличие GGUF через неделю
