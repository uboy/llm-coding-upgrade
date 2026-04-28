# Результаты quality eval – 2026-04-28

## Scope

Этот отчёт фиксирует:

- какие задачи реально используются для сравнения;
- какие результаты уже получены по локальным моделям;
- какие слоты подготовлены под завтрашние прогоны `Codex` и `Claude`.

Важно:

- measured таблицы ниже отражают уже выполненные прогоны на исходном strict suite;
- после этого в репозиторий добавлены новые tracked formal fixtures `case04_rate_limiter`, `case05_cpp_lru_cache`, `case06_js_retry_async`, `case07_ts_event_bus`;
- для них auto-tests и criterion `formal_solution` уже заведены, но сами model runs по ним ещё не выполнялись на локальных моделях.

Канонический task catalog: `evals/quality-task-catalog.json`
Канонический протокол: `docs/quality-evaluation-protocol.md`

## Targets

| Target | Transport | Status | Source |
|--------|-----------|--------|--------|
| `qwen_raw` | local raw API (`qwen`), max_tokens=5000 | measured | `runs/live-eval-smoke-qwen-default/summary.json` |
| `qwen_16k` | local raw API (`qwen`), max_tokens=16384 | **measured** | `runs/max-tokens-16k-test/summary.json` |
| `qwen_no_think` | local raw API (`qwen` + `/no_think`), max_tokens=5000 | measured | `runs/live-eval-smoke-qwen-nothink/summary.json` |
| `qwen36_raw` | local raw API (`qwen36`), max_tokens=5000 | measured | `runs/live-eval-smoke-qwen36/summary.json` |
| `qwen36_no_think` | local raw API (`qwen36` + `/no_think`), max_tokens=5000 | measured | `runs/live-eval-smoke-qwen36-nothink/summary.json` |
| `glm51_coding_api` | Z.AI coding API | measured | `runs/live-eval-smoke-glm51-coding-api/summary.json` |
| `glm51_claude_wrapper` | `claude -p` against `glm-5.1` | measured partial | `runs/live-eval-smoke-glm51-claude/glm-5.1/summary.json` |
| `codex_cli` | external agentic runner | planned `2026-04-29` | pending |
| `claude_code_vendor` | external agentic runner | planned `2026-04-29` | pending |

## Historical baseline: 10 Python prompt tasks

Источник: `experiments/model-comparison-full-2026-04-24.md`
Важно: это historical prompt-quality layer, а не strict executable verdict.

| Task | Difficulty | Check focus | `qwen` V100 | `qwen36` BM |
|------|------------|-------------|-------------|-------------|
| `Q01` TTL LRU cache | hard | TTL + LRU + thread safety | OK | OK |
| `Q02` race condition bug fix | medium | debugging completeness | OK | EMPTY |
| `Q03` sliding window limiter | medium | system design correctness | OK | OK |
| `Q04` async producer-consumer | hard | async semantics | EMPTY | PARTIAL |
| `Q05` Dijkstra | medium | algorithm correctness | OK | OK |
| `Q06` code review | medium | review completeness | OK | OK |
| `Q07` event bus | hard | concurrency + wildcard pub/sub | OK | OK |
| `Q08` retry decorator/context | hard | dual API design | OK | EMPTY |
| `Q09` connection pool | hard | pool lifecycle | OK | EMPTY |
| `Q10` BST serialization | hard | DS + serialization + rebalance | OK | OK |

## Strict executable suite: Python fixtures

Notation: `V/H` = `visible tests` / `hidden check`.

### max_tokens=5000 (старый benchmark)

| Task | Difficulty | What checked | `qwen` | `qwen /no_think` | `qwen36` | `qwen36 /no_think` | `glm-5.1 API` | `glm-5.1 via Claude` |
|------|------------|--------------|--------|------------------|----------|--------------------|----------------|----------------------|
| `case01_ttl_cache` | hard | lazy expiry, LRU among live entries, per-item TTL, stats API | `0/0` | `0/0` | `0/0` | `0/0` | `0/0` | `1/0` |
| `case02_env_template` | medium | recursive resolution, defaults on empty or missing, cycle detection | `0/0` | `0/0` | `0/0` | `0/0` | `1/1` | `1/1` |
| `case03_json_patch` | medium | JSON pointer escaping, patch semantics, deep copy, list edge cases | `0/0` | `0/0` | `0/0` | `0/0` | `1/1` | `1/1` |

> **Причина 0/0:** при max_tokens=5000 thinking mode тратит весь бюджет на reasoning (17-22K chars), на код остаётся 0 chars. `/no_think` не помогает на Python fixtures — тоже 0 chars content.

### max_tokens=16384 (новый benchmark, только `qwen`)

| Task | Difficulty | What checked | `qwen` (max_tokens=16384) | tokens | wall_time | reason/content chars | Detail |
|------|------------|--------------|---------------------------|--------|-----------|----------------------|--------|
| `case01_ttl_cache` | hard | lazy expiry, LRU among live entries, per-item TTL, stats API | **5/6** | 1836 | 47.6s | 4912 / 2643 | `get()` missing default arg — 1 line fix |
| `case02_env_template` | medium | recursive resolution, defaults on empty or missing, cycle detection | **PASS** | 1539 | 38.9s | 5141 / 2729 | all tests green |
| `case03_json_patch` | medium | JSON pointer escaping, patch semantics, deep copy, list edge cases | **PASS** | 3754 | 93.1s | 9661 / 7362 | all tests green |
| `speed_numbers` | easy | exact `1..80` output, no extra prose | **PASS** | 6124 | 153.5s | 21126 / 230 | exact match |

> **Ключевая находка:** увеличение max_tokens с 5000 до 16384 превращает `qwen` из 0/0 → 2 PASS + 1×(5/6) на Python fixtures. Проблема была не в модели, а в token budget.

### Сравнение: `qwen` max_tokens=5000 vs 16384

| Task | max_tokens=5000 content | max_tokens=16384 content | Verdict |
|------|------------------------|--------------------------|---------|
| `case01_ttl_cache` | 0 chars | 2643 chars (5/6 tests) | +2643, near-pass |
| `case02_env_template` | 0 chars | 2729 chars (PASS) | +2729, **PASS** |
| `case03_json_patch` | 0 chars | 7362 chars (PASS) | +7362, **PASS** |
| `speed_numbers` | 0 chars | 230 chars (PASS) | +230, **PASS** |

### max_tokens=16384: `qwen` vs `qwen36`

| Task | `qwen` (10B active) | `qwen36` (3B active) |
|------|----------------------|----------------------|
| `case01_ttl_cache` | **5/6 tests** (2643 chars) | FAIL (1882 chars, bugs) |
| `case02_env_template` | **PASS** (2729 chars) | FAIL (1715 chars, bugs) |
| `case03_json_patch` | **PASS** (7362 chars) | **PASS** (5439 chars) |
| `speed_numbers` | **PASS** (230 chars) | **PASS** (230 chars) |

> Обе модели имеют одну и ту же проблему с token budget при max_tokens=5000 (content=0). При max_tokens=16384 `qwen` (10B active) решает 2.5 из 3 задач, `qwen36` (3B active) — только 1 из 3. Разрыв объясняется размером активных параметров, не budget.

## Strict executable suite: multi-language single-shot tasks

(max_tokens=5000)

| Task | Lang | Difficulty | What checked | `qwen` | `qwen /no_think` | `qwen36` | `qwen36 /no_think` | `glm-5.1 API` | `glm-5.1 via Claude` |
|------|------|------------|--------------|--------|------------------|----------|--------------------|----------------|----------------------|
| `speed_numbers` | text | easy | exact `1..80` output, no extra prose | fail | fail | fail | fail | fail | pass |
| `cpp_lru_cache` | cpp | medium | compile/run pass, API shape, LRU semantics | fail | pass | fail | pass | pass | fail |
| `js_retry_async` | js | medium | retry loop, `shouldRetry`, last-error semantics | fail | pass | pass | pass | pass | pass |
| `ts_event_bus` | ts | hard | generic payload typing, `once`, order, unsubscribe | fail | fail | fail | fail | pass | fail |
| `arkts_stage_page` | arkts | medium | 6-point rubric for Stage page fix | `5/6` | `5/6` | `5/6` | `5/6` | `5/6` | `5/6` |

> **Note:** `speed_numbers` с max_tokens=16384 уже PASS (см. выше). Остальные multi-language tasks ещё не перезапускались с увеличенным budget.

## Agentic fixture suite

Notation: `pass/pass` = visible pass + hidden pass.

| Task | `qwen36 + OpenCode + /no_think` | `glm-5.1 + Claude Code` | `Codex` | `Claude Code` |
|------|----------------------------------|-------------------------|---------|----------------|
| `case01_ttl_cache` | `pass/pass` – self-repair after first failed attempt | `pass/pass` – 6 turns, ~62.9s | planned | planned |
| `case02_env_template` | not run yet | not run yet | planned | planned |
| `case03_json_patch` | not run yet | not run yet | planned | planned |

## Speed summary from current local runs

| Target | Observed client tok/s | Wall-time pattern | Notes |
|--------|-----------------------|-------------------|-------|
| `qwen_raw` (5000) | ~16–31 | ~124–307s on strict tasks | slowest; 0 chars content — budget consumed by reasoning |
| `qwen_16k` (16384) | ~40–41 | ~39–153s | **41 tok/s stable**, 2/3 Python fixtures PASS |
| `qwen_no_think` (5000) | ~27–41 | ~98–161s | still slow, but `cpp` and `js` recover |
| `qwen36_raw` (5000) | ~77–135 | ~29–39s | fast, but often spends budget in reasoning and leaves empty content |
| `qwen36_no_think` (5000) | ~126–134 | ~17–39s | best local speed/cost profile, but Python/TS strict tasks still weak |
| `glm51_coding_api` | ~32–43 | ~34–117s | strongest raw correctness on current strict suite |
| `glm51_claude_wrapper` | ~14–30 | ~10–226s | more agent-oriented; Python strong, but wrapper sometimes violates code-only constraint |

## Current conclusions

- **max_tokens=5000 — главный bottleneck для think-режима.** При увеличении до 16384 `qwen` V100 переходит от 0/0 к 2 PASS + 1×(5/6) на Python fixtures. Это не вопрос качества модели или KV precision — это чисто token budget.
- Для raw strict coding quality лучший текущий результат у `glm-5.1` через coding API.
- Для локального speed-first режима лучший practical profile у `qwen36 + /no_think`, но Python fixtures и TS он пока не закрывает.
- `qwen` на V100 с max_tokens=16384 уже сопоставим с `glm-5.1` на Python fixtures (2 PASS + near-pass vs 2 PASS + 1 partial).
- `ArkTS` сейчас никем не закрыт на `6/6`: все модели стабильно дают `5/6`, значит этот кейс полезен как differentiator для завтрашних `Codex` и `Claude`.

## Что должно быть добавлено завтра

Обязательные слоты для заполнения:

1. raw strict suite на `Codex`
2. raw strict suite на `Claude`
3. agentic `case01_ttl_cache` на `Codex`
4. agentic `case02_env_template` на `Codex`
5. agentic `case03_json_patch` на `Codex`
6. agentic `case01_ttl_cache` на `Claude`
7. agentic `case02_env_template` на `Claude`
8. agentic `case03_json_patch` на `Claude`

После этих прогонов этот файл нужно дополнить теми же полями: verdict, visible/hidden, compile/run, ArkTS score, wall time, tok/s и notes.
