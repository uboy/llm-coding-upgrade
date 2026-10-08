# Config Card - Производственная конфигурация

> Актуально на 2026-05-07. За sampling-параметрами - в `decision-log.md`.

## V100 - Qwen3.5-122B-A10B (кодинг + reasoning)

| Параметр | Значение |
|---|---|
| Model | Qwen3.5-122B-A10B UD-Q4_K_XL |
| GGUF path | `/models/Qwen3.5-122B-A10B-GGUF/UD-Q4_K_XL/Qwen3.5-122B-A10B-UD-Q4_K_XL-00001-of-00003.gguf` |
| Runtime | `ghcr.io/ggml-org/llama.cpp:server-cuda` |
| Proxy alias | `qwen` (порт 4001) |
| Proxy URL | `http://v100-host:4001/v1` |
| llama.cpp upstream | `http://127.0.0.1:8001` |
| GPU | 3× Tesla V100 PCIE 32GB (PCIe only, NVLink недоступен) |
| CUDA_VISIBLE_DEVICES | 0,1,2 |

### llama.cpp параметры

```
--n-gpu-layers 100
--ctx-size 262144           # native n_ctx_train модели
--batch-size 2048           # PP throughput
--ubatch-size 2048          # PP throughput (+37-42% vs 512, D-038)
--split-mode layer
--tensor-split 1,1,1
--parallel 1
--cache-type-k q4_0         # экономия VRAM vs Q8_0, без потери качества
--cache-type-v q4_0
--jinja                     # нативный chat template для tool-calling
--reasoning on              # thinking-модель
--temp 0.6
--top-p 0.95
--top-k 20
--min-p 0.0
--repeat-penalty 1.0        # 1.0 = отключен (thinking models)
```

> Примечание: `--override-kv` не используется - `ctx-size` совпадает с `n_ctx_train=262144`.

### VRAM (факт, 2026-05-07, ubatch=2048, parallel=1, ctx=262144, KV Q4_0, UD-Q4_K_XL)

```
GPU0: 30,180/32,768 MiB (92.1%)  - 2,3 GiB свободно
GPU1: 26,350/32,768 MiB (80.4%)  - 6,1 GiB свободно
GPU2: 26,424/32,768 MiB (80.6%)  - 6,1 GiB свободно
Total: 82,954/98,304 MiB (84.4%)
Веса: ~72 GiB (UD-Q4_K_XL)
Compute buffer: ~9.8 GiB (GPU0, ubatch=2048)
```

> GPU0 increased from 89% to 92% vs ubatch=512. Additional compute buffer ~+1.2 GiB.
> Stable, no OOM observed on 128K prompts. Production decision D-038.

### Скорость (2026-05-07, ubatch=2048, UD-Q4_K_XL, parallel=1, ctx=262144, KV Q4_0)

**Короткий контекст (cold cache):**

| Prompt tokens | PP tok/s | Decode tok/s | Wall time |
|---------------|----------|-------------|-----------|
| 865 | 498.3 | 44.6 | 4.8s |
| 11,785 | 445.0 | 41.6 | 30.2s |

**Длинный контекст (cold cache, один запрос):**

| Prompt tokens | PP tok/s | Decode tok/s | Wall time |
|---------------|----------|-------------|-----------|
| 75,362 | 369.7 | 23.0 | 183s |
| 150,702 | 246.9 | 22.3 | 320s |

**PP improvement vs ubatch=512 (D-038):**

| Context | PP before | PP after | Delta |
|---------|-----------|----------|-------|
| 10K | 325.6 tok/s | 445.0 tok/s | +37% |
| 64K | 262.6 tok/s | 369.7 tok/s | +41% |
| 128K | 189.4 tok/s | 246.9 tok/s | +30% |

**Wall time improvement:**
- 10K: 39.8s → 30.2s (-24%)
- 64K: 249s → 183s (-26%)
- 128K: 407s → 320s (-21%)

> *256K тест с горячим KV cache (предыдущие запросы прогрели кэш). Cold 256K оценочно ~33 мин при ~130 tok/s PP.

**Деградация decode по контексту:**
- 0-2K: **42-48 tok/s** (полная скорость)
- 10-65K: **16-22 tok/s** (PCIe bottleneck между 3 GPU)
- 100-256K: **14-25 tok/s**

- Cold-start: ~76s (cold cache, загрузка модели)

> Ранее 41.3 tok/s при parallel=2, ctx=589824 - decode стал быстрее на коротком контексте.
> Ранее 23.9 tok/s при parallel=4, ctx=262144 (4×65536 слота).

### Архитектура

| Параметр | Значение |
|----------|---------|
| Total params | 122B |
| Active params | 10B |
| Type | MoE (8/64 experts) + SSM |
| Blocks | 48 |
| Attention layers | 12 (interval=4) |
| SSM layers | 36 |
| KV heads (GQA) | 4 |
| Head dim | 128 |
| Embed dim | 2048 |
| n_ctx_train | 262,144 (256K) |
| Thinking | ✅ hybrid |

---

## bm1 / bm2 - Qwen3.6-35B-A3B (general + vision)

| Параметр | Значение |
|---|---|---|
| Model | Gemma 4 26B-A4B Q4_K_M |
| GGUF path | `/models/gemma4/google_gemma-4-26B-A4B-it-Q4_K_M.gguf` |
| mmproj | не используется (текстовая модель) |
| HF repo | `google/gemma-4-26B-A4B-it-GGUF` |
| Runtime | `ghcr.io/ggml-org/llama.cpp:server-cuda` |
| LB alias | `gemma4` |
| LB URL | `http://v100-host:4002/v1` |
| GPU | 1× RTX 3090 24GB (на каждом сервере) |

### llama.cpp параметры

```
-ngl 100 (BM1) / -ngl 999 (BM2)
--ctx-size 262144
--parallel 1
--batch-size 1024 --ubatch-size 256
--cache-type-k q8_0
--cache-type-v q8_0
--reasoning on
--jinja
--temp 0.6
--top-p 0.95
--top-k 20
--min-p 0.0
--override-kv qwen35moe.context_length=int:327680  # снять hard cap на n_ctx_train
```

### VRAM (факт, 2026-04-24, ctx=327680)

```
Веса (CUDA0):  15,256 MiB
KV Q8 (328K):   3,400 MiB  ← 10/40 attn слоёв, остальные SSM
RS buffer:         63 MiB  ← recurrent state (фиксированный)
Compute buf:      ~350 MiB
─────────────────────────────
BM1:  21,195 / 24,576 MiB (86.2%)
BM2:  21,128 / 24,576 MiB (85.9%)
```

### Скорость (production, 2026-04-28, smoke-verified)

- Decode: **140.7 tok/s** (smoke-verified)
- Prompt: **471 tok/s** (smoke-verified)
- LB backends: BM1 + BM2 оба **healthy**

### Архитектура

| Параметр | Значение |
|----------|---------|
| Total params | 35B |
| Active params | 3B |
| Type | MoE (4/32 experts) + SSM |
| Blocks | 40 |
| Attention layers | 10 (interval=4) |
| SSM layers | 30 |
| KV heads (GQA) | 2 |
| Head dim | 256 |
| Embed dim | 3072 |
| n_ctx_train | 262,144 (256K) - переопределён на 327,680 через override-kv |
| Thinking | ✅ hybrid |
| Vision | ✅ mmproj |

---

## Управляющие скрипты

### deploy.sh - Единый lifecycle-менеджер

Управляет всеми сервисами: V100 стек + LB proxy + BM1/BM2 (через SSH).

```bash
bash scripts/deploy.sh restart            # Перезапуск всего (V100 + BM + LB) с health-waits
bash scripts/deploy.sh restart-local      # Только локальные сервисы (V100 + LB)
bash scripts/deploy.sh restart-bm         # Только BM1/BM2 через SSH
bash scripts/deploy.sh status             # Статус всех сервисов с параметрами
bash scripts/deploy.sh smoke              # E2E smoke на всех эндпоинтах
bash scripts/deploy.sh down               # Остановить все локальные сервисы
bash scripts/deploy.sh logs [target]      # Логи: v100, lb, bm1, bm2, all
```

Порядок restart с health-waits:
1. V100 llama.cpp → wait `/health` (до 5 мин)
2. BM1/BM2 llama.cpp → wait `/health` через SSH (до 5 мин)
3. LB proxy → wait port ready (до 30с)

### apply-model.sh - Переключение модели

Читает `model-suite.models.json`, генерирует конфиг, перезапускает стек, валидирует, откатывает при ошибке.

```bash
bash scripts/apply-model.sh list              # Список доступных моделей
bash scripts/apply-model.sh current           # Текущий активный конфиг
bash scripts/apply-model.sh apply <model-id>  # Переключить модель (с rollback)
```

Полный цикл `apply`: parse JSON → resolve GGUF → validate → backup config → generate stack.env → restart → wait-ready → smoke → откат при ошибке.

### stack.sh - Управление V100 стеком

Управляет локальными контейнерами: llama.cpp, proxy, Open WebUI.

```bash
bash scripts/stack.sh up             # Запустить стек
bash scripts/stack.sh down           # Остановить стек
bash scripts/stack.sh restart        # Перезапустить стек
bash scripts/stack.sh status         # Статус контейнеров
bash scripts/stack.sh smoke          # Smoke test через proxy
bash scripts/stack.sh wait-ready [timeout]  # Ждать готовности llama.cpp
bash scripts/stack.sh logs [target]  # Логи: all, llama, proxy, webui
bash scripts/stack.sh render-proxy   # Перегенерировать proxy.js из конфига
```

### lb-stack.sh - Управление LB proxy

Управляет контейнером load balancer proxy.

```bash
bash scripts/lb-stack.sh up             # Запустить LB proxy
bash scripts/lb-stack.sh down           # Остановить
bash scripts/lb-stack.sh restart        # Перезапустить
bash scripts/lb-stack.sh status         # Статус
bash scripts/lb-stack.sh smoke          # Smoke test
bash scripts/lb-stack.sh logs           # Логи
```

### Конфигурационные файлы

| Файл | Назначение |
|------|-----------|
| `stack.env` | V100 стек: llama.cpp, proxy, Open WebUI, BM SSH |
| `lb-proxy.env` | LB proxy: backends, model alias |
| `model-suite.models.json` | Реестр моделей с runtime-параметрами |
| `model-suite.evals.json` | Конфигурация benchmark suite |

---

## Smoke check (2026-05-05)

```
V100 (qwen, :4001)
  llamacpp-server-p8001  Up  (healthy)
  llm-proxy-p4001        Up
  open-webui-p3001       Up  (healthy)
  Model: Qwen3.5-122B-A10B-UD-Q4_K_XL
  Decode: 42.7-47.8 tok/s | PP: 103-170 tok/s
  VRAM: 81.5/98.3 GiB (82.9%)
  Config: parallel=1, ctx=262144, KV Q4_0

LB (gemma4, :4002)
  BM1 (bm1:8001)  healthy
  BM2 (bm2:8001)  healthy
  Model: google_gemma-4-26B-A4B-it-Q4_K_M.gguf
  Decode: ~80 tok/s

Все сервисы работают без проблем.
```

---

## BM1/BM2 (RTX 3090 24 GB) - Qwen3.8-27B + DFlash 2 (протестировано 2026-08-20, НЕ продакшн)

> Рецепты проверены E2E на bm1/bm2.
> Полные данные: `experiments/dflash2-qwen38-27b-2026-08-20.md`. Продакшн-стек не тронут.

| Параметр | Значение |
|---|---|
| Runtime | `llamacpp-dflash2:pr27342` (llama.cpp PR #27342, `--spec-type draft-dflash`) |
| Target | `unsloth/Qwen3.8-27B-GGUF` UD-Q4_K_M (15.32 GiB) или UD-Q6_K (20.47 GiB) |
| Drafter | `incoai/Qwen3.8-27B-DFlash2-GGUF` Q4_K_M (1.07 GiB) |
| KV-кэш | q4_0 у target И драфтера (`-ctk/-ctv/-ctkd/-ctvd q4_0`) |
| Веса/скрипты | bm1 `~/proj/dflash2-bench/`; bm2 - Q4+drafter + longctx-скрипты |

### Проверенные конфигурации

| Рецепт | Конфиг | Скорость | Примечание |
|---|---|---|---|
| R1 скорость | Q4, ctx ≤16k, n-max 5 (код) / 2 (проза) | 95 tk/s (код) / 61 (проза) | 2.23× к baseline |
| R2 качество | Q6_K, ctx ≤8k, n-max 2 | 50.3 tk/s | +49%, VRAM 23 630 MiB |
| R3 длинный ctx | Q4, ctx ≤144k, n-max 5, KV q4_0 | 51.5–52.6 tk/s | 2.54×; потолок DFlash |

### Границы (24 GB, одна 3090)
- ctx ≥160k + DFlash: крэш на первом decode (ленивая аллокация спек-буферов).
- ctx 200k: только baseline без DFlash (17.3 tk/s, VRAM 20 259 MiB).
- Lossless НЕ побайтовый (расхождения на близких токенах при temp 0).
- n-max обязательно под тип нагрузки: дефолт 7 - хуже всех (до −4.4%).

## BM/big-model 2026-08 (эксперименты; продакшн не включено)

| Рецепт | Конфиг | Скорость | Примечание |
|---|---|---|---|
| R4 драйвер 3090 | Qwen3.8-27B UD-Q4_K_M, turbo3 KV + draft-mtp n-max 2, ctx 131072 | 62.3 tk/s @8k / 43.7 @104k | рекомендован владельцем как постоянный; образ llamacpp-turboquant:fork |
| R5 V100 качество | UD-Q6_K + draft-mtp 2 (32 GB) | 16.5 @8k, 26.5 @124k | Q6 влезает только на 32GB; turbo3 на V100 по скорости невыгоден |
| R6 консультант | DeepSeek-V4-Flash Q4 155GB + dspark, --n-cpu-moe, V100-хост | 6.0/8.7 tk/s, prefill 71-74 т/с | 284B, mmap; эксперименты, не стенд |

Веса-инвентарь после чистки 2026-08-23: bm1 = UD-Q4_K_M (16.5G) + образы/скрипты;
v100-host = UD-Q6_K (21G) + gpt-oss-120b-GGUF (60G) + DeepSeek Q4/dspark (155G).
Скрипты воспроизведения: experiments/scripts-bigmodel-2026-08/.
