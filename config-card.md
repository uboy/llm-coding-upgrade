# Config Card — Производственная конфигурация

> Актуально на 2026-04-28. За sampling-параметрами — в `decision-log.md`.

## V100 — Qwen3.5-122B-A10B (кодинг + reasoning)

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
--ctx-size 589824           # 2 слота × 294912 токенов
--batch-size 2048           # PP throughput
--ubatch-size 512           # micro-batch (безопасный для VRAM)
--split-mode layer
--tensor-split 1,1,1
--parallel 2
--cache-type-k q4_0         # -3.5 GiB vs Q8_0, без потери качества
--cache-type-v q4_0
--jinja                     # нативный chat template для tool-calling
--reasoning on              # thinking-модель
--temp 0.6
--top-p 0.95
--top-k 20
--min-p 0.0
--repeat-penalty 1.0        # 1.0 = отключен (thinking models)
--override-kv qwen35moe.context_length=int:589824  # снять hard cap на n_ctx_train
```

### VRAM (факт, 2026-04-28, parallel=2, ctx=589824, KV Q4_0, UD-Q4_K_XL)

```
GPU0: 30,260/32,768 MiB (92.3%)  — 1,9 GiB свободно
GPU1: 26,890/32,768 MiB (82.0%)  — 4,6 GiB свободно
GPU2: 26,838/32,768 MiB (81.9%)  — 4,6 GiB свободно
Total: 83,988/98,304 MiB (85.4%)
KV total: ~4,185 MiB (Q4_0, ctx=589824, 12 attn слоёв, 2 слота) — было 7,344 MiB при Q8_0
Веса: ~72 GiB (UD-Q4_K_XL)
```

### Скорость (production, 2026-04-28, UD-Q4_K_XL, parallel=2)

- Decode: **~41 tok/s** (stable, ctx=589824, parallel=2, warmed)
- Prompt (короткий): ~75 tok/s
- Prompt (длинный, >100K): **~25 tok/s** (PCIe bottleneck между 3 GPU)
- Cold-start: ~20-100s (зависит от warm cache)

> 23.9 tok/s — было при parallel=4, ctx=262144 (4×65536 слота).
> 42-47 tok/s — было при Q4_K_M, parallel=2.
> ~41 tok/s — текущая скорость при UD-Q4_K_XL, parallel=2 (10/10 OK качество).

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
| n_ctx_train | 262,144 (256K) — переопределён на 589,824 через override-kv |
| Thinking | ✅ hybrid |

---

## bm1 / bm2 — Qwen3.6-35B-A3B (general + vision)

| Параметр | Значение |
|---|---|
| Model | Qwen3.6-35B-A3B Q3_K_M + mmproj |
| GGUF path | `/models/Qwen3.6-35B-A3B-GGUF/Qwen_Qwen3.6-35B-A3B-Q3_K_M.gguf` |
| mmproj | `/models/Qwen3.6-35B-A3B-GGUF/mmproj-Qwen_Qwen3.6-35B-A3B-f16.gguf` |
| HF repo | `bartowski/Qwen_Qwen3.6-35B-A3B-GGUF` |
| Runtime | `ghcr.io/ggml-org/llama.cpp:server-cuda` |
| LB alias | `qwen36` |
| LB URL | `http://v100-host:4002/v1` |
| GPU | 1× RTX 3090 24GB (на каждом сервере) |

### llama.cpp параметры

```
--n-gpu-layers 100
--ctx-size 327680
--parallel 1
--mmproj mmproj-Qwen_Qwen3.6-35B-A3B-f16.gguf
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

### Скорость (production, 2026-04-24)

- Decode: **127.1 tok/s**
- Prompt: **1,501 tok/s**

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
| n_ctx_train | 262,144 (256K) — переопределён на 327,680 через override-kv |
| Thinking | ✅ hybrid |
| Vision | ✅ mmproj |

---

## Операционные команды

```bash
# V100 стек
bash /data/home/<user>/proj/llm-coding-upgrade/scripts/stack.sh restart
bash /data/home/<user>/proj/llm-coding-upgrade/scripts/stack.sh status
bash /data/home/<user>/proj/llm-coding-upgrade/scripts/stack.sh smoke

# LB proxy
bash /data/home/<user>/proj/llm-coding-upgrade/scripts/lb-stack.sh restart
curl http://localhost:4002/lb-status

# Проверка эндпоинтов
curl http://v100-host:4001/v1/models
curl http://v100-host:4002/v1/models
```

## Клиентская конфигурация

См. `client-setup.md`.
