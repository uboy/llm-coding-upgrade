# Эксперимент: V100 RAM overflow — Qwen3.5-397B-A17B

> Дата: 2026-04-22
> Статус: **ЗАВЕРШЁН** — все 3 run выполнены

## Гипотеза

CPU RAM spillover линейно снижает decode speed пропорционально доле слоёв в RAM.
Интересно: при малом overflow (~10 GB) штраф может быть непропорционально большим
из-за PCIe bottleneck на layer sync.

При MoE-архитектуре (17B active из 397B total) активируется лишь подмножество экспертов —
часть слоёв может «везти»: оставаться в VRAM, даже если модель формально не влезает.
Это позволяет надеяться на умеренный штраф при небольшом overflow.

## Железо

- 3× Tesla V100 PCIE 32GB = 96 GB VRAM суммарно
- CPU RAM: уточнить перед запуском (`free -h`)
- PCIe: Gen3 x16

## Baseline

| Run | Модель | Кванти- зация | Размер | VRAM (96 GB) | CPU RAM overflow | Ожидаемая скорость |
|-----|--------|--------------|--------|--------------|------------------|--------------------|
| 0 — baseline | Qwen3-Coder-Next | Q5_K_S | 52 GB | 72 GB | 0 | **71 tok/s** (измерено) |

## Сетка тестов (Qwen3.5-397B-A17B)

| Run | Квантизация | Размер (факт) | GPU layers | CPU spillover (факт) | Decode tok/s | Prompt tok/s |
|-----|-------------|--------------|------------|----------------------|-------------|-------------|
| 1 | IQ1_M | 86 GiB | 60/61 | **0** | **29.4** | **43–45** |
| 2 | IQ2_XXS | 100 GiB | 52/61 | **15.6 GiB** | **10.3** | **36.6** |
| 3 | IQ2_XS | 111 GiB | 47/61 | **26.3 GiB** | **7.76** | **28.7** |

Дополнительная точка (при наличии времени):
- Qwen3.5-122B-A10B Q4_K_M (72 GB, путь: `/data/shared/<user>/models/Qwen3.5-122B-A10B-GGUF/`) —
  измерить фактическую скорость, задокументировать почему "слишком медленная".

## Методика измерения

**Контекст для эксперимента:** 8192 токенов (чистый замер скорости без влияния KV cache).

**Команда замера decode speed (llama-bench внутри контейнера):**
```bash
docker exec llamacpp-exp-p8002 /app/llama-bench \
  --model /models/Qwen3.5-397B-A17B-GGUF/IQ1_M/<filename>.gguf \
  -n 128 -p 512 \
  --n-gpu-layers 100 \
  --output json
```

**Замер через API (3 прогрева + 3 замера, среднее):**
```bash
# Прогрев × 3
for i in 1 2 3; do
  curl -s -X POST http://localhost:8002/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"local","messages":[{"role":"user","content":"Write a Python quicksort implementation."}],"max_tokens":200}' \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('usage',{}))"
done

# Смотреть tokens_per_second в логах
docker logs llamacpp-exp-p8002 --tail 30
```

**Мониторинг VRAM и RAM во время теста:**
```bash
# В отдельном терминале
watch -n 2 'nvidia-smi --query-gpu=memory.used,memory.free --format=csv && free -h'
```

## Скачивание моделей (на V100 хосте)

⚠️ Проверить свободное место перед скачиванием (~320 GB нужно для всех 3 квантизаций):
```bash
df -h /data/shared/<user>/
```

```bash
# Run 1: IQ1_M (~91.6 GB)
huggingface-cli download bartowski/Qwen_Qwen3.5-397B-A17B-GGUF \
  --include "*IQ1_M*" \
  --local-dir /data/shared/<user>/models/Qwen3.5-397B-A17B-GGUF/IQ1_M/

# Run 2: IQ2_XXS (~106.6 GB)
huggingface-cli download bartowski/Qwen_Qwen3.5-397B-A17B-GGUF \
  --include "*IQ2_XXS*" \
  --local-dir /data/shared/<user>/models/Qwen3.5-397B-A17B-GGUF/IQ2_XXS/

# Run 3: IQ2_XS (~118.7 GB)
huggingface-cli download bartowski/Qwen_Qwen3.5-397B-A17B-GGUF \
  --include "*IQ2_XS*" \
  --local-dir /data/shared/<user>/models/Qwen3.5-397B-A17B-GGUF/IQ2_XS/
```

## Команды запуска (для каждого Run)

Конфиг: `stack-exp-397b.env` — перед каждым run изменить `LLAMA_MODEL_PATH`.

```bash
# Остановить предыдущий эксперимент (если запущен)
docker stop llamacpp-exp-p8002 && docker rm llamacpp-exp-p8002

# Запустить Run N (подставить нужный путь к модели)
docker run -d --name llamacpp-exp-p8002 \
  --gpus '"device=0,1,2"' \
  --restart no \
  -v /data/shared/<user>/models:/models \
  -p 8002:8080 \
  ghcr.io/ggml-org/llama.cpp:server-cuda \
  --model /models/Qwen3.5-397B-A17B-GGUF/IQ1_M/<filename>.gguf \
  --ctx-size 8192 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --split-mode layer \
  --tensor-split 1,1,1 \
  --parallel 1 \
  --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0 \
  --host 0.0.0.0 --port 8080 \
  -ngl 100

# Проверка запуска
curl -s http://localhost:8002/health
docker logs llamacpp-exp-p8002 --tail 50
```

**Проверка продакшн стека (должен оставаться живым):**
```bash
curl http://localhost:4001/v1/models
curl http://localhost:4002/lb-status
```

## Результаты (выполнено 2026-04-22)

| Run | Квантизация | tok/s decode | tok/s prompt | TTFT (мс) | VRAM факт (GiB / 96) | RAM overflow факт (GiB) | ngl |
|-----|-------------|-------------|-------------|---------|----------------------|-------------------------|-----|
| 0 (baseline) | Q5_K_S (Qwen3-Coder-Next) | **71** | 183 | ~47s cold | 70/96 | 0 | 100 |
| 1 | IQ1_M (86 GiB) | **29.4** | **43–45** | **411** | 87.5/96 | **0** | 100 |
| 2 | IQ2_XXS (100 GiB) | **10.3** | **36.6** | **~780** | 86.7/96 | **15.6** | 52 |
| 3 | IQ2_XS (111 GiB) | **7.76** | **28.7** | **~960** | 87.3/96 | **26.3** | 47 |

### Детали по run'ам

**Run 1 (IQ1_M — 86 GiB, ngl=100, 0 RAM overflow)**
```
GPU0:  31460 MiB / 32768 MiB  (96.0%)
GPU1:  28932 MiB / 32768 MiB  (88.3%)
GPU2:  29210 MiB / 32768 MiB  (89.1%)
Total VRAM: 89,602 MiB (87.5 GiB / 96 GiB)

Decode (3 warmed runs): 29.37 / 29.17 / 30.60  → avg 29.7 tok/s
Prompt eval (warmed): 43–45 tok/s
TTFT: 411 ms
CPU_Mapped buffer: 0
```

**Run 2 (IQ2_XXS — 100 GiB, ngl=52, 15.6 GiB RAM overflow)**
```
load_tensors: offloaded 52/61 layers to GPU
CUDA0 model:     29,790 MiB
CUDA1 model:     28,134 MiB
CUDA2 model:     27,713 MiB
CPU_Mapped:      15,981 MiB  ← spillover
Total VRAM:  88,774 MiB (86.7 GiB / 96 GiB)

Decode (3 warmed runs): 10.26 / 10.43 / 10.25  → avg 10.3 tok/s
Prompt eval (warmed): 34.7 / 36.4 / 38.7  → avg 36.6 tok/s
TTFT: ~780 ms
```

**Run 3 (IQ2_XS — 111 GiB, ngl=47, 26.3 GiB RAM overflow)**
```
load_tensors: offloaded 47/61 layers to GPU
CUDA0 model:     29,553 MiB
CUDA1 model:     29,583 MiB
CUDA2 model:     27,097 MiB
CPU_Mapped:      26,973 MiB  ← spillover
Total VRAM:  89,406 MiB (87.3 GiB / 96 GiB)

Decode (3 warmed runs): 7.67 / 7.79 / 7.81  → avg 7.76 tok/s
Prompt eval (warmed): 26.0 / 30.1 / 29.9  → avg 28.7 tok/s
TTFT: ~960 ms
```

## Вывод

### Снижение decode speed от RAM overflow

| | vs baseline (71 tok/s) | vs Run 1 (29.4 tok/s, IQ1_M) |
|---|---|---|
| Run 1: IQ1_M, 0 GiB spillover | **–59%** (29.4 tok/s) | — |
| Run 2: IQ2_XXS, 15.6 GiB spillover | **–85%** (10.3 tok/s) | **–65%** |
| Run 3: IQ2_XS, 26.3 GiB spillover | **–89%** (7.76 tok/s) | **–74%** |

### Ключевые инсайты

1. **Гипотеза о линейности НЕ подтвердилась в чистом виде.** Первый переход (0 → 15.6 GiB,
   Run 1 → Run 2) даёт падение на 65%, следующий шаг (15.6 → 26.3 GiB) даёт только
   дополнительные –25% относительно Run 2. Т.е. первый факт наличия spillover —
   наиболее болезненный.

2. **Эффект смешан: квантизация + spillover.** IQ2_XXS/IQ2_XS — более высокобитные
   квантизации, чем IQ1_M, что само по себе требует чтения больше байт на токен.
   Разделить вклады без baseline-без-spillover для IQ2 невозможно на данном железе
   (100+ GiB модели не влезают в 96 GiB VRAM).

3. **PCIe bottleneck выраженный.** 15.6 GiB в CPU RAM = ~65% penalty — критично.
   Для продуктивного использования при overflow рекомендуется минимизировать spillover
   и оставлять PCIe как можно меньше загруженным.

4. **IQ1_M (29.4 tok/s) — рабочий вариант для 397B в данной конфигурации.**
   Подходит для batch/creative задач без строгих SLA. Для интерактивных задач —
   слишком медленно по сравнению с Qwen3.6-35B-A3B (~130 tok/s на RTX 3090).

5. **Architecture note:** `full_attention_interval=4` (15 attention layers из 60 блоков)
   значительно уменьшает KV cache. KV buffer при ctx=8192 = ~127 MiB — незначительно
   на фоне весов модели.
