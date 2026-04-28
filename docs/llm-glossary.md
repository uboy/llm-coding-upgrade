# Глоссарий параметров LLM

> Все технические параметры, встречающиеся в конфигурации llama.cpp и архитектуре моделей.

## Архитектура модели

### Total parameters (общее число параметров)

Общее количество весов в модели. Включает embedding-слой, все transformer/SSM блоки, lm_head.
Для dense-моделей = active parameters. Для MoE — включает веса **всех** экспертов, даже неактивных.

Пример: Qwen3.5-122B — 122 миллиарда параметров total.

### Active parameters (активные параметры на токен)

Количество параметров, **фактически используемых** при генерации каждого токена.
Для dense-моделей = total parameters. Для MoE — только веса активированных экспертов.

Пример: Qwen3.5-122B-A10B — из 122B total только 10B используются на каждый токен
(8 из 64 экспертов активируются per-token). Это делает inference значительно дешевле,
чем у dense-модели аналогичного размера.

**Почему важно:** определяет:
- Скорость inference (меньше активных → быстрее decode)
- VRAM для compute (не для хранения — все веса всё равно в памяти)
- Сравнение: dense 10B ≈ MoE 122B-A10B по скорости, но MoE даёт качество 122B модели

### MoE (Mixture of Experts)

Архитектура, где вместо одной FFN (feed-forward network) на каждом слое стоит набор
«экспертов» (отдельных FFN) + router (маршрутизатор). На каждом токене router
выбирает K экспертов из N для активации.

- **Experts (N)**: общее число экспертов. Все хранятся в VRAM.
- **Active experts (K)**: сколько активируются на каждый токен. Определяет active params.
- **Router**: небольшая линейная проекция, определяет top-K экспертов per-token.

Пример: Qwen3.5-122B — 64 эксперта, 8 активных (8/64).
Qwen3.6-35B — 32 эксперта, 4 активных (4/32).

**Компромисс MoE:**
- ✅ Качество ~dense модели с total params при скорости dense модели с active params
- ❌ Все веса N экспертов должны поместиться в VRAM (storage = total, not active)
- ❌ Load balancing: разные эксперты активируются с разной частотой

### Блоки / Слои (Blocks / Layers)

Transformer состоит из N одинаковых блоков, уложенных последовательно.
Каждый блок обрабатывает входные данные и передаёт результат следующему.

Увеличение числа блоков:
- ↑ Качество (больше нелинейных преобразований, глубже reasoning)
- ↑ VRAM для весов (линейно)
- ↑ Время decode (больше матричных умножений)
- ↑ KV cache (если блок содержит attention-слой)

Пример: Qwen3.5-122B — 48 блоков. MiniMax-M2.7 — 62 блока (отсюда медленнее при 39 vs 44 tok/s).

### Attention-слои

Слои, реализующие self-attention — механизм, позволяющий каждому токену «смотреть»
на все предыдущие токены через KV (Key-Value) кеш. Это «память» модели.

В гибридных моделях (SSM/attention) не все блоки содержат attention.
Параметр `full_attention_interval` задаёт период: каждый N-й блок — attention,
остальные — SSM/recurrent.

Пример: interval=4 → из 48 блоков только 12 — attention (остальные 36 — SSM).
Это кардинально снижает KV cache: 12 слоёв вместо 48.

### SSM / Recurrent слои

Альтернатива attention. Вместо хранения KV для всех предыдущих токенов,
поддерживают фиксированный-size рекуррентный state (RS buffer).

- ✅ Фиксированный memory footprint (не растёт с контекстом)
- ✅ O(1) update per token (vs O(n) для attention)
- ❌ Меньшая expressiveness (хуже для precise retrieval из длинного контекста)
- ❌ Speculative decoding несовместим (нельзя откатить state)

Параметр: `ssm_d_state` — размер рекуррентного state (например, 128).

### GQA (Grouped Query Attention)

Оптимизация attention: вместо уникальных KV-head для каждого query-head,
группирует query-heads, разделяя KV-heads внутри группы.

- **n_kv_heads**: количество KV-heads (ключей/значений)
- **n_head**: количество query-heads (запросов)
- GQA ratio = n_head / n_kv_heads

Полный attention (MHA): n_kv_heads = n_head (например, 32/32).
GQA: n_kv_heads < n_head (например, 32 query heads, 4 KV heads).
MQA (Multi-Query Attention): n_kv_heads = 1 (минимальный KV cache).

**Влияние на KV cache:** KV ∝ n_kv_heads. GQA 4 KV heads → в 8× меньше KV чем MHA 32 heads.

Пример: Qwen3.5-122B — 4 KV heads. MiniMax-M2.7 — 8 KV heads. DeepSeek V4-Flash — 1 KV head.

### Head dimension (dim)

Размерность одной attention head. Определяет «разрешение» attention.
Стандарт: 128 или 256.

KV per attention layer = 2 × n_kv_heads × head_dim × seq_len × bytes_per_element.

### Embedding dimension

Размер скрытого состояния модели (hidden_size). Определяет общую «ёмкость» модели.
Коррелирует с total params.

## KV Cache

### Что такое KV Cache

При генерации токена t модель должна «видеть» все предыдущие токены 0..t-1.
Self-attention вычисляет ключи (K) и значения (V) для каждого токена.
KV cache хранит уже вычисленные K,V, чтобы не пересчитывать их для каждого нового токена.

Без KV cache: генерация токена t = O(t²) операций (пересчёт всех K,V).
С KV cache: генерация токена t = O(1) операций (добавить K,V только для нового токена).

Tradeoff: KV cache растёт линейно с длиной контекста и числом одновременных запросов.

### Формула расчёта KV cache

```
KV_size (bytes) = 2 × n_layers_attn × n_kv_heads × head_dim × ctx_size × bytes_per_element
```

Где:
- `2` — отдельно Key и Value
- `n_layers_attn` — количество attention-слоёв (не всех блоков, только attn!)
- `n_kv_heads` — KV-heads (из GQA)
- `head_dim` — размерность одной head
- `ctx_size` — длина контекста (токенов)
- `bytes_per_element` — 2 для F16, 1 для Q8_0, 0.5 для Q4_0

**Пример расчёта — V100 (Qwen3.5-122B):**
```
n_layers_attn = 12 (48 блоков, interval=4)
n_kv_heads = 4
head_dim = 128
ctx_size = 262,144
bytes_per_element = 1 (Q8_0)

KV = 2 × 12 × 4 × 128 × 262,144 × 1 = 3,221,225,472 bytes ≈ 3,072 MiB
Факт: ~3,264 MiB (включая overhead)
```

**Пример расчёта — BM (Qwen3.6-35B):**
```
n_layers_attn = 10 (40 блоков, interval=4)
n_kv_heads = 2
head_dim = 256
ctx_size = 262,144
bytes_per_element = 1 (Q8_0)

KV = 2 × 10 × 2 × 256 × 262,144 × 1 = 2,684,354,560 bytes ≈ 2,560 MiB
Факт: ~2,720 MiB (включая overhead)
```

### KV Cache квантизация

KV можно хранить в разных форматах:
- **F16** (2 bytes): без потерь, максимальное качество
- **Q8_0** (1 byte): ~0.01 ppl degradation, 2× экономия VRAM — **рекомендуется**
- **Q4_0** (0.5 bytes): ~0.05 ppl degradation, 4× экономия — для длинных контекстов

`--cache-type-k q8_0 --cache-type-v q8_0` в llama.cpp.

## Контекст (Context)

### n_ctx_train (тренировочный контекст)

Максимальная длина контекста, на которой модель обучалась. RoPE positional embeddings
определены до этого предела. Использование выше n_ctx_train требует экстраполяции
RoPE (через RoPE scaling), что может ухудшить качество.

Пример: Qwen3.5-122B — n_ctx_train=262144 (256K). MiniMax-M2.7 — 192K.

### --ctx-size (в llama.cpp)

Общий размер KV cache в токенах. Распределяется между параллельными слотами:
```
ctx_per_slot = --ctx-size / --parallel
```

Если ctx_per_slot > n_ctx_train → RoPE экстраполяция (потенциальная потеря качества).
Если ctx_per_slot < n_ctx_train → контекст урезан, модель «не видит» весь свой потенциал.

### --parallel

Число одновременных слотов inference. Каждый слот получает ctx_per_slot контекста.

- parallel=1: весь ctx-size доступен одному пользователю. Максимальный контекст.
- parallel=2: ctx делится пополам. Два пользователя одновременно.
- parallel=4: ctx делится на 4. Четыре пользователя, но контекст в 4× короче.

**Tradeoff:** больше parallel → больше одновременных пользователей, но меньше контекст каждому.
Больше parallel → немного больше VRAM overhead (буферы, pipeline).

### ctx_per_slot (контекст на слот)

Реальный доступный контекст для одного пользователя/запроса:
```
ctx_per_slot = --ctx-size / --parallel
```

Если ctx_per_slot < n_ctx_train → потеряна часть потенциального контекста модели.
Если запрос превышает ctx_per_slot → ошибка `exceeds context size`.

**Пример:**
V100: `--ctx-size 262144 --parallel 4` → ctx_per_slot = 65536 ← проблема!
Запрос в 262K токенов не влезает.

Решение: `--parallel 2 --ctx-size 589824` → ctx_per_slot = 294912 ← достаточно.

## Квантизация (Quantization)

### Что такое квантизация

Сжатие весов модели из F16 (2 bytes/param) в меньшие форматы для экономии VRAM
и ускорения inference за счёт уменьшения memory bandwidth.

| Формат | Bytes/param | Относительный размер | PPL degradation |
|--------|------------|---------------------|-----------------|
| F16 | 2.0 | 100% | baseline |
| Q8_0 | 1.0 | 50% | ~0.01 |
| Q5_K_M | 0.75 | 37.5% | ~0.05 |
| Q4_K_M | 0.69 | 34.5% | ~0.10 |
| Q3_K_M | 0.55 | 27.5% | ~0.25 |
| IQ3_S | 0.45 | 22.5% | ~0.40 |
| Q2_K | 0.38 | 19% | ~0.60 |
| IQ1_M | 0.22 | 11% | ~1.20 |

### K-quants vs I-quants

- **K-quants** (Q4_K_M, Q5_K_S, ...): блоковая квантизация с разным размером блоков.
  Устойчивые, хорошо протестированные. Суффиксы: _S (small), _M (medium), _L (large).
- **I-quants** (IQ3_S, IQ2_XXS, ...): importance matrix quantization. Использует
  calibration dataset для определения значимости каждого веса. Лучшее качество
  при том же bitrate, но сложнее в производстве.

### imatrix (Importance Matrix)

Матрица, вычисленная на representative dataset, указывающая значимость каждого
тензора в модели. Используется I-quants для оптимального распределения бит.
Без imatrix I-quants работают хуже. Суффикс «imatrix» в имени файла GGUF означает
использование этой матрицы.

## Sampling параметры

### Temperature (temp)

Контролирует «случайность» выбора следующего токена.
- temp=0: всегда выбирает самый вероятный токен (greedy). Детерминированный, но скучный.
- temp=1.0: оригинальное распределение вероятностей из модели.
- temp<1: сужает distribution → более «уверенные», предсказуемые ответы.
- temp>1: расширяет distribution → более «креативные», но менее coherent ответы.

Для thinking-моделей Qwen3: temp=0.6 рекомендован (balanced reasoning).
Для non-thinking моделей: temp=1.0 (позволяет модели проявить обучение).

### top-k

Ограничивает кандидатов до K наиболее вероятных токенов.
- top-k=1: greedy (как temp=0)
- top-k=40: стандарт для non-thinking
- top-k=20: для thinking (узкий пул, фокус на reasoning chain)

### top-p (nucleus sampling)

Выбирает из минимального набора токенов, чья суммарная вероятность ≥ p.
- top-p=0.95: стандарт (отсекает хвост distribution)
- top-p=1.0: не ограничивает (все токены-кандидаты)

### min-p

Отсекает токены с вероятностью < min-p × max_probability.
- min-p=0.0: не применяется
- min-p=0.05: отсекает маловероятные токены даже если top-p их включает

### repeat-penalty

Штрафует токены, которые уже появлялись в output. Предотвращает зацикливание.
- 1.0: нет штрафа
- 1.1: лёгкий штраф (рекомендован для Qwen3-Coder-Next)
- **НЕ применять для thinking-моделей** — повторение в reasoning chain — нормальный паттерн

## Thinking / Reasoning

### Hybrid Thinking (Qwen3.x)

Модель генерирует два блока:
1. **Thinking chain** (внутренний reasoning, тег `<think/>`) — невидим пользователю
2. **Content** (финальный ответ) — видимый результат

Thinking chain «съедает» токены из max_tokens бюджета. Если thinking слишком длинный —
content будет пустым (как у BM на Q02/Q04/Q08/Q09).

Рекомендации:
- max_tokens ≥ 4000 для coding (thinking ~2000-3000 токенов)
- max_tokens ≥ 8000 для сложных задач
- `/no_think` prefix в prompt — отключает thinking для speed-critical задач

### --reasoning on/off (llama.cpp)

Флаг, управляющий parsing reasoning_content из ответа модели.
- `on`: разделяет ответ на thinking + content (для thinking-моделей)
- `off`: весь ответ — content (для non-thinking моделей)

## Speed метрики

### Decode speed (tok/s)

Скорость генерации **новых** токенов. Зависит от:
- Количества активных параметров (больше → медленнее)
- VRAM bandwidth (все веса читаются на каждый токен — memory-bound)
- GPU clock и memory bus width
- KV cache size (больше → медленнее attention, но для SSM-моделей не критично)

Формула (упрощённая): `tok/s ≈ bandwidth / (2 × active_params × bytes_per_weight)`

### Prompt speed (tok/s)

Скорость обработки **входного** prompt. Зависит от:
- GPU compute (матричные умножения в parallel)
- Batch size (prompt tokens обрабатываются параллельно)
- Обычно 5-30× быстрее decode

### TTFT (Time To First Token)

Время от отправки запроса до первого токена ответа.
= prompt_processing_time + time_to_first_decode_token.
Для thinking-моделей TTFT может включать весь thinking chain.

## VRAM

### Компоненты VRAM

```
VRAM_total = model_weights + KV_cache + RS_buffer + compute_buffers + overhead

model_weights:  file_size GGUF (зависит от квантизации)
KV_cache:       формула выше (зависит от ctx, layers, GQA)
RS_buffer:      ssm_d_state × n_ssm_layers × hidden (фиксированный, не зависит от ctx)
compute_buf:    ~200-500 MiB (временные тензоры для attention, FFN)
overhead:       CUDA context, CUDA graphs, etc.
```

### Распределение по GPU (--split-mode layer)

При multi-GPU модель «разрезается» по слоям:
- `--split-mode layer`: GPU0 получает первые N слоёв, GPU1 — следующие, и т.д.
- `--tensor-split`: пропорция распределения VRAM между GPU

Каждый GPU хранит свою часть весов + полный KV cache для своих attention-слоёв.

## Спецификации серверов

| Параметр | V100 | RTX 3090 (BM) |
|----------|------|---------------|
| GPU | 3× Tesla V100 PCIE 32GB | 1× RTX 3090 24GB |
| VRAM total | 96 GiB | 24 GiB |
| Memory BW | 900 GB/s (HBM2) | 936 GB/s (GDDR6X) |
| Compute | CC 7.0 (Volta) | CC 8.6 (Ampere) |
| NVLink | Нет (PCIe only) | Нет |
| Flash Attention | ✅ (CC≥7.0) | ✅ (CC≥7.0) |

**Узкое место V100:** decode speed ограничен PCIe bandwidth между GPU при multi-GPU inference.
Все три GPU обрабатывают sequentially по pipeline, данные пересылаются через PCIe.
Отсутствие NVLink ограничивает эффективный throughput.

## MoE Tensor Distribution

### ncmoe (--n-cpu-moe)

Режим распределения тензоров MoE модели по GPU. Вместо загрузки целыми слоями (ngl),
ncmoe распределяет тензоры точечно: attention-тензоры на GPU, MoE-эксперты — пропорционально.

- **ngl** (`--n-gpu-layers`): загружает целые слои. Для MoE неэффективно — GPU простаивает на неактивных экспертах.
- **ncmoe** (`--n-cpu-moe`): точечное распределение. GPU загружен на 100%. Автоматически включается при `--fit on`.
- **cmoe** (`--cpu-moe`): MoE-эксперты на CPU, attention на GPU. Медленнее TG, но экономит VRAM.

Режим `--fit on` автоматически выбирает ncmoe для MoE моделей и ngl для Dense.

## UD-кванты (Unsloth Dynamic)

### Что такое UD-кванты

Unsloth Dynamic (UD) — схема динамического квантования от Unsloth. В отличие от статичных
K-квантов (Q4_K_M), UD использует:

- **Блочное квантование** с разным scale для каждого блока (выше точность)
- **Калибровочную imatrix** (importance matrix) для определения значимости тензоров
- **Разделение attn/ffn**: attn-тензоры квантуются слабее (категория XL = Extra Large quality)

### Обозначения

- `UD-Q4_K_XL`: UD-квантование, FFN в Q4, attn в повышенном качестве (XL)
- `UD-Q3_K_XL`: UD-квантование, FFN в Q3, attn в XL — легче на ~4 GB при качестве ≈ Q4_K_M
- `IQ4_KS`: ik_llama-специфичный квант, сопоставим с UD-Q4_K_XL, но легче на ~1 GB

### Сравнение (Qwen3.6-35B-A3B)

| Квант | Размер (GiB) | Качество (KLD ↓) |
|-------|-------------|-----------------|
| Q4_K_M | 21.2 | baseline (худшее) |
| UD-Q4_K_XL | 22.4 | лучше Q4_K_M |
| UD-Q3_K_XL | 16.8 | ≈ Q4_K_M (на 4.4 GiB легче!) |
| IQ4_KS (ik_llama) | 21.0 | ≈ UD-Q4_K_XL |

## Speculative Decoding

### Что такое Speculative Decoding

Метод ускорения inference: маленькая модель-черновик (draft) генерирует N токенов,
затем большая модель верифицирует их за один проход. Accepted токены не нужно
генерировать заново → экономия времени.

Ускорение: ~1.5× для Dense моделей на coding-задачах (при ratio active params > 3×).

### Ограничение для SSM/гибридных моделей

Speculative decoding требует **отката KV-cache** при отклонении draft-токенов.
SSM/recurrent слои хранят полный рекуррентный state — его невозможно откатить на N
токенов назад без полного пересчёта.

**Вывод:** Speculative decoding **НЕ работает** с гибридными SSM моделями
(Qwen3.5-122B, Qwen3.6-35B, Qwen3-Coder-Next). Это архитектурное ограничение,
обойти без смены модели невозможно (D-016).

## ik_llama.cpp

### Что такое ik_llama.cpp

Форк llama.cpp от ikawrakow (создатель K-quants и I-quants). Основные отличия:

- **IQK кванты** (IQ4_KS и др.): лучше качество при меньшем размере vs UD-Q4_K_XL
- **Q6 KV cache**: промежуточный вариант между Q8 и F16
- **Лучшая скорость PP**: до 4× при стандартных -ub/-b
- **Медленнее TG**: родные IQK кванты могут быть медленнее на decode

Минусы: один разработчик, расхождение с llama.cpp растёт, слабая поддержка Vulkan/ROCm.

Для V100 (CC 7.0) требуется отдельная сборка: `cmake -DCMAKE_CUDA_ARCHITECTURES="70"`.

## Batch Size (-b / -ub)

### --batch-size (-b)

Максимальное число токенов, обрабатываемых параллельно при prompt processing (PP).
Больше значение → быстрее PP, но больше VRAM overhead.

### --ubatch-size (-ub)

Micro-batch size: размер под-батча внутри одного batch. Должен быть ≤ batch-size.
Для V100 рекомендовано ubatch = batch (например, `-b 2048 -ub 2048`).

Влияние: PP speed может вырасти с ~93 tok/s до ~475 tok/s (+5×).
На decode speed (TG) не влияет.
