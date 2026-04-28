# Протокол оценки качества coding-моделей

## Назначение

Этот протокол нужен для одного и того же сравнения:

- локальных production-моделей `qwen`, `qwen36`, `glm-5.1`;
- agent-first клиентов и внешних моделей `Codex` и `Claude`, которые будут прогоняться по тем же задачам;
- raw API и agentic workflow без подмены критериев под конкретный инструмент.

Полный каталог задач хранится в `evals/quality-task-catalog.json`.

## Что уже было в проекте

- `evals/benchmark-suite.json` – исторический 10-task Python prompt benchmark.
- `model-suite.evals.json` – direct checks и 3 executable Python fixtures.
- `eval-fixtures/` – сами Python-кейсы с видимыми тестами.
- `runs/live-eval-smoke-*` – текущие live-прогоны raw API по Python, C++, JS, TS и ArkTS.

## Канонические группы задач

### 1. Historical prompt suite

Назначение: continuity baseline, чтобы не потерять связь с ранними V100/BM сравнениями.

- тип: raw prompt quality
- язык: Python
- сложность: `medium` / `hard`
- ограничение: это не строгая executable-проверка; по нему нельзя принимать решение в одиночку

### 2. Direct short checks

Назначение: быстро проверить format adherence и короткое reasoning.

- `short_numbers`
- `edge_case_brainstorm`

### 3. Strict executable suite

Назначение: главный слой сравнения coding quality.

- Python: `case01_ttl_cache`, `case02_env_template`, `case03_json_patch`
- Python: `case04_rate_limiter`
- C++: `cpp_lru_cache`, `case05_cpp_lru_cache`
- JS: `js_retry_async`, `case06_js_retry_async`
- TS: `ts_event_bus`, `case07_ts_event_bus`
- ArkTS: `arkts_stage_page`
- exact-format/speed smoke: `speed_numbers`

### 4. Agentic fixture suite

Назначение: сравнить готовность реально работать как coding-agent, а не только как raw text generator.

- `case01_ttl_cache`
- `case02_env_template`
- `case03_json_patch`
- `case04_rate_limiter`
- `case05_cpp_lru_cache`
- `case06_js_retry_async`
- `case07_ts_event_bus`

Для agentic suite модель должна читать fixture, править только implementation file, запускать тесты, делать self-repair и останавливаться на рабочем состоянии.

## Приоритет критериев

Сравнение идёт в таком порядке:

1. `formal_solution`
2. `strict_correctness`
3. `hidden_correctness`
4. `agentic_autonomy`
5. `output_hygiene`
6. `speed`
7. `stability`

Это значит:

- если авто-тесты/compile-run не прошли, задача не считается формально решённой;
- если hidden-check или compile/run упал, задача считается непрошедшей независимо от скорости;
- speed важен только после correctness;
- historical prompt benchmark используется как фон, а не как финальный tie-breaker.

## `formal_solution`

Это главный бинарный verdict для tracked fixture-задач.

`formal_solution = true`, если одновременно выполнено всё:

- visible tests / compile-run passed;
- hidden check passed, если он сконфигурирован;
- test assets не были изменены моделью.

Для ArkTS сейчас `formal_solution` не вычисляется полноценно, потому что в этом репозитории пока нет compile/runtime harness для OpenHarmony UI; там остаётся rubric-based verdict.

## Правила оценки по типам задач

### Exact-match prompts

- pass только при точном совпадении ожидаемого текста;
- любой лишний prose, Markdown fence или reasoning в `content` = fail.

### Python fixtures

- pass только если `visible tests = pass` и `hidden check = pass`;
- отдельный visible-pass без hidden-pass фиксируется как partial signal, но не как final pass.
- для tracked fixture suite именно это и образует `formal_solution`, если тестовые файлы не менялись.

### C++ / JS / TS

- pass только если код собрался или выполнился и validation script завершился `0`;
- наличие полезного текста без compile/run pass не считается решением.
- для tracked fixture suite compile/runtime pass образует `formal_solution`, если тестовые файлы не менялись.

### ArkTS

Rubric из 6 пунктов:

- `@State` reactive state
- `aboutToAppear` initial load
- stable key in `ForEach`
- router params with item id
- loading UI
- empty state

Интерпретация:

- `6/6` – полностью корректно
- `5/6` – strong pass, можно принимать как рабочий draft
- `4/6` – частично корректно, требует ручной доводки
- `<=3/6` – fail

### Agentic fixtures

Для agentic run дополнительно фиксируются:

- число turns
- был ли self-repair после первого failing test
- запускались ли реальные tests/tools
- менялись ли только разрешённые implementation files

Минимальный pass для agentic task:

- implementation file создан или исправлен;
- tests запущены самим агентом;
- visible tests pass;
- hidden check pass.

## Поля, которые нужно сохранять для каждой модели

- `model_id`
- `client_or_transport`
- `endpoint_or_runner`
- `task_id`
- `language`
- `difficulty`
- `result`
- `visible_passed`
- `hidden_passed`
- `compile_or_runtime_passed`
- `arkts_score`
- `wall_time_s`
- `completion_tps_client`
- `server_tps` если есть
- `notes`

## Правила сравнения для завтрашних Codex и Claude

Завтра `Codex` и `Claude` должны прогоняться по тому же протоколу, а не по отдельному набору задач.

Обязательный минимум:

1. `speed_numbers`
2. `case01_ttl_cache`
3. `case02_env_template`
4. `case03_json_patch`
5. `case04_rate_limiter`
6. `cpp_lru_cache`
7. `case05_cpp_lru_cache`
8. `js_retry_async`
9. `case06_js_retry_async`
10. `ts_event_bus`
11. `case07_ts_event_bus`
12. `arkts_stage_page`
13. agentic `case01_ttl_cache`
14. agentic `case02_env_template`
15. agentic `case03_json_patch`
16. agentic `case04_rate_limiter`
17. agentic `case05_cpp_lru_cache`
18. agentic `case06_js_retry_async`
19. agentic `case07_ts_event_bus`

Дополнительно можно оставить `Q01..Q10` как continuity layer, но не заменять им strict suite.

## Источник истины

- task catalog: `evals/quality-task-catalog.json`
- текущие локальные результаты: `experiments/quality-eval-results-2026-04-28.md`
- исторический baseline: `experiments/model-comparison-full-2026-04-24.md`
