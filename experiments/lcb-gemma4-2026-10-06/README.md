# LiveCodeBench release_v5 vs base gemma4-26B-A4B (2026-10-06/07)

Последний из четырёх внешних бенчмарков против локальной модели. Официальный
скорер LiveCodeBench (release_v5, codegeneration, 880 задач).

## Результат

- **pass@1 = 0.8364** (83.6%) - официальный скорер, файл
  `Scenario.codegeneration_1_0.2_eval.json`.
- Покрытие: 813/880 задач (92.4%); 67 задач не досчитались из-за таймаута
  клиента (600 с) на длинных генерациях при 4 слотах на одной карте. pass@1
  посчитан по решённым. n=1, temperature 0.2, max_tokens 4096.
- Генерация заняла 24 ч 20 мин (880 задач, 4 воркера на V100 32GB), оценка
  кода - 4 мин.

## Вендор-патчи (исходники *.orig-20261006 рядом)

1. `lcb_runner/runner/oai_runner.py`: base_url из env `OPENAI_BASE_URL` (раннер
   жёстко смотрел на api.openai.com) и n=codegen_n для codegeneration (раннер
   игнорировал codegen_n и слал args.n=10 - при 4 слотах сервера все запросы
   падали 400-й).
2. `lcb_runner/lm_styles.py`: entry `gemma4-26b-local` (LMStyle.OpenAIChat).
3. Сравнение сценария через `str(args.scenario).endswith(...)` (Scenario - enum).

## Окружение

- Изолированный venv `/data/home/user/proj/venvs/lcb` (anthropic==0.42.0 -
  у нового SDK нет нужных констант, datasets==2.21.0 - новые не умеют
  script-датасеты, CPU torch - раннеру нужен импорт даже для API-прогонов,
  vllm не требуется).
- Модель: gemma-4-26B-A4B-it Q4_K_M, llama.cpp server-cuda, GPU2, ctx 32k,
  --parallel 4, fast mode.

## Итоговая таблица внешних бенчмарков vs локальная gemma4-26B (все - официальные скореры)

| Бенчмарк | Класс (карта задач) | Результат |
|---|---|---|
| MMLU-Pro (12032 вопроса) | знания/экзамены | 82.0% overall (math 94.45) |
| IFEval (50 промптов) | следование инструкциям | 0.880 strict/loose |
| BFCL v4 non-live (900) | function calling | 66.83% overall (simple 94) |
| LiveCodeBench v5 (880) | код по описанию | pass@1 83.6% (n=1, 813/880) |

Оговорки: LCB - n=1 (не усреднение по 10), 7.6% задач вне покрытия; BFCL -
non-live часть без multi-turn; IFEval - 50 первых промптов. Все прогоны - одна
модель, один квант, fast mode.
