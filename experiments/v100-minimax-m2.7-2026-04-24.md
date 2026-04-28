# Эксперимент: MiniMax-M2.7 на V100 — 2026-04-24

> Цель: сравнить MiniMax-M2.7 UD-IQ3_S с текущей прод-моделью Qwen3.5-122B Q4_K_M на V100.

---

## Модель и конфигурация

| Параметр | Значение |
|---------|--------|
| Модель | MiniMax-M2.7 UD-IQ3_S |
| Источник | unsloth/MiniMax-M2.7-GGUF |
| Размер файлов | 78 GiB (7.9 MB + 47 GB + 32 GB, 3 шарда) |
| Путь | `/data/shared/<user>/models/MiniMax-M2.7-GGUF/UD-IQ3_S/` |
| Архитектура | `minimax-m2`, 228.69B params |
| Блоков | 62 (все — full attention, нет SSM/hybrid) |
| Attention heads | 48 (GQA, 8 KV heads), head_dim=128 |
| Experts | 256 / 8 активных (MoE) |
| Context trained | 196,608 (192K) |
| Embedding | 3,072 |

## VRAM на V100 (96 GiB)

| Компонент | MiB |
|-----------|-----|
| CUDA0 model | 26,680 |
| CUDA1 model | 26,680 |
| CUDA2 model | 25,891 |
| KV cache (8192 ctx) | 1,054 |
| Compute buffers | ~792 |
| **Итого** | **~81,097 MiB (~79.2 GiB)** |

Запас: ~14.9 GiB. При ctx=32768: +4 GiB KV → ~83.2 GiB (OK). При ctx=65536: +8 GiB → ~87.2 GiB (OK).

## Скорость

| Метрика | MiniMax-M2.7 UD-IQ3_S | Qwen3.5-122B Q4_K_M | Разница |
|---------|----------------------|---------------------|---------|
| Decode (tok/s) | **39.4** | 44.5 | −11.5% |
| Prompt eval (tok/s) | ~234 | 128 | +83% |
| Cold start | ~45s | ~190ms TTFT | хуже |
| VRAM | 79.2 GiB | 79.4 GiB | ≈ |

> ctx=8192, parallel=1, Q8_0 KV, 3 warmup + 3 измерения.

## Thinking mode — критическая проблема

MiniMax-M2.7 генерирует очень длинные thinking-цепочки:
- Q1 (LRU cache): ~1144 токенов thinking (46% от total) — OK
- Q2 (bug fix): **>7000 токенов thinking** — при max_tokens=7000 content пустой
- Q3 (rate limiter): **>7000 токенов thinking** — аналогично

**Workaround**: префикс `/no_think` + параметр `reasoning_effort: "none"` → thinking сокращается до 4-7K chars, content появляется.

## Качество кодинга

### Q1 — Thread-safe LRU Cache
| Критерий | Результат |
|---------|--------|
| Алгоритм | Doubly linked list + dict + Lock — оптимально |
| Type hints | ✅ использованы |
| Thread safety | ✅ Lock.acquire/release через context manager |
| Качество | ⭐⭐⭐⭐⭐ |

### Q2 — Bug Fix (race condition в Counter)
С `/no_think` + `reasoning_effort: none`:
| Баг | Найден? |
|-----|--------|
| Race condition в increment() | ✅ |
| get() не thread-safe | ✅ |
| assert отключается -O | ❌ не упомянут |
| **Итого** | **2/3** |

### Q3 — Sliding Window Rate Limiter
С `/no_think` + `reasoning_effort: none`:
| Критерий | Результат |
|---------|--------|
| Алгоритм | deque + timestamp pruning |
| Thread safety | ✅ RLock |
| Тесты | ✅ comprehensive (unit tests) |
| Качество | ⭐⭐⭐⭐⭐ |

## Сравнение с другими моделями

| Модель | Decode | Q2 баги | Q3 дизайн | Thinking |
|--------|--------|---------|-----------|---------|
| Baseline (Coder-Next) | 71 tok/s | 1/3 | ⭐⭐⭐ | off |
| **Qwen3.5-122B Q4_K_M** | 44.5 tok/s | **3/3** | ⭐⭐⭐⭐⭐ | контролируемый |
| MiniMax-M2.7 UD-IQ3_S | 39.4 tok/s | 2/3 | ⭐⭐⭐⭐⭐ | ⚠️ неуправляемый |
| BM1 (Qwen3.6-35B Q3_K_M) | 130 tok/s | 2/3* | ⭐⭐⭐⭐⭐ | контролируемый |

*BM1 нашел race + объяснил GIL (2.5/3 можно считать)

## Вердикт

**❌ MiniMax-M2.7 UD-IQ3_S не рекомендуется для V100**

Причины:
1. **Медленнее decode** (39.4 vs 44.5 tok/s) — при сопоставимом размере VRAM
2. **Неконтролируемый thinking** — Q2/Q3 требуют воркэраунда, иначе пустой ответ
3. **Хуже на bug finding** (2/3 vs 3/3 у 122B)
4. Промпт-скорость выше (~234 vs 128 tok/s), но это не компенсирует decode penalty

**Текущий прод остаётся: Qwen3.5-122B Q4_K_M**.

---

## Файлы

MiniMax файлы сохранены на диске (78 GiB):
```
/data/shared/<user>/models/MiniMax-M2.7-GGUF/UD-IQ3_S/
├── MiniMax-M2.7-UD-IQ3_S-00001-of-00003.gguf   (7.9 MB)
├── MiniMax-M2.7-UD-IQ3_S-00002-of-00003.gguf   (47 GB)
└── MiniMax-M2.7-UD-IQ3_S-00003-of-00003.gguf   (32 GB)
```

Удалить если нужно освободить место: `rm -rf /data/shared/<user>/models/MiniMax-M2.7-GGUF/`

*Создан 2026-04-24.*
