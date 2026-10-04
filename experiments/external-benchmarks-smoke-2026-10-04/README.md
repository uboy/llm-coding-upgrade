# Прогон внешних бенчмарков против локальной gemma4 (2026-10-04)

Заказ владельца: «внешние бенчмарки нужны чтобы тестировать и локальные модели;
склонируй их и прогони для локальной gemma4 - проверить что вообще работает».
Модель: gemma-4-26B-A4B-it Q4_K_M (google base), llama.cpp server-cuda, GPU2
v100-host, :8033 (ctx 32k, KV q8, fast mode). Клоны:
`/data/home/<user>/proj/external-benchmarks/` (НЕ внутри репо).

## Результаты по бенчмаркам

| Бенчмарк | Статус | Результат | Комментарий |
|---|---|---|---|
| MMLU-Pro (API-форк evaluate_from_apiX) | **РАБОТАЕТ** | math 38.32% (n=167), cs 60% (n=5), health 80% (n=5) | math = 167 вопросов из первого запуска (раннер мерджит инкрементально); **max_tokens 2048 обрезал CoT - цифры занижены, это smoke трубы, не заявка о модели**; честный прогон: MMLUPRO_LIMIT=0 + max_tokens 16384 |
| IFEval (google-research, 50 первых промптов) | **РАБОТАЕТ** | strict 0.880, loose 0.880 | сильный результат; генератор - наш `scripts/run_ifeval_api.py`, скоринг - родной evaluation_main (subset-файл как input_data) |
| LiveCodeBench | склонирован, не прогнан | - | нужен HF-датасет + разбор lcb_runner (поддержка custom endpoint) |
| BFCL (gorilla) | склонирован, не прогнан | - | нужен pip install -e berkeley-function-call-leaderboard и его зависимости |

## Патчи вендорских раннеров (задокументированы, исходники .orig-20261004)

- `MMLU-Pro/evaluate_from_apiX.py` строка 40: `API_KEY = os.environ.get("OPENAI_API_KEY") or "dummy"`
  (SDK отвергает пустую строку; локальному серверу ключ не нужен).
- там же `load_mmlu_pro()`: env `MMLUPRO_LIMIT` = cap вопросов на категорию
  (to_pandas → groupby.head → Dataset.from_pandas); 0/пусто = полный сет.

## Как повторить (3 команды)

1. Поднять модель: docker run ... (рецепт в experiments/gemma4-uncensored-v100-2026-10-04.md).
2. MMLU-Pro: `external-benchmarks/run-mmlupro-local.sh http://127.0.0.1:8033/v1 "math,computer science" 16384 5`
3. IFEval: `python3 scripts/run_ifeval_api.py --base-url ... --limit 50 --out ...` →
   `python3 -m instruction_following_eval.evaluation_main --input_data=<subset> --input_response_data=<out> --output_dir=...`

## Вывод

Цепочка «локальная модель → внешний официальный бенчмарк → официальные метрики»
работает. Следующий шаг по желанию владельца: полный честный MMLU-Pro (14 категорий,
max_tokens 16384, ~15-20 тыс. генерируемых токенов на вопрос CoT - часы на 26B MoE)
и подключение LCB/BFCL.

Артефакты: ifeval-responses.jsonl, eval_results_{strict,loose}.jsonl, mmlupro-gemma4.log.
Хост после прогона: eval-контейнер удалён, GPU2 = v52-2 7.9 ГБ (исходное).
