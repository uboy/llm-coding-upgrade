# Большие MoE на малом VRAM + turbo3/MTP + 284B: фазы 6-10 (2026-08-22/23)

Полный отчёт с матрицами: `<internal>/work/local-llm-inference/bigmodel-smallvram-2026-08-22.md`
(репозиторий трекера). Здесь - рецепты воспроизведения и ключевые числа.
Скрипты: `experiments/scripts-bigmodel-2026-08/` (bm1 = RTX 3090, v100 = v100-host GPU2).

## Итоговая рекомендация (владелец 2026-08-23)

- 3090 (bm1): **Qwen3.8-27B UD-Q4_K_M + turbo3-KV + draft-mtp n-max 2** - единственная
  постоянная модель (62 tk/s @8k, 44 tk/s @104k, до 160k ctx, JSON 5/5 в агентном eval).
- V100-хост: Qwen3.8-27B UD-Q6_K (качество) + DeepSeek-V4-Flash Q4 (284B консультант).
- gpt-oss-20b/120b удалены по решению владельца (старее, агентный JSON 3/5).

## Рецепт R4: Qwen3.8-27B Q4 + turbo3 + MTP на 3090 (24 GB)

Образ: `llamacpp-turboquant:fork` (Dockerfile.turboquant в scripts-bigmodel/bm1/,
форк TheTom/llama-cpp-turboquant, ветка feature/turboquant-kv-cache, arch 86).

```bash
docker run --gpus all -d -p 8081:8080 -v <models>:/models llamacpp-turboquant:fork \
  -m /models/qwen3.8-27b/UD-Q4_K_M.gguf -ngl 99 -c 131072 \
  --cache-type-k turbo3 --cache-type-v turbo3 \
  --spec-type draft-mtp --spec-draft-n-max 2 \
  --host 0.0.0.0 --port 8080
```

Замеры: 62.3 tk/s @8k (+46% к 42.6 baseline); 43.7 tk/s на 104k заполненного
контекста (2.03x к 21.6 без MTP); 19.2 tk/s на 124k без MTP; turbo3 = скорость
q8_0 при -1.4..-3.5 GB VRAM; needle 64k/128k чист. Имена типов turbo2/3/4
(НЕ tbqp3 из статей). Предел: 196k ctx + MTP не влезает (draft-KV), 262k - dead.

## Рецепт R5: V100 32 GB (GPU2, v100-host)

Тот же форк, Dockerfile.turboquant-v100 (arch 70). Qwen3.8-27B UD-Q6_K влезает
(21.0 GB VRAM, 16.5 tk/s, на 3090 OOM): -c 32768, KV q8_0, + draft-mtp n-max 2.
Long-ctx: 196k ctx + MTP = 26.5 tk/s @124k токенов (draft-KV влез на 32GB!),
262k ctx = 9.2 tk/s @166k токенов. turbo3 на V100 выигрыша по скорости НЕ даёт
(18.0 против 19.2 q8_0) - только экономия VRAM. MTP: +79% на 8k, 2.35x на 124k.

## Рецепт R6: DeepSeek-V4-Flash 284B на V100-хосте (llama.cpp mmap)

Веса: unsloth/DeepSeek-V4-Flash-0731-GGUF UD-Q4_K_XL (155 GB, 5 шардов) +
dspark-...-Q8_0.gguf (10.9 GB драфт). Скачивание: dl-deepseek.sh (aria2 -x16,
self-heal). Нужен СВЕЖИЙ llama.cpp (апрельские не знают deepseek_v4).

```bash
# базово: 6.0 tk/s, VRAM 8.9 GB, load 332 c
docker run --gpus '"device=2"' -d -p 8081:8080 -v <ds>:/models llamacpp-turboquant:v100 \
  -m /models/DeepSeek-V4-Flash-0731-UD-Q4_K_XL-00001-of-00005.gguf \
  -ngl 99 --n-cpu-moe 999 -c 8192 -ctk q8_0 -ctv q8_0 --host 0.0.0.0 --port 8080
# + DSpark спекуляция (-md ... -ngld 99 --spec-type draft-dspark --spec-draft-n-max 2):
#   8.7 tk/s (+44%, acceptance 0.584, lossless), VRAM 19.7 GB
```

Контекст: замер на 83k реальных токенов (2/3 от 131k): needle чист, decode
5.2-5.8 tk/s, prefill 71-74 ток/с (19 мин на 83k - главный лимит; radix-кэш
переиспользует префикс в диалоге). Нативный контекст модели 1M (MLA, KV ~33
КБ/ток: 83k = 2.7 GB).

## FreeToken (FlashML) на 3090: рецепт и вердикт

`uv pip install "freetoken[accel]"`, `ft serve --model <путь>` (ft-launch.sh).
Auto-конфиг сам выбрал offload+triton: gpt-oss-120b = 49 tk/s @21.8 GB VRAM,
58 GB RAM, init 4.5-15 мин (готовность = «API server is ready to serve» в логе,
/v1/models врёт). Без кэша экспертов (mr 0.40) = 21 tk/s - вся скорость даётся
LRU-кэшем экспертов. На cc 7.0 (V100) не работает: no kernel image. Веса
gpt-oss удалены 2026-08-23; для повтора - перекачать openai/gpt-oss-120b (58 GB).

## Агентный мини-eval (фаза 10)

agent-eval.py (scripts-bigmodel/bm1/agent-eval/): 5 машинно-проверяемых задач.
Qwen Q4 (3090) 5/5 и Q6 (V100) 5/5; gpt-oss-120b 4/5, JSON-стабильность 3/5
(t4-stab.py). Обвязка агента: max_tokens >= 3500 (reasoning-модели), retry на
невалидный JSON, radix-кэш.

## Границы/грабли (кратко; полностью - в <internal> gotchas G-A1..G-D3)

- HF-закачка с серверов душится per-connection ~1 МБ/с -> aria2c -x16.
- Вырожденный повторяющийся филлер -> мгновенный EOS при temp 0 (needle-якорь обязателен).
- Клиентский таймаут бенчмарка >= 7200 c для prefill 20+ мин.
- Весовой инвентарь после чистки 2026-08-23: bm1 = Qwen Q4_K_M + образы;
  v100-host = Qwen Q6_K + gpt-oss-120b-GGUF + DeepSeek Q4/dspark.
