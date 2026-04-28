# Decision Log

## Принятые решения

### D-001. Оставить клиентский алиас `qwen`

Статус: принято

Причина:

- упрощает cutover;
- не требует перенастройки клиентов;
- rollback делается быстро.

### D-002. Целевая модель первого внедрения – `Qwen3-Coder-Next Q5_K_S`

Статус: принято

Причина:

- это верхняя практичная планка качества под coding workload;
- размер всё ещё совместим с `3x V100-32GB`.

### D-003. Не выделять одну GPU строго под `KV-cache`

Статус: принято

Причина:

- при `split-mode layer` все `3 GPU` могут работать полезно;
- отдельная карта только под память не даёт лучшей общей экономики.

### D-004. Не выносить `KV-cache` в RAM по умолчанию

Статус: принято

Причина:

- это ухудшит latency;
- режим нужен только как fallback по памяти.

## Отложенные решения

### P-001. Оставаться на `ctx = 32768` или повышать

Статус: resolved

Решение:

- baseline на `32K` снят;
- runtime переведён на `196608`;
- новый режим влезает в VRAM и проходит smoke test.

### P-002. Поднимать ли `parallel` выше `1`

Статус: resolved → D-013

### D-005. Оставить `parallel = 1` на первом cutover

Статус: принято

Причина:

- так проще подтвердить baseline без смешивания эффектов очереди и shared slots;
- single-user baseline после прогрева оказался сильным: около `74.4 tok/s` на генерации;
- следующий этап для многопользовательского режима должен быть отдельным контролируемым экспериментом.

### P-003. Нужен ли откат к `Q4_K_M`

Статус: pending

Триггер:

- если `Q5_K_S` окажется слишком медленным или нестабильным.

### D-006. Поднять рабочий контекст до `196608` и оформить это через launcher

Статус: принято

Причина:

- `Qwen3-Coder-Next` обучен на большем контексте, чем `32K`;
- фактический `KV-cache` на `196608` укладывается в доступную VRAM;
- сохранён воспроизводимый способ заново поднять весь стек без ручной сборки команд.

### D-007. Считать первый completion после полного рестарта отдельным cold-start сценарием

Статус: принято

Причина:

- на `192K` первый короткий completion занял около `47.9 s` по `prompt eval`;
- повторный короткий completion вернулся к нормальной latency;
- оценивать UX нужно минимум по двум состояниям: сразу после рестарта и после прогрева.

### D-008. Tensor-split 1,1,1 вместо 2,2,1 на V100

Статус: принято (2026-04-11)

Причина:

- при 2,2,1 GPU0/GPU1 загружены на 84%/78%, GPU2 на 35%
- равномерный 1,1,1 даёт ~13 GB свободного VRAM на каждом GPU
- это открывает путь к ctx 524288 в будущем
- незначительная регрессия decode (~8%): 68 vs 74 tok/s — приемлема

### D-009. KV cache квантизация Q8 на V100

Статус: принято (2026-04-11)

Причина:

- F16 KV при 262144 ctx занимал ~6144 MiB, Q8 занимает 3264 MiB
- экономия ~3 GB VRAM без ощутимой потери качества или скорости
- согласует V100 с BM1/BM2, где Q8 стоял с самого начала

### D-010. Отказ от Q6_K_M на bm1/2

Статус: принято (2026-04-11)

Причина:

- Q6_K_M (20.6 GB) + mmproj (0.9 GB) = 21.5 GB весов
- при ctx=65536 с KV Q8 суммарно превышает 24 GB VRAM
- без mmproj можно запустить только при ctx ≤ 32768 — потеря vision и короткий контекст не оправдывают переход
- файл сохранён на BM2 как резерв, UD-Q6_K_XL удалён с обоих серверов (48 GB освобождено)

### D-011. Health check в LB proxy

Статус: принято (2026-04-11)

Причина:

- старый round-robin не знал о состоянии бэкендов
- при падении BM клиент получал 502 без fallback
- новый lb-proxy.js проверяет `/health` на каждом бэкенде каждые 15 с
- помечает unhealthy после 2 consecutive failures, восстанавливает автоматически
- добавлен `/lb-status` endpoint для мониторинга

### D-012. Все sampling параметры перенесены в stack.env

Статус: принято (2026-04-11)

Причина:

- `--reasoning on`, `--temp 0.6`, `--top-p 0.95`, `--top-k 20`, `--min-p 0.0` ранее прописывались вручную в docker run, но отсутствовали в stack.sh
- после `stack.sh restart` они терялись
- теперь все параметры хранятся в `stack.env` и применяются через `stack.sh`

### D-013. Поднять `parallel = 2` на V100

Статус: принято (2026-04-11)

Причина:

- при parallel=1 свободно ~10 GB VRAM на GPU0, ~13 GB на GPU1/GPU2 — ресурс не использовался
- parallel=2 добавляет второй слот инференса без дополнительного расхода VRAM (суммарный KV cache не меняется: 3264 MiB при ctx=262144)
- llama.cpp делит total ctx поровну: каждый слот получает n_ctx_seq = 131072 (128K токенов) — достаточно для кодинг-задач
- контекст выше 262144 не имеет смысла: модель обучена до этого предела
- flash_attn уже включён автоматически (CC7.0)
- два пользователя теперь могут работать одновременно без очереди
- на момент принятия каждый слот получал 131072 ctx (ctx-size=262144/2)

### D-014. Поднять `ctx-size = 524288` при `parallel = 2`

Статус: принято (2026-04-11)

Причина:

- при ctx=262144 и parallel=2 каждый слот получал только 131072 токенов — половину тренировочного контекста
- удвоение до ctx=524288 даёт каждому слоту ровно 262144 (= n_ctx_train) без RoPE-экстраполяции
- KV cache вырос с 3264 до 6528 MiB (Q8), или +1088 MiB на GPU — бюджет позволяет (GPU0: 73%)
- оба пользователя одновременно, каждый с полным 256K контекстом

### D-015. Остаться на Q5_K_S — не переходить на Q5_K_M или Q6_K

Статус: принято (2026-04-13) — **не пересматривать**

Причина:

- Q5_K_S vs Q5_K_M: разница в perplexity ~0.02–0.04 ppl — ниже порога субъективного восприятия на 80B модели.
  На практике неотличимо на coding-задачах (подтверждено llama.cpp сообществом и arxiv.org/abs/2601.14277).
- Q5_K_M потребует скачать дополнительно ~4 GB ради нулевого ощутимого улучшения.
- Q6_K (+15 GB) приближается к F16 по perplexity, но резко сокращает запас VRAM под KV cache и parallel slots.
- **Вердикт:** Q5_K_S — финальный выбор для V100. Возвращаться к этому вопросу нет смысла.

Источники:
- https://arxiv.org/abs/2601.14277 (unified quantization evaluation)
- https://github.com/ggml-org/llama.cpp/discussions/2094

### D-016. Speculative decoding — НЕСОВМЕСТИМО с Qwen3-Coder-Next

Статус: **закрыто — не применимо** (проверено 2026-04-13) — **не пересматривать**

Итог:

- Speculative decoding **протестирован** с draft-моделью `Qwen3-0.6B Q4_K_M` (462 MB, скачана в `/data/shared/<user>/models/Qwen3-0.6B-GGUF/`).
- `stack.sh` и `stack.env` обновлены с поддержкой optional draft; baseline при temp=0 сохранён в `runs/spec-baseline/`.
- При запуске llama.cpp выдал:
  ```
  common_speculative_is_compat: the target context does not support partial sequence removal
  srv    load_model: speculative decoding not supported by this context
  ```
- Сервер продолжает работать без spec decoding, но ускорения нет.

Причина несовместимости (архитектурная, не конфигурационная):

- Qwen3-Coder-Next использует **гибридную DeltaNet/SSM архитектуру**: `ssm_d_state=128`, `ssm_d_inner=4096` (подтверждено из GGUF metadata).
- Speculative decoding требует **отката KV-cache** при отклонении draft-токенов (`partial sequence removal`).
- SSM/recurrent слои хранят **полный рекуррентный state** — его невозможно откатить на N токенов назад без полного пересчёта. llama.cpp это не поддерживает для гибридных архитектур.
- Известное ограничение llama.cpp: issues [#20039](https://github.com/ggml-org/llama.cpp/issues/20039), [#19653](https://github.com/ggml-org/llama.cpp/issues/19653).
- Это ограничение **архитектуры модели**, не конфигурации — обойти без смены модели невозможно.

Что сделано:

- `stack.env`: блок spec decoding закомментирован с пояснением "НЕ раскомментировать".
- `stack.sh`: поддержка draft оставлена (может пригодиться для других моделей).
- `scripts/spec-decode-test.sh`: оставлен для будущих моделей.

Возврат к теме: только если будет замена основной модели на архитектуру без SSM/recurrent слоёв.

Источники:
- https://github.com/ggml-org/llama.cpp/issues/20039
- https://github.com/ggml-org/llama.cpp/issues/19653
- https://github.com/ggml-org/llama.cpp/discussions/10466

---

## Канонические sampling-параметры по моделям

> **Этот раздел — источник истины для параметров сэмплинга.**
> При любом споре или смене параметров — читать сначала сюда.

### Qwen3.5-122B-A10B (V100, alias `qwen`/`qwen35-122b`, порт 4001/8001)

```
--temp 0.6  --top-p 0.95  --top-k 20  --min-p 0.0
--jinja
```

**Почему именно эти значения:**

- `temp=0.6, top-k=20`: **официальные параметры thinking-режима** Qwen3 семейства.
  Qwen3.5-122B — полноценная thinking-модель, генерирует `<think/>` блоки.
- `top-p=0.95`: стандарт для Qwen3 thinking, без изменений.
- **НЕ добавлять `--repeat-penalty`**: в thinking-режиме повторение токенов — нормальный паттерн.
- **НЕ ставить `--reasoning off`**: модель thinking, jinja template обрабатывает thinking format.

**Источники:**
- https://huggingface.co/Qwen/Qwen3.5-122B — model card
- См. также D-026

### Qwen3.6-35B-A3B (bm1/2, alias `qwen36`, порт 4002)

```
--temp 0.6  --top-p 0.95  --top-k 20  --min-p 0.0
--reasoning on
--jinja
```

**Почему именно эти значения:**

- `temp=0.6`, `top-k=20`: **официальные параметры thinking-режима** Qwen3 семейства.
  Qwen3.6-35B — thinking-модель, генерирует `reasoning_content`.
- `--reasoning on`: корректно для этой модели — активирует отдельный `reasoning_content`.
- **НЕ добавлять `--repeat-penalty`**: повторение в reasoning chain — нормальный паттерн.

**Источники:**
- https://huggingface.co/Qwen/Qwen3.6-35B-A3B — model card

### ~~Qwen3-Coder-Next (предыдущая V100 модель)~~

> **Устарело.** Модель заменена на Qwen3.5-122B 2026-04-23. Параметры оставлены для справки.

```
--temp 1.0  --top-p 0.95  --top-k 40  --min-p 0.0  --repeat-penalty 1.1
--reasoning off
--jinja
```

Non-thinking модель. temp=1.0 для RL-обученной модели, top-k=40 для широкого candidate pool.

### ~~Qwen3.5-27B (предыдущая BM модель)~~

> **Устарело.** Заменена на Qwen3.6-35B-A3B 2026-04-22.

```
--temp 0.6  --top-p 0.95  --top-k 20  --min-p 0.0
--reasoning on
```

---

### D-017. Обзор рынка coding-моделей апрель 2026

Статус: **частично устарело** (Qwen3-Coder-Next заменена на Qwen3.5-122B 2026-04-23)

Вопрос: есть ли open-weight модель лучше Qwen3-Coder-Next именно для кодирования?

#### Сравнительная таблица (SWE-Bench Verified, апрель 2026)

| Модель | SWE-Bench | Total params | Active params | Мин. VRAM | Статус для нас |
|---|---|---|---|---|---|
| MiniMax M2.5 | 80.2% | 229B MoE | **10B** (8/256 экспертов) | ~126 GB (NVFP4) / 2×B200 full | ❌ не влезает |
| Claude Opus 4.6 | ~80.8% | проприетарная | — | только облако | ❌ не self-hosted |
| GLM-5 | 77.8% | 744B dense | — | ~1.5 TB | ❌ не влезает |
| Claude 4 | 77.2% | проприетарная | — | только облако | ❌ не self-hosted |
| Kimi K2.5 | 76.8% | **1T** MoE | 32B | ~240–380 GB unified / 2×H100 prod | ❌ не влезает |
| GPT-5 | 74.9% | проприетарная | — | только облако | ❌ не self-hosted |
| GLM-4.7 | 74.2% | 358B | — | мульти-GPU | ❌ не влезает |
| DeepSeek V3.2 | 70.2% | 671B MoE | — | мульти-GPU | ❌ не влезает |
| **Qwen3-Coder-Next** | **70.6%** | **80B MoE** | **3B** | **~52 GB (Q5_K_S)** | ✅ **наш текущий** |

> **Примечание по MiniMax M2.5:** 10B активных параметров — корректно. Архитектура: 256 экспертов, 8 активируются на каждый токен. Полный вес 229B, но inference дешевле, чем кажется. Для self-hosted всё равно нужно минимум ~126 GB VRAM при NVFP4 квантизации.
>
> **Примечание по Kimi K2.5:** 1 триллион параметров (1T), 32B активных. Disk: 600 GB; для production-grade inference нужно 2×H100 или 8×A100.

#### Вывод

**Qwen3-Coder-Next — Pareto-оптимальный выбор для 3× V100 32GB (96 GB VRAM).**
Всё, что превосходит его по SWE-bench, требует минимум 126 GB VRAM (MiniMax M2.5 NVFP4) или облачной инфраструктуры. Следующая ступень качества недостижима без смены железа.

> **Обновление 2026-04-24:** Coder-Next заменена на **Qwen3.5-122B-A10B Q4_K_M** (D-021).
> 122B thinking модель даёт лучшее качество кодинга. Скорость: 23.9 tok/s production.
> Полный бенчмарк: `experiments/model-comparison-full-2026-04-24.md`.
> DeepSeek V4-Flash (158B, Q4 ~73.6 GiB) — потенциальная замена, GGUF пока нет.

#### Что нужно перепроверить

- [ ] Актуальность benchmarks: рынок coding-моделей меняется быстро — сверить через ~3 месяца или при появлении новых open-weight моделей
- [ ] Появление новых MoE-моделей с малым active-param footprint (~3–5B), которые могут влезть в 96 GB
- [ ] GGUF-квантизации для MiniMax M2.5 — если выйдет Q4_K_M с footprint ≤90 GB (маловероятно при 229B total)
- [ ] GLM-4.7 / GLM-5 GGUF quantizations — пока нет данных о доступных llama.cpp-совместимых форматах

Источники:
- Qwen3-Coder-Next technical report — https://arxiv.org/html/2603.00729v1
- Qwen3-Coder-Next официальный блог — https://qwen.ai/blog?id=qwen3-coder-next
- Best open-source coding model 2026 сравнение — https://www.morphllm.com/best-open-source-coding-model-2026
- Kimi K2.5 vs Qwen3-Coder-Next — https://www.openaitoolshub.org/en/blog/kimi-k2-5-vs-qwen3-coder-next
- MiniMax M2.5 официальный анонс — https://www.minimax.io/news/minimax-m25
- MiniMax M2.5 VRAM/specs — https://apxml.com/models/minimax-m2
- MiniMax M2.5 Unsloth guide — https://unsloth.ai/docs/models/minimax-m25
- Kimi K2.5 VRAM requirements — https://apxml.com/models/kimi-k25
- Kimi K2.5 Unsloth guide — https://unsloth.ai/docs/models/kimi-k2.5
- Best AI coding models SWE-bench leaderboard — https://localaimaster.com/models/best-ai-coding-models

---

### D-018. Апгрейд bm1/2: Qwen3.5-27B Q5_K_M → Qwen3.6-35B-A3B Q3_K_M

Статус: принято (2026-04-22)

**Причина:**

- Qwen3.6-35B-A3B — MoE-модель (35B total / 3B active); при меньшем VRAM-следе даёт
  качество dense-модели ~35B класса
- Q3_K_M (16.23 GB) + mmproj (0.90 GB) оставляет ~6.9 GB под KV cache → ~98K контекст
  при 24 GB VRAM RTX 3090 — сохранена текущая рабочая точка
- IQ4_XS (18.81 GB) не рассмотрена: оставляет лишь ~4.3 GB под KV → контекст ~65K,
  ниже текущего 98K — потеря без компенсации
- Multimodal сохранён: `mmproj-Qwen_Qwen3.6-35B-A3B-f16.gguf` доступен в том же GGUF-репо
- Sampling-параметры не изменяются: Qwen3.6 — thinking-модель, те же
  `temp=0.6, top-k=20, reasoning on` корректны

**Изменения:**

- `lb-proxy.env`: `LB_PROXY_MODEL_ALIAS=qwen36`, `LB_PROXY_REAL_MODEL=Qwen_Qwen3.6-35B-A3B-Q3_K_M.gguf`
- `current-state.md`, `config-card.md`: bm секция обновлена
- Деплой: скачать на каждый сервер через `huggingface-cli`, перезапустить контейнер

**Примечание про alias:** alias сменился с `qwen27b` на `qwen36`. Клиентские конфиги
(Cline, Continue, OpenWebUI) необходимо обновить. При критичности обратной совместимости —
можно временно вернуть старый alias (модель всё равно будет правильной — лишь имя отвечает).

**Команды деплоя на bm (одинаково для BM1 и BM2):**
```bash
# 1. Скачать модель и mmproj
mkdir -p /home/<user>/models/Qwen3.6-35B-A3B-GGUF
huggingface-cli download bartowski/Qwen_Qwen3.6-35B-A3B-GGUF \
  --include "Qwen_Qwen3.6-35B-A3B-Q3_K_M.gguf" \
  --local-dir /home/<user>/models/Qwen3.6-35B-A3B-GGUF/
huggingface-cli download bartowski/Qwen_Qwen3.6-35B-A3B-GGUF \
  --include "mmproj-Qwen_Qwen3.6-35B-A3B-f16.gguf" \
  --local-dir /home/<user>/models/Qwen3.6-35B-A3B-GGUF/

# 2. Остановить старый контейнер
docker stop llamacpp-server-p8001 && docker rm llamacpp-server-p8001

# 3. Запустить новый
docker run -d --name llamacpp-server-p8001 \
  --gpus all --restart unless-stopped \
  -v /home/<user>/models:/models \
  -p 8001:8080 \
  ghcr.io/ggml-org/llama.cpp:server-cuda \
  --model /models/Qwen3.6-35B-A3B-GGUF/Qwen_Qwen3.6-35B-A3B-Q3_K_M.gguf \
  --mmproj /models/Qwen3.6-35B-A3B-GGUF/mmproj-Qwen_Qwen3.6-35B-A3B-f16.gguf \
  --ctx-size 98304 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --batch-size 1024 --ubatch-size 256 \
  --parallel 1 --reasoning on --temp 0.6 \
  --top-p 0.95 --top-k 20 --min-p 0.0 \
  --host 0.0.0.0 --port 8080 -ngl 100 --jinja

# 4. Smoke test
curl -s http://localhost:8001/health
curl -s http://localhost:8001/v1/models
```

---

### D-019. Эксперимент: V100 RAM overflow с Qwen3.5-397B-A17B

Статус: **завершён** (все 3 Run выполнены 2026-04-22)

**Цель:**

Измерить фактический штраф decode speed от CPU RAM spillover на 3× V100 32GB (96 GB VRAM),
используя Qwen3.5-397B-A17B (397B total / 17B active MoE) в трёх квантизациях.

**Гипотеза:** штраф не строго линеен — при небольшом overflow PCIe bottleneck
может давать непропорционально большую деградацию.

**Результаты:**

| Run | Квантизация | Файл (GiB) | GPU layers | VRAM факт (GiB) | RAM overflow (GiB) | Decode tok/s | Prompt tok/s | TTFT |
|-----|-------------|-----------|------------|-----------------|---------------------|-------------|-------------|------|
| 0 baseline | Qwen3-Coder-Next Q5_K_S | 52 | 100 | 70/96 | 0 | **71** | 183 | ~47s cold |
| 1 ✅ | IQ1_M | 86 | 60/61 | 87.5/96 | **0** | **29.4** | 43–45 | 411 мс |
| 2 ✅ | IQ2_XXS | 100 | 52/61 | 86.7/96 | **15.6** | **10.3** | 36.6 | ~780 мс |
| 3 ✅ | IQ2_XS | 111 | 47/61 | 87.3/96 | **26.3** | **7.76** | 28.7 | ~960 мс |

**Архитектурное открытие:** Qwen3.5-397B имеет `full_attention_interval=4` (15 attention слоёв
из 60 блоков). KV cache при ctx=8192 = ~127 MiB — минимальный. Это позволило максимизировать
VRAM под веса модели.

**Методология Runs 2-3:** ngl снижен ниже block_count для принудительного CPU spillover.
Calc: ngl = floor((VRAM_budget - fixed_overhead) / file_size × n_blocks).
Run 2: ngl=52, Run 3: ngl=47.

**Важно:** Эксперимент требует остановки prod V100 контейнера (~1 ч 40 мин суммарно).
Prod стек восстановлен после каждого run.

**Конфиг:** `stack-exp-397b.env` (контейнер `llamacpp-exp-p8002`, порт 8002)
**Полный дизайн-документ с анализом:** `experiments/v100-ram-overflow-397b-exp.md`

**Вывод:**
Гипотеза частично подтвердилась — первый факт spillover (0 → 15.6 GiB) снижает decode
на 65% (vs Run 1), следующий шаг (15.6 → 26.3 GiB) даёт дополнительные 25%. Зависимость
убывающая, но не строго линейная. IQ1_M (29.4 tok/s, 0 spillover) — рабочий вариант
для 397B на данном железе. IQ2+ с overflow неприемлемы для интерактивных задач.

---

### D-020. Поднять ctx-size до 262144 на bm1/2

Статус: принято (2026-04-22)

**Причина:**

- После апгрейда на Qwen3.6-35B-A3B Q3_K_M VRAM оказалась 76% вместо ожидаемых 97%
- Причина: гибридная архитектура (SSM/recurrent) — только 10 из 40 слоёв имеют KV-кеш
  (`full_attention_interval=4`), остальные 30 — recurrent с фиксированным RS buffer
- KV при ctx=98304: 1,020 MiB (vs ~5,500 MiB у Qwen3.5-27B dense-трансформера)
- `n_ctx_train=262144` — модель обучена на 256K токенах, экстраполяции нет
- KV при ctx=262144: 2,720 MiB — всё ещё комфортно
- Итоговый VRAM: 83% (20.4 / 24.6 GB) — запас сохранён

**Замер KV на токен:** 10,240 bytes/token = 2 × 10 layers × 2 KV heads × 256 head_dim × 1 byte (Q8)

**Контекст:** 98304 → 262144 (256K) = +2.67×

---

### D-021. Замена V100 prod: Qwen3-Coder-Next → Qwen3.5-122B-A10B Q4_K_M

Статус: принято (2026-04-23)

**Причина:**

Сравнение 5 моделей по скорости и качеству кодинга выявило неэффективность текущей модели:

| Модель | Decode tok/s | Thinking | Q2 bugs (из 3) |
|--------|-------------|---------|----------------|
| Qwen3-Coder-Next Q5_K_S (предыдущий) | 71 | ❌ нет | 1/3 |
| **Qwen3.5-122B Q4_K_M (новый)** | **44.5** | **✅ да** | **3/3** |
| Qwen3.5-397B IQ1_M | 29.4 | ✅ да | 1-2/3 |

**Ключевые аргументы:**
- 122B Q4_K_M находит тонкие баги (assert -O, get() lock), которые Coder-Next и 397B IQ1_M пропускают
- Thinking включён: глубокий reasoning chain перед ответом
- 397B IQ1_M хуже по обоим параметрам: медленнее (29.4 < 44.5 tok/s) и хуже качество — агрессивная квантизация нивелирует преимущество большего размера
- VRAM: 70.5/96 GiB (73%) — 25.5 GiB запаса (vs 87.5/96 GiB для IQ1_M)

**Параметры запуска:**
```bash
docker run -d --name llamacpp-server-p8001 \
  --gpus all --restart unless-stopped \
  -v /data/shared/<user>/models:/models \
  -p 8001:8080 \
  ghcr.io/ggml-org/llama.cpp:server-cuda \
  -m /models/Qwen3.5-122B-A10B-GGUF/Q4_K_M/Qwen3.5-122B-A10B-Q4_K_M-00001-of-00003.gguf \
  --host 0.0.0.0 --port 8080 \
  --n-gpu-layers 100 --split-mode layer --tensor-split 1,1,1 \
  --ctx-size 262144 --cache-type-k q8_0 --cache-type-v q8_0 \
  --alias qwen35-122b \
  --parallel 4 --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0 --jinja
```

**Сравнение с bm (Qwen3.6-35B Q3_K_M):**
- BM1 быстрее (130 tok/s vs 44.5 tok/s) из-за RTX 3090 vs V100 + меньшая модель
- Качество сопоставимо: оба на высоком уровне, BM1 лучше по скорости, V100 иногда глубже по design
- V100 122B имеет больший knowledge base (122B vs 35B параметров)

**Клиентам:** использовать `max_tokens ≥ 4000` для coding задач (thinking chain занимает 2000-3000 токенов).

---

---

### D-022. MiniMax-M2.7 UD-IQ3_S — протестирован, не заменяет прод

Статус: принято (2026-04-23)

**Контекст:** протестирован как альтернатива для V100 prod по просьбе.

**Результаты тестирования:**

| Метрика | MiniMax M2.7 UD-IQ3_S | Qwen3.5-122B Q4_K_M |
|---------|----------------------|---------------------|
| Decode tok/s | 39.2 | **44.5** |
| Prompt tok/s | **244** | 128 |
| VRAM | 80.6/96 GiB | **70.5/96 GiB** |
| Q1 LRU | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Q2 bugs found | **3/3** | **3/3** |
| Q3 rate limiter | ⭐⭐⭐⭐ (no time_func) | ⭐⭐⭐⭐⭐ |
| Max ctx | 192K | 262K |

**Вывод:** Qwen3.5-122B Q4_K_M остаётся в проде.

**Аргументы против замены:**
- Decode на 12% медленнее (39.2 vs 44.5 tok/s) — для streaming-ответов это ощутимо
- Занимает больше VRAM (80.6 vs 70.5 GiB → меньше запас для ctx/parallel)
- Качество практически идентично (оба 3/3 на Q2, оба ⭐⭐⭐⭐⭐ на Q1)
- Архитектура `minimax-m2` (62 слоёв) поддерживается в llama.cpp build ≥ b8022

**Когда MiniMax предпочтительнее 122B Q4_K_M:**
- Workload с длинными prompts + короткими ответами (prompt 244 vs 128 tok/s → в 2× быстрее TTFT)
- RAG или large context retrieval сценарии

**MiniMax хранится на диске** (`/data/shared/<user>/models/MiniMax-M2.7-GGUF/UD-IQ3_S/`, 78 GiB).
Для активации: остановить prod, запустить на порту 8001 с теми же параметрами, заменив путь к модели.

---

### D-023. Полный бенчмарк V100 vs BM — 10 задач + speed (2026-04-24)

Статус: **зафиксировано**

**Методология:** `/tmp/fullbench.py`, 3 warmup + 3 measured decode, 10 quality tasks, max_tokens=7000.

**Результаты:**

| Метрика | V100 (122B Q4) | BM (35B Q3) |
|---------|----------------|-------------|
| Decode tok/s | **23.9** | **127.1** |
| Prompt tok/s | ~128 (пред.) | **1,501** |
| OK (content>500) | **9/10** | 6/10 |
| EMPTY (content=0) | 1/10 | 3/10 |
| Avg content (OK) | **9,101 chars** | 5,819 chars |
| Thinking overflow | 1 задача (Q04) | 4 задачи (Q02,Q04,Q08,Q09) |

**Ключевое открытие — V100 production speed:**
Ранее 44.5 tok/s (ctx=8192/parallel=1) → реально 23.9 tok/s (ctx=262144/parallel=4).
Разница из-за большого KV footprint (3,264 MiB) и overhead 4 parallel slots.
44.5 — benchmark в идеальных условиях. 23.9 — реальная production скорость.

**Ключевое открытие — BM thinking overflow:**
Qwen3.6-35B Q3_K_M на 4/10 сложных задач (bug fix, async, retry, connection pool)
потребляет весь 7000-токенный budget на thinking chain, оставляя content = 0.
V100 122B справляется лучше: только 1/10 overflow.

**Полный отчёт:** `experiments/model-comparison-full-2026-04-24.md`

---

### D-024. V100: снизить parallel 4→2, увеличить ctx-size (2026-04-24)

Статус: **выполнено**

**Проблема:** `--parallel 4 --ctx-size 262144` → ctx_per_slot = 65536. Запрос в 262K токенов отклоняется.

**Решение:**
```
--parallel 2 --ctx-size 589824
--override-kv qwen35moe.context_length=int:589824
→ ctx_per_slot = 294,912 (хватает на 262K+ запросы)
→ VRAM: GPU0 31,412/32,768 MiB (95.8%)
```

KV cache вырос: 3,264 → 7,344 MiB (+4,080 MiB). Умещается.
Decode speed: 23.9 → 42-47 tok/s (+76-96%).

**Tradeoff:** 2 одновременных пользователя вместо 4, но каждый с 295K контекстом.

**override-kv:** llama.cpp автоматически capped n_ctx_seq до n_ctx_train (262144).
`--override-kv` переопределяет метаданные модели, снимая cap.
Контекст сверх 262K (до 295K) использует RoPE-экстраполяцию — +12.5% сверх обучения,
минимальное влияние на качество (только attention-слои, 12/48).

**Ограничение:** prompt processing на длинных промптах (>100K) = ~25 tok/s.
265K промпт обрабатывается ~3 часа. Это ограничение PCIe (no NVLink), не контекста.

---

### D-025. BM1/2: увеличить ctx-size 262144→327680 (2026-04-24)

Статус: **выполнено**

**Проблема:** ctx=262144 insufficient для запросов >256K токенов.

**Решение:**
```
--ctx-size 327680
--override-kv qwen35moe.context_length=int:327680
→ 328K ctx per slot
→ VRAM: BM1 21,195/24,576 MiB (86.2%), BM2 21,128/24,576 MiB (85.9%)
```

KV cache вырос: 2,720 → 3,400 MiB (+680 MiB). Запас VRAM достаточный.

**override-kv:** llama.cpp автоматически capped n_ctx_seq до n_ctx_train (262144).
`--override-kv` снимает cap. Контекст до 328K (+25% сверх обучения).

---

### D-026. Sampling параметры для Qwen3.5-122B (V100)

Статус: **подтверждено (2026-04-24)**

```
--temp 0.6  --top-p 0.95  --top-k 20  --min-p 0.0
--jinja
```

**Почему:**
- Qwen3.5-122B — thinking-модель, генерирует `<think/>` блоки
- `temp=0.6, top-k=20`: официальные параметры thinking-режима Qwen3 семейства
- `--jinja`: нативный chat template для корректного tool-calling и thinking format
- **НЕ добавлять `--repeat-penalty`**: в thinking-режиме повторение токенов — нормальный паттерн
- **НЕ ставить `--reasoning off`**: модель thinking, `--reasoning` может быть опущен (jinja обрабатывает)

**Источники:**
- https://huggingface.co/Qwen/Qwen3.5-122B — model card

---

### D-027. override-kv для снятия context cap (2026-04-24)

Статус: **принято**

**Проблема:** llama.cpp capped n_ctx_seq до n_ctx_train (262144) независимо от --ctx-size.
Это блокировало запросы >262K токенов даже при наличии VRAM.

**Решение:** `--override-kv qwen35moe.context_length=int:<ctx_size>` переопределяет
метаданные модели, сообщая llama.cpp что модель «обучена» на больший контекст.

**Применено:**
- V100: override=589824 (parallel=2 → 294,912/slot)
- BM1/2: override=327680 (parallel=1 → 327,680/slot)

**Риски:** контекст сверх реального n_ctx_train (262K) использует RoPE-экстраполяцию.
Для SSM-моделей (только ~25% слоёв — attention) влияние минимально:
- V100: +12.5% сверх обучения — пренебрежимо
- BM: +25% сверх обучения — умеренный риск, только на позициях >262K

---

### D-028. NVLink на V100 сервере — недоступен (2026-04-24)

Статус: **подтверждено — не применимо**

**Факты:**
- GPU: 3× Tesla V100 PCIE 32GB (GV100GL)
- nvidia-smi topo: SYS/NODE (все через PCIe, no NVLinks)
- Bridge Chip: N/A (физические NVLink-мосты отсутствуют)
- Tesla V100 PCIe поддерживает NVLink 2.0 аппаратно (2 links, до 300 GB/s bidirectional)

**Для NVLink потребуются:**
- Физические NVLink-мосты (DLL-NVLINK-Bridge для V100)
- Сервер с правильным расположением PCIe-слотов (adjacent slots)
- Возможно: замена материнской платы/сервера

**Альтернативы NVLink для ускорения multi-GPU inference:**
- RPC-режим llama.cpp (отдельный сервер на GPU) — не даёт преимуществ при layer split
- Замена сервера на платформу с NVLink (DGX-1, HGX) — капитальные затраты
- Замена на единый GPU большего объёма (A100 80GB, H100) — устраняет PCIe bottleneck

---

### D-029. stack.env обновлён под Qwen3.5-122B (2026-04-24)

Статус: **выполнено**

**Изменения:**
- Model path: Qwen3-Coder-Next → Qwen3.5-122B-A10B Q4_K_M
- Models dir: `/data/shared/<user>/models` → `/data/shared/<user>/models`
- ctx-size: 1048576 → 589824
- parallel: 4 → 2
- temp: 1.0 → 0.6
- top-k: 40 → 20
- reasoning: off → on
- repeat-penalty: 1.1 → 1.0
- proxy real model: Qwen3-Coder-Next → Qwen3.5-122B-A10B Q4_K_M
- Добавлен: LLAMA_OVERRIDE_KV=qwen35moe.context_length=int:589824

**stack.sh обновлён:** добавлена поддержка `${LLAMA_OVERRIDE_KV:+--override-kv "$LLAMA_OVERRIDE_KV"}`.

---

### D-030. ai-targets.conf: обновлены GLM модели (2026-04-24)

Статус: **выполнено**

**Изменения:**
- OPUS: glm-5 → **glm-5.1** (флагман, $1.4/$4.4 per Mtok)
- SONNET: glm-4.7 (без изменений)
- HAIKU: glm-4.5-air → **glm-4.7-flash** (FREE tier)

**Файл:** `/data/shared/common/scripts/ai-targets.conf`

---

### D-031. Batch size tuning: -b 2048 -ub 512 для V100 (2026-04-28)

Статус: **реализовано и протестировано**

**Причина:**

Статья на Хабр (https://habr.com/ru/articles/1025132/) демонстрирует ускорение PP speed при увеличении `-ub/-b`. Для нашего стека с 3× V100 32GB и ctx=589824:

- `ubatch=2048` — **вызывает OOM** (compute buffer растёт с ~350 MiB до 10,985 MiB на GPU0)
- `ubatch=512` — безопасно, не вызывает OOM

**Изменения:**
- `stack.env`: `LLAMA_BATCH_SIZE=2048`, `LLAMA_UBATCH_SIZE=512`
- `stack.sh`: добавлены параметры `--batch-size` и `--ubatch-size` в docker run команду

**Результат:**
- Decode: 42-43.5 tok/s (без изменений)
- PP (144 tokens): 50-170 tok/s (было ~31-134 tok/s)
- VRAM: без изменений

**Источник:** https://habr.com/ru/articles/1025132/

---

### D-033. KV cache Q4_0 вместо Q8_0 (2026-04-28)

Статус: **реализовано и протестировано**

**Причина:**

KV cache Q4_0 вместо Q8_0 экономит ~50% памяти KV cache. Для нашего стека:
- Q8_0 KV: ~7,344 MiB (3 attention sections × 2 KV heads × 128 head_dim × 589824 ctx × 1 byte × 2 slots)
- Q4_0 KV: ~4,185 MiB (те же формулы × 0.5 byte)
- **Экономия: ~3,159 MiB (3.1 GiB)**

**Результаты замеров:**

| Метрика | Q8_0 (до) | Q4_0 (после) | Разница |
|---------|-----------|-------------|---------|
| Decode | 42-43.5 tok/s | 42.6-43.5 tok/s | без изменений |
| PP (144 tokens) | 50-170 tok/s | 134-136 tok/s | без изменений |
| VRAM GPU0 | 31,412 MiB (95.8%) | 29,515 MiB (90.0%) | **-1,897 MiB** |
| VRAM GPU1 | 28,042 MiB (85.6%) | 26,580 MiB (81.1%) | **-1,462 MiB** |
| VRAM GPU2 | 27,520 MiB (84.0%) | 26,057 MiB (79.5%) | **-1,463 MiB** |
| VRAM Total | 86,974 MiB (88.5%) | 82,152 MiB (83.6%) | **-4,822 MiB** |
| Качество (Q01) | 9,863 chars | 9,863 chars | без изменений |

**Изменения:**
- `stack.env`: `LLAMA_CACHE_TYPE_K=q4_0`, `LLAMA_CACHE_TYPE_V=q4_0`

**Преимущества:** 3+ GiB свободного VRAM на каждом GPU. Это даёт запас для:
- Увеличения ctx сверх 589824
- Увеличения parallel до 3
- Более крупных batch sizes

**Риски:** ~0.05 ppl degradation (пренебрежимо для SSM-моделей, где только 25% слоёв — attention).

---

### D-034. ncmoe уже включён через --fit on (2026-04-28)

Статус: **подтверждено — уже оптимизировано**

**Проверка:** `--fit on` автоматически включает ncmoe для MoE моделей. Все 49/49 слоёв оффложены на GPU. Дополнительных изменений не требуется.

Статус: **выполнено**

**Удалено (устаревшее/дублирующееся):**
- `design.md`, `implementation-plan.md`, `benchmark-plan.md`, `benchmark-results.md` — выполненные планы
- `model-comparison-wave1.md`, `opencode-eval-results.md` — заменены experiments/
- `stack-transfer-to-3090.md`, `rollback-plan.md` — устаревшие гайды
- `current-state.md` — объединён в README.md
- `artifacts/`, `.scratchpad/`, `coordination/`, `.agent-memory/` — исторические артефакты агентов

**Обновлено:**
- `README.md` — переписан как единый входной документ
- `client-setup.md` — исправлены alias: qwen27b → qwen36, обновлены contextLength
- `automation.md` — обновлены candidates под текущие модели
- `references.md` — добавлены ссылки на Хабр статью, Qwen3.5-122B, ik_llama
- `docs/llm-glossary.md` — расширено: ncmoe, UD-кванты, spec-decoding, ik_llama, batch size

**Создано:**
- `docs/optimization-research.md` — выводы по статье Хабр + план оптимизаций
- `evals/benchmark-suite.json` — 10 задач для оценки качества до/после
- `scripts/v100-benchmark.sh` — скрипт бенчмарка V100 (speed + quality)

---

## Открытые вопросы

- DeepSeek V4-Flash GGUF availability — перепроверить через ~1 неделю (unsloth/bartowski)
- BM thinking overflow mitigation — протестировать с max_tokens=12000 и/или `/no_think`
- Cold-start после рестарта V100 (~20-100s) — принят как рабочее ограничение
- V100 prompt processing bottleneck (~25 tok/s на длинных промптах) — аппаратное ограничение (PCIe, no NVLink)
- UD-Q4_K_XL для Qwen3.5-122B-A10B — проверить наличие на HuggingFace (unsloth)
- KV cache Q4_0 — протестировать экономию ~3.5 GiB vs падение качества
- ik_llama.cpp для CC 7.0 — оценить целесообразность сборки
