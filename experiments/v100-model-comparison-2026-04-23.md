# V100 Model Comparison Report — 2026-04-23

> Цель: найти лучшую замену или дополнение к текущей продакшн модели на V100.
> Железо: 3× Tesla V100 PCIE 32GB = 96 GB VRAM, PCIe Gen3.

---

## Кандидаты и статус

| Модель | Источник | Вердикт | Причина |
|--------|----------|---------|---------|
| Qwen3.5-397B IQ1_M | bartowski GGUF | ⚠️ протестирован | медленнее 122B, хуже качество |
| Qwen3.5-397B IQ2_XXS | bartowski GGUF | ❌ отклонён | CPU spillover 15.6 GiB → 10.3 tok/s |
| Qwen3.5-397B IQ2_XS | bartowski GGUF | ❌ отклонён | CPU spillover 26.3 GiB → 7.76 tok/s |
| unsloth/Qwen3.5-397B-A17B GGUF | unsloth | ❌ пропущен | минимальная квантизация 107 GB > 96 GB |
| **Qwen3.5-122B Q4_K_M** | **unsloth GGUF** | **✅ ЛУЧШИЙ** | скорость + качество + удобный размер |
| Qwen3.5-122B Q5_K_S | unsloth GGUF | ✅ протестирован | чуть хуже по скорости, качество ≈ Q4_K_M |
| Qwen/Qwen3.5-122B-A10B (BF16) | Qwen HF | ❌ не подходит | 244 GiB >> 96 GiB |
| Qwen/Qwen3.5-122B-A10B-FP8 | Qwen HF | ❌ не подходит | FP8 не поддерживается на V100 (Volta) |

---

## Скорость — итоговая таблица

| Модель | Размер (GiB) | VRAM (GiB) | CPU spillover | ngl | Decode tok/s | Prompt tok/s | TTFT (мс) | Thinking |
|--------|-------------|-----------|--------------|-----|-------------|-------------|-----------|---------|
| **Baseline**: Qwen3-Coder-Next Q5_K_S | 52 | 70/96 | 0 | 100 | **71** | 183 | ~200 | ❌ off |
| 122B Q4_K_M (unsloth) | 72 | 70.5/96 | 0 | 49/49 | **44.5** | 128 | ~190 | ✅ on |
| 122B Q5_K_S (unsloth) | 81 | 82.2/96 | 0 | 49/49 | **42.6** | 121 | ~200 | ✅ on |
| 397B IQ1_M (bartowski) | 86 | 87.5/96 | 0 | 60/61 | **29.4** | 43–45 | 411 | ✅ on |
| 397B IQ2_XXS (bartowski) | 100 | 86.7/96 | 15.6 | 52/61 | **10.3** | 36.6 | ~780 | ✅ on |
| 397B IQ2_XS (bartowski) | 111 | 87.3/96 | 26.3 | 47/61 | **7.76** | 28.7 | ~960 | ✅ on |

> Контекст бенчмарка: ctx=8192, Q8_0 KV, параллель=1, 3 warmup + 3 измерения, avg.
> Decode измеряется при max_tokens=200, prompt ≈ 25 токенов.

---

## Качество — coding eval

### Задачи

| № | Задача | Что проверяет |
|---|--------|--------------|
| Q1 | Thread-safe LRU cache (O(1), locking) | Архитектура, data structures, thread safety |
| Q2 | Bug fix: race condition в Counter | Понимание concurrency, поиск тонких багов |
| Q3 | Sliding window rate limiter (per-user) | Design, алгоритм, тесты |

### Результаты качества

#### Q1 — Thread-safe LRU Cache

| Модель | Подход | Thinking | Качество |
|--------|--------|---------|---------|
| Baseline (no thinking) | `OrderedDict` + `RLock` | — | ⭐⭐⭐ корректно, просто |
| **122B Q4_K_M** | Doubly-linked list + `dict` + `Lock` | 1,236 chars | ⭐⭐⭐⭐⭐ полная реализация с sentinel nodes |
| **122B Q5_K_S** | `OrderedDict` + `Lock` + type hints | 2,368 chars | ⭐⭐⭐⭐⭐ развёрнутый ответ с threading tests |
| 397B IQ1_M | Doubly-linked list + `RLock` | 7,435 chars | ⭐⭐⭐⭐ корректно, но verbose мышление |

#### Q2 — Bug Fix (race condition в Counter)

Известные баги в коде:
1. **Race condition** в `increment()` (critical) — все нашли
2. **`get()` не thread-safe** (design) — только 122B нашли
3. **`assert` отключается `-O`** (robustness) — только 122B нашли

| Модель | Багов найдено | Найденные баги | Качество |
|--------|--------------|----------------|---------|
| Baseline | **1/3** | race condition | ⭐⭐ минимум |
| **122B Q4_K_M** | **3/3** | race + get() lock + assert -O | ⭐⭐⭐⭐⭐ все найдены |
| **122B Q5_K_S** | **3/3** | race + get() lock + assert -O | ⭐⭐⭐⭐⭐ все найдены |
| 397B IQ1_M | **1-2/3** | race + "missing sync" (то же самое), assertion как симптом | ⭐⭐ аналогично baseline |

> **Ключевой вывод**: 397B IQ1_M при 1.75 bits/weight находит те же баги, что и baseline без thinking.
> 122B при Q4_K_M/Q5_K_S находит существенно больше благодаря thinking и лучшему качеству квантизации.

#### Q3 — Sliding Window Rate Limiter

| Модель | Алгоритм | Thread-safe | Тесты | Качество |
|--------|---------|------------|-------|---------|
| Baseline (no thinking) | Sliding window log (`deque`) | ❌ не реализовано | ✅ | ⭐⭐⭐ |
| **122B Q4_K_M** | Sliding window log + user dict | ✅ `threading.Lock` | ✅ comprehensive | ⭐⭐⭐⭐⭐ |
| **122B Q5_K_S** | Sliding window log + user dict | ✅ `threading.Lock` | ✅ comprehensive | ⭐⭐⭐⭐⭐ |
| 397B IQ1_M | Sliding window log + injectable `time_func` | ✅ Lock | ✅ + `unittest` | ⭐⭐⭐⭐⭐ тоже хорошо |

---

## Архитектура моделей

| Параметр | 122B-A10B | 397B-A17B |
|----------|-----------|-----------|
| Total params | 122B | 397B |
| Active params | 10B | 17B |
| Block count | 48 | 60 |
| Full attention layers | 12/48 (1/4) | 15/60 (1/4) |
| Experts | 256 / 8 active | 512 / 10 active |
| Embedding dim | 3,072 | 4,096 |
| Context trained | 262,144 | 262,144 |
| Source imatrix | unsloth | bartowski |

---

## Почему 122B > 397B IQ1_M?

### 1. Качество квантизации важнее параметров
- IQ1_M = ~1.75 bits/weight: значительная потеря точности при 397B → итоговое "эффективное" знание может быть ниже, чем 122B при Q4_K_M (4 бита)
- Q4_K_M и Q5_K_S сохраняют достаточно precision для тонкого reasoning

### 2. Скорость
- 122B Q4_K_M: **44.5 tok/s** vs IQ1_M: **29.4 tok/s** → в 1.5× быстрее при лучшем качестве
- Причина: 48 последовательных блоков vs 60 у 397B + меньше байт на токен

### 3. VRAM margin
- 122B Q4_K_M: 70.5/96 GiB → **25.5 GiB свободно** (можно поднять ctx, добавить параллель)
- 397B IQ1_M: 87.5/96 GiB → **8.5 GiB свободно** (почти нет запаса)

---

## Рекомендация

### Для V100 (продакшн)

**Рекомендуется: Qwen3.5-122B-A10B Q4_K_M**

```
Путь: /data/shared/<user>/models/Qwen3.5-122B-A10B-GGUF/Q4_K_M/Qwen3.5-122B-A10B-Q4_K_M-00001-of-00003.gguf
Размер: 72 GiB
VRAM: 70.5/96 GiB (73%)
Decode: 44.5 tok/s
Prompt: 128 tok/s
Thinking: включён по умолчанию (нужен max_tokens ≥ 4000 для coding tasks)
```

**Команда запуска (замена текущего prod):**
```bash
docker stop llamacpp-server-p8001
docker run -d --name llamacpp-server-p8001 \
  --gpus all --restart unless-stopped \
  -v /data/shared/<user>/models:/models \
  -p 8001:8080 \
  ghcr.io/ggml-org/llama.cpp:server-cuda \
  -m /models/Qwen3.5-122B-A10B-GGUF/Q4_K_M/Qwen3.5-122B-A10B-Q4_K_M-00001-of-00003.gguf \
  --host 0.0.0.0 --port 8080 \
  --n-gpu-layers 100 \
  --split-mode layer --tensor-split 1,1,1 \
  --ctx-size 32768 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --parallel 4 \
  --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0 \
  --jinja
```

> Замечание: ctx=32768 вместо 1M (у текущего prod) — 122B с thinking требует больший ctx для полных ответов на coding задачи, но 1M потребовало бы больше VRAM для KV (хотя при hybrid SSM это умеренно).

### Альтернативы

| Вариант | Когда выбрать |
|---------|--------------|
| Qwen3-Coder-Next Q5_K_S (текущий) | Максимальная скорость (71 tok/s), reasoning off, огромный ctx (1M), кодинг без thinking |
| 122B Q5_K_S | Если Q4_K_M заметно теряет качество на конкретных задачах (–4% скорость, +12% VRAM) |
| 397B IQ1_M | Только если нужна максимальная "ширина знаний" (397B параметров), готовы мириться с 29 tok/s |

### Не рекомендуется

- **397B IQ2+**: CPU spillover → критическое падение скорости (7-10 tok/s)
- **Qwen/122B-FP8**: V100 не поддерживает FP8 hardware
- **Qwen/122B-BF16**: 244 GiB не влезет

---

## MiniMax-M2.7 UD-IQ3_S — дополнительное тестирование (2026-04-23)

> Цель: проверить не-Qwen альтернативу для V100.

### Архитектура MiniMax-M2.7

| Параметр | Значение |
|----------|---------|
| Total params | 230B |
| Active params | ~10B |
| Architecture | `minimax-m2` (чистый MoE, нет SSM) |
| Block count | 62 |
| Attention heads | 48 (full), 8 KV (GQA 6:1) |
| Head dimension | 128 |
| Embedding dim | 3,072 |
| Experts | 256 / 8 active |
| Context trained | 196,608 (192K) |
| RoPE base | 5,000,000 |
| Quantization | Unsloth Dynamic v2.0 UD-IQ3_S (~3.4 bit/wt) |
| File size | ~78 GiB (3 shards: 7.9M + 47G + 32G) |
| VRAM loaded | 82,502 MiB (80.6 GiB) / 96 GiB |

> llama.cpp поддержка: требуется build ≥ b8022 (протестировано на b8895). Architecture `minimax-m2` распознана.

### Скорость MiniMax-M2.7 UD-IQ3_S

| Метрика | MiniMax-M2.7 | Qwen3.5-122B Q4_K_M | Qwen3.5-122B Q5_K_S |
|---------|-------------|---------------------|---------------------|
| Decode tok/s | **39.2** | 44.5 | 42.6 |
| Prompt tok/s | **244** | 128 | 121 |
| VRAM | 80.6/96 GiB | 70.5/96 GiB | 82.2/96 GiB |
| First warmup | 54s (cold mmap) | ~15s | ~15s |
| Ctx benchmark | 8192 | 8192 | 8192 |

> Примечание: Prompt speed у MiniMax в 2× быстрее 122B Q4_K_M (244 vs 128 tok/s).
> Decode чуть медленнее (39.2 vs 44.5 tok/s) — из-за большего числа слоёв (62 vs 48).

### Качество MiniMax-M2.7 UD-IQ3_S

#### Q1 — Thread-safe LRU

MiniMax использует `OrderedDict` + `RLock` — корректно, elegant, хорошие docstrings. Ответ 8,136 символов, очень детальный. ⭐⭐⭐⭐⭐

#### Q2 — Bug Fix (race condition в Counter)

Найдены 3 бага (thinking=7,547 chars, content=3,008 chars):
1. ✅ **Race condition** в `increment()` — non-atomic read-modify-write, example с Thread A/B
2. ✅ **Visibility guarantee** — `get()` может вернуть stale value без lock
3. ✅ **No synchronization primitive** — нет Lock в классе

Фикс: добавить `threading.Lock`, защитить `increment()` и `get()`. Объяснение memory barrier при acquire/release. ⭐⭐⭐⭐⭐

#### Q3 — Sliding Window Rate Limiter

- ✅ Sliding window с `deque` (O(1) append/popleft)
- ✅ Thread safety — `threading.RLock`
- ✅ Дополнительные методы: `get_remaining_requests`, `get_reset_time`, `reset_user`, `get_stats`
- ✅ Unit tests — basic + concurrent + edge cases
- ❌ Нет injectable `time_func` (uses `time.time()` напрямую → тяжелее юнит-тестировать)
- Ответ 14,572 символов (самый большой из всех моделей). ⭐⭐⭐⭐

### Итоговое сравнение всех 4 моделей V100

| Метрика | Baseline (Coder-Next) | BM1 (35B Q3) | V100 122B Q4_K_M | MiniMax M2.7 UD-IQ3_S |
|---------|----------------------|--------------|-----------------|----------------------|
| Decode tok/s | **71** | 130 | 44.5 | 39.2 |
| Prompt tok/s | 183 | ~350 | 128 | **244** |
| VRAM GiB | 70/96 | — | 70.5/96 | 80.6/96 |
| Q1 LRU | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Q2 bugs/3 | 1/3 | 3/3 | 3/3 | 3/3 |
| Q3 rate limiter | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Thinking | ❌ off | ✅ | ✅ | ✅ |
| Max ctx | 1M | 40K | 262K | 192K |

### Вывод по MiniMax-M2.7

**Не рекомендуется заменять текущий прод (122B Q4_K_M)** по следующим причинам:

1. **Медленнее по decode**: 39.2 vs 44.5 tok/s (−12%)
2. **Больше VRAM**: 80.6 vs 70.5 GiB → меньше запас
3. **Качество comparable**: оба находят 3/3 бага, оба генерируют comprehensive код
4. **Меньше max ctx**: 192K vs 262K
5. **Более сложный MoE**: 62 блоков vs 48 → выше latency на длинных генерациях

**Преимущество MiniMax**: prompt speed (244 vs 128 tok/s) — значимо для задач с длинным контекстом (RAG, большие code bases). Если основная нагрузка — длинные prompts + короткие ответы, MiniMax предпочтительнее.

**Остаётся в продакшне**: Qwen3.5-122B-A10B Q4_K_M.

**MiniMax хранится на диске** (`/data/shared/<user>/models/MiniMax-M2.7-GGUF/UD-IQ3_S/`) как резервный вариант.

---

## Файлы на диске

```
/data/shared/<user>/models/
├── Qwen3.5-122B-A10B-GGUF/
│   ├── Q4_K_M/          (72 GiB) ← ПРОД (активен)
│   └── Q5_K_S/Q5_K_S/   (81 GiB) ← резерв
├── Qwen3.5-397B-A17B-GGUF/
│   ├── IQ1_M/            (86 GiB) ← для экспериментов
│   ├── IQ2_XXS/          (100 GiB) ← для экспериментов
│   └── IQ2_XS/           (111 GiB) ← для экспериментов
├── MiniMax-M2.7-GGUF/
│   └── UD-IQ3_S/         (78 GiB) ← протестирован, резерв
└── Qwen3-Coder-Next-GGUF/
    └── Q5_K_S/ (в /data/shared/<user>/models/) ← deprecated
```

---

*Создан 2026-04-23 по результатам тестирования.*
*Связанные документы: `v100-ram-overflow-397b-exp.md`, `decision-log.md` D-019.*
