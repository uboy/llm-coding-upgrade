# Automation

## Purpose

Этот пакет автоматизирует полный цикл сравнения моделей:

- скачивание GGUF-моделей;
- переключение локального `llama.cpp` runtime между кандидатами;
- прямые API benchmark-замеры;
- `OpenCode` coding-оценку на фиксированном наборе кейсов;
- hidden-check валидацию после видимых тестов;
- генерацию итогового отчёта `summary.json` и `summary.md`.

## Files

- `model-suite.models.json` – список кандидатов и runtime-параметры
- `model-suite.evals.json` – direct benchmarks и eval suite
- `scripts/model_suite.py` – основной runner
- `scripts/model-suite.sh` – Linux/macOS wrapper
- `scripts/model-suite.ps1` – Windows wrapper
- `eval-fixtures/` – чистые кейсы для прогона
- `runs/` – результаты конкретных запусков

## Linux/macOS

List configured models:

```bash
bash /data/home/<user>/proj/llm-coding-upgrade/scripts/model-suite.sh list-models
```

Dry-run plan:

```bash
bash /data/home/<user>/proj/llm-coding-upgrade/scripts/model-suite.sh plan
```

Install default candidates:

```bash
bash /data/home/<user>/proj/llm-coding-upgrade/scripts/model-suite.sh install
```

Default candidates now include:

- `qwen35-122b-a10b-q4km` (current V100 prod)
- `qwen36-35b-a3b-q3km` (current BM prod)

Current storage roots:

- candidates are expected under `/data/shared/<user>/models`

Full run:

```bash
bash /data/home/<user>/proj/llm-coding-upgrade/scripts/model-suite.sh full
```

Run only selected models:

```bash
bash /data/home/<user>/proj/llm-coding-upgrade/scripts/model-suite.sh full --models qwen3-coder-next-q5ks,qwen35-35b-a3b-q5km
```

Night run with `nohup`:

```bash
mkdir -p /data/home/<user>/proj/llm-coding-upgrade/runs; LOG=/data/home/<user>/proj/llm-coding-upgrade/runs/nightly-$(date +%Y%m%d-%H%M%S).log; nohup bash /data/home/<user>/proj/llm-coding-upgrade/scripts/model-suite.sh full >"$LOG" 2>&1 & echo "$LOG"
```

Watch progress:

```bash
tail -f /path/from-echoed-log
```

Do not use wildcard log tails when several night runs exist, otherwise old failed logs and the new run will be mixed in one output stream.

Cold-start note:

- после `restart` runner теперь сам ждёт готовность стека и повторяет `smoke`, если модель ещё грузится;
- для крупных GGUF, особенно `Qwen3.5-122B-A10B`, первый проход может ждать готовность несколько минут.
- на Linux/macOS `OpenCode` eval теперь запускается через `script`, чтобы detached `nohup`-прогон получал псевдо-TTY и не срывался из-за no-tty режима.
- по умолчанию runner запускает `OpenCode` в quiet-режиме без `--print-logs`, чтобы длинные benchmark-прогоны не захлёбывались в агентных логах; для подробного debug-лога можно выставить `MODEL_SUITE_PRINT_LOGS=true`.
- после завершения `OpenCode`-кейса runner теперь повторяет `opencode export`, если первый export попал в короткое окно неполной записи сессии.
- если отдельный кейс или hidden-check падает, runner теперь записывает это как failed result и продолжает следующие кейсы и модели вместо аварийного завершения всего `full`-run.
- runner теперь поддерживает mixed storage roots под `/data/shared`: baseline из `/data/shared/<user>/models` и новые кандидаты из `/data/shared/<user>/models` могут запускаться одним и тем же suite без ручного переноса файлов.

## Windows

List configured models:

```powershell
powershell -File C:\path\to\llm-coding-upgrade\scripts\model-suite.ps1 list-models
```

Dry-run plan:

```powershell
powershell -File C:\path\to\llm-coding-upgrade\scripts\model-suite.ps1 plan
```

Install default candidates:

```powershell
powershell -File C:\path\to\llm-coding-upgrade\scripts\model-suite.ps1 install
```

Full run:

```powershell
powershell -File C:\path\to\llm-coding-upgrade\scripts\model-suite.ps1 full
```

## Output

Для каждого запуска создаётся каталог:

- `runs/<run-id>/summary.json`
- `runs/<run-id>/summary.md`
- `runs/<run-id>/<model-id>/stack.env`
- `runs/<run-id>/<model-id>/exports/*.json`
- `runs/<run-id>/<model-id>/cases/*`

## What the Runner Measures

- direct API timings через proxy `:4001`
- wall-clock и token usage из `OpenCode export`
- visible test pass/fail
- hidden-check pass/fail
- сохранность хэшей test files

## Systems

Эти скрипты рассчитаны на использование из:

- Codex
- Claude
- Cursor
- Gemini
- OpenCode

Фактический agentic benchmark внутри suite выполняется через `OpenCode`.
