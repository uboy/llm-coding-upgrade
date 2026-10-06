# BFCL v4 (non-live python) vs base gemma4-26B-A4B (2026-10-06)

Официальный Berkeley Function Calling Leaderboard против локальной модели
(gemma-4-26B-A4B-it Q4_K_M, llama.cpp server-cuda, GPU2 v100-host, fast mode).
Модель зарегистрирована под именем `google/gemma-3-27b-it` (тот же чат-формат;
токенизатор и config - негейтед зеркало unsloth, поданы через --local-model-path).

## Результаты (родной скоринг BFCL v4)

| Категория | Accuracy |
|---|---|
| simple_python | **94.00%** |
| multiple | 87.00% |
| parallel | 80.00% |
| parallel_multiple | 69.00% |
| irrelevance | 88.33% |
| **Non-Live Overall (этот прогон)** | **66.83%** |

BFCL сводит это в свой формат лидерборда: Gemma-3-27b-it (Prompt), Non-Live
Overall 66.83% (см. score/data_non_live.csv, Rank 1 в локальной таблице - других
моделей в ней нет).

## Вендор-патчи (исходники .orig-20261006 рядом)

1. `bfcl_eval/model_handler/local_inference/base_oss_handler.py`:
   `strip_channel_markers()` - gemma-4 протекает маркерами думания
   (`<|channel>thought ... <channel|>`) в raw-completion, без срезания декодер
   даёт 0% на простых вызовах (модель отвечала верно, парсер не мог распарсить).
2. Запуск только через `script -qec` (rich-CLI без TTY умирает молча) и с
   `--local-model-path` (гейтнутый google-репо требует авторизации HF).
3. Эндпоинт - переменные `LOCAL_SERVER_ENDPOINT/LOCAL_SERVER_PORT`
   (REMOTE_OPENAI_* в этом handler-е не используются).

## Как повторить

```
export LOCAL_SERVER_ENDPOINT=127.0.0.1 LOCAL_SERVER_PORT=8033
bfcl generate --model google/gemma-3-27b-it --test-category simple_python,... \
  --skip-server-setup --local-model-path /data/shared/<user>/models/tokenizers/gemma3
bfcl evaluate --model google/gemma-3-27b-it --test-category ...
```

Артефакты: result/*.json (сырые ответы), score/*.csv (таблицы BFCL), bfcl-eval.log.
Хост: контейнер g4-bench остался для идущего LCB-прогона (см. BFCL-LCB-RUN-STATE.md).
