# AGENTS.md — LLM Coding Upgrade

> Проектный **single source of truth** для агентов (functional behavior + process/quality gates).
> При конфликте источников — стоп, записать конфликт, запросить решение пользователя,
> обновить authoritative-источник.

## 1. Что это за проект

Self-hosted LLM-стек для coding и общих AI-задач на трёх серверах. Инференс — `llama.cpp` (CUDA) в Docker,
спереди — Node-прокси с алиасами моделей. Балансировка нагрузки BM1/BM2 — отдельный round-robin LB-proxy
с health-check. Никакие данные не покидают локальную сеть.

### Архитектура

| Сервер | IP | GPU | Модель | Алиас | Порт (прокси/llama) |
|--------|----|-----|--------|-------|---------------------|
| V100 (v100-host) | v100-host | 3× Tesla V100 PCIE 32GB | Qwen3.5-122B-A10B UD-Q4_K_XL | `qwen` | 4001 / 8001 |
| bm1 | bm1 | 1× RTX 3090 24GB | Gemma 4 26B-A4B Q4_K_M | `gemma4` (через LB) | 8001 |
| bm2 | bm2 | 1× RTX 3090 24GB | Gemma 4 26B-A4B Q4_K_M | `gemma4` (через LB) | 8001 |

- **`qwen`** → `http://v100-host:4001/v1` — кодинг/reasoning (V100).
- **`gemma4`** → `http://v100-host:4002/v1` — general (+ vision), round-robin BM1+BM2, health-check каждые 15с.
- Оба эндпоинта OpenAI-совместимы. Open WebUI: `http://v100-host:3000` (порт контейнера маппится на 3001 локально).

## 2. Источники истины (для этого проекта)

| Тема | Authoritative | Роль остальных |
|------|---------------|----------------|
| Sampling-параметры (temp/top-p/top-k/min-p/repeat-penalty/reasoning) | **`decision-log.md`** (раздел «Канонические sampling-параметры») | README/config-card — только зеркало |
| Production-конфиг (GGUF path, ctx, parallel, cache-type, VRAM факт) | **`config-card.md`** | `stack.env`/`lb-proxy.env` — runtime-воплощение |
| Реестр моделей и runtime-параметры для switching | **`model-suite.models.json`** | `automation.md` — как запускать |
| Вход в проект / общий обзор | **`README.md`** | docs/ — глубина, experiments/ — отчёты |
| Решения и их статус (принято/закрыто/«не пересматривать») | **`decision-log.md`** (D-XXX) | — |
| Этот файл | **`AGENTS.md`** | процесс/правила проекта |

> **Запрет на создание нового drift-источника:** не дублируйте изменяемые значения (sampling, пути, VRAM)
> в AGENTS.md/README/config-card дословно. Указывайте на authoritative и держите зеркало синхронным.
> См. раздел 9 — известные расхождения, которые надо чинить.

## 3. Guardrails (обязательно)

- **Production-стек в горячем режиме.** Не перезапускайте `qwen`/`gemma4` без явной необходимости.
  Рестарт V100 = простой кодинг-ворклоуда на ~76с cold-start (+ полная потеря KV-кэша).
- **No shadow work.** Никаких скрытых изменений tracked-файлов/конфигов/сервисов до того, как выбран
  workflow это разрешает. Особо — `stack.env`, `lb-proxy.env`, `decision-log.md`, запущенные контейнеры.
- **Restart-порядок с health-wait** (только через скрипты, см. раздел 4):
  1. V100 llama.cpp → ждать `/health` (до 5 мин)
  2. BM1/BM2 llama.cpp → ждать `/health` через SSH (до 5 мин)
  3. LB proxy → ждать порт (до 30с)
  - LB health-check авторекавери: поднятый BM-бэкенд сам становится UP в течение ~15–45с, LB рестартить обычно не нужно.
- **Rollback.** `apply-model.sh apply` откатывает автоматически при ошибке. Ручные переключения модели —
  только через `apply-model.sh`, не прямой правкой `docker run`.
- **Не трогайте «закрытые» решения.** `decision-log.md` содержит записи со статусом
  **«не пересматривать»** (напр. D-015 Q5_K_S финален, D-016 spec-decoding закрыт). Не открывать заново.
- **Доступы.** V100 — локально (`/data/home/<user>/proj/llm-coding-upgrade`). BM1/BM2 — только по SSH
  (`<user>@bm1/bm2`). SSH-команды на BM — осознанно; не рестартуйте BM-ноду,
  которая занята (уточняйте у пользователя, если GPU несвободен).
- **Адреса хостов.** Хосты в этом репо названы логическими именами (v100-host, bm1, bm2);
  при развёртывании подставьте адреса своего оборудования в env-файлы и client-setup.md.
  Ориентир по железу: 3x V100 32GB (v100-host), 2x RTX 3090 24GB (bm1, bm2).
- **GPU-память.** Модель Gemma 4 26B Q4_K_M занимает ~21 ГБ из 24. При параллельном GPU-процессе на BM
  (видно через `nvidia-smi --query-compute-apps`) контейнер падает в OOM при загрузке mmproj.
  Сначала убедитесь, что VRAM свободен, иначе старт сервиса «проверочно» провалится по памяти, а не по конфигу.
- **Docker 29 + GPU = нужен CDI.** На всех нодах должен быть установлен `nvidia-container-toolkit`
  и сгенерирована CDI-спецификация (`/etc/cdi/nvidia.yaml`). Без неё `--gpus all` падает с
  `failed to discover GPU vendor from CDI: no known GPU vendor found`. После установки toolkit рестарт
  docker-daemon требуется только если он стартовал ДО установки (BM-ноды читают CDI on-demand).
  См. урок 2026-06-13 ниже.
- **Секреты.** В `stack.env` API-ключи Open WebUI — `dummy` (offline). Не выносите и не логируйте ключи.
- **Язык ответа:** пользовательский язык — русский; технические термины/команды/пути — как есть.

## 4. Операционные скрипты (использовать их, а не ad-hoc)

```bash
# Единый lifecycle (V100 + LB + BM1/BM2 по SSH), с health-wait
bash scripts/deploy.sh status            # статус всех сервисов с параметрами
bash scripts/deploy.sh smoke             # E2E smoke на всех эндпоинтах
bash scripts/deploy.sh restart           # рестарт всего (порядок выше)
bash scripts/deploy.sh restart-local     # только V100 + LB
bash scripts/deploy.sh restart-bm        # оба BM (BM1 И BM2) — для одного узла действуйте вручную
bash scripts/deploy.sh down              # остановить локальные сервисы
bash scripts/deploy.sh logs [v100|lb|bm1|bm2|all]

# Переключение модели из реестра (с автороллбэком)
bash scripts/apply-model.sh list
bash scripts/apply-model.sh current
bash scripts/apply-model.sh apply <model-id>

# Точечные лончеры
bash scripts/stack.sh   up|down|restart|status|smoke|wait-ready|logs|render-proxy   # V100
bash scripts/lb-stack.sh up|down|restart|status|smoke|logs                          # LB proxy

# Бенчмарки
bash scripts/v100-benchmark.sh [--speed-only|--quality-only|--task Q01|--endpoint URL|--model MODEL]
bash scripts/run-benchmark.sh        # универсальный (quality review)
bash scripts/run-exec-benchmark.sh   # исполняемый (генерит код, гоняет реальные тесты, PASS/FAIL)
```

> `deploy.sh restart-bm` рестартит **оба** узла. Чтобы поднять/остановить один BM — те же шаги вручную:
> `ssh <user>@v100-host-01X 'docker {start|stop} llamacpp-server-p8001'` + поллинг `/health`.

## 5. Проверка и критерий «готово»

Перед любой заявкой о завершении операции/изменения — обязательная верификация:

```bash
bash scripts/deploy.sh status     # все сервисы: state + параметры + backend health
bash scripts/deploy.sh smoke      # /v1/models + chat на qwen и gemma4
# LB backends: curl -s http://localhost:4002/lb-status
# BM health (с ноды): ssh <user>@v100-host-01X 'curl -s localhost:8001/health'
```

- **Готово = smoke проходит на затронутых эндпоинтах** + (для старта) `/health: ok` + контейнер `running`,
  модель/ctx/sampling совпадают с `config-card.md`/`decision-log.md`.
- Для бенчмарков — артефакты пишутся в `runs/<name>-<timestamp>/` (`summary.json`, `*.json`).

## 6. Decision-log протокол

- Решения нумеруются **D-XXX** последовательно; для нового решения — следующий свободный номер.
- Каждое решение: статус (`принято`/`выполнено`/`частично устарело`/`закрыто — не применимо`), причина,
  источники. Дата в скобках.
- Статусы **«не пересматривать»** и **«закрыто»** — табу на переоткрытие без смены архитектуры/железа.
- Любое изменение sampling/runtime-параметров prod-модели — **сначала запись в `decision-log.md`**,
  затем зеркало в config-card/README/stack.env.

## 7. Канонические sampling-параметры (краткое зеркало → см. decision-log.md)

> Authoritative: `decision-log.md`, раздел «Канонические sampling-параметры». Здесь — только указатель.

- **`qwen` (Qwen3.5-122B-A10B):** `temp 0.6, top-p 0.95, top-k 20, min-p 0.0, --jinja`.
  Thinking-модель (`<think/>`). **НЕ добавлять `--repeat-penalty`. НЕ ставить `--reasoning off`.**
- **`gemma4` (Gemma 4 26B-A4B):** `temp 0.6, top-p 0.95, top-k 20, min-p 0.0, repeat-penalty 1.0, --jinja`.
- Для think-моделей клиенты: `max_tokens ≥ 12000–16384` (иначе thinking-chain съедает бюджет → content=0).

## 8. Известные ограничения и non-goals

- **NVLink недоступен** на V100 (D-028): только PCIe. Деградация decode по длине контекста:
  0–2K ~42–48 tok/s; 10–65K ~16–28; 100–256K ~14–25. Не лечится без смены железа.
- **Speculative decoding НЕ совместим** с гибридными SSM-моделями (Qwen3.5-122B, Coder-Next) — D-016, закрыто.
  Не раскомментировать блок draft в `stack.env`. Возврат темы — только при смене модели на не-SSM.
- **V100 long-context PP** на промптах >100K — ~25 tok/s (PCIe). Очень длинные промпты (265K+) — минуты/часы.
- **BM thinking overflow** — на сложных задачах thinking-chain может занять весь budget. Mitigation: `/no_think` или большой `max_tokens`.
- **Flash attention** — включён автоматически (CC ≥ 7.0).
- **Существующие тесты/архитектурные артефакты — заморожены** по умолчанию;
  исключение — с одобрения пользователя.

## 9. Известные расхождения документации (чинить, не плодить)

> Обнаружено 2026-06-13. Перед правкой документации сверяйтесь с **runtime-фактом** (`deploy.sh status`,
> `docker inspect`, `/props`), а не с соседним абзацем.

1. **Модель BM:** `decision-log.md` (D-018/D-020/D-025 + секция sampling) описывает **Qwen3.6-35B-A3B**,
   но фактически развёрнута **Gemma 4 26B-A4B** (`lb-proxy.env`, README). Нет записи decision-log о переключении.
2. **config-card.md:** заголовок секции BM = «Qwen3.6-35B-A3B», а таблица внутри — Gemma 4. Алиас `gemma4` vs `qwen36`.
3. **mmproj:** config-card для BM пишет «не используется», но контейнер стартует с `--mmproj`
   (подтверждено логами `mtmd_init`/`clip_init`). Влияет на VRAM (~1.1 ГБ).
4. **README comparison table:** заголовки колонок BM1 «Qwen3.6 35B» / BM2 «Gemma4 26B» — обе ноды на самом деле Gemma 4.

При правке: обновить authoritative (`decision-log.md` добавить запись о переходе на Gemma 4) и синхронизировать зеркала.

## 10. Урок 2026-06-13 — CDI/toolkit на BM-нодах

- Симптом: контейнер `llamacpp-server-p8001` не стартует, `failed to discover GPU vendor from CDI: no known GPU vendor found`.
- Причина: Docker 29 для `--gpus all` использует CDI; `nvidia-container-toolkit` удалён и/или CDI-спецификация
  `/etc/cdi/nvidia.yaml` не сгенерирована.
- Фикс на BM-ноде: `apt-get install -y nvidia-container-toolkit` →
  `nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml` → (если daemon стартовал до установки) `systemctl restart docker` →
  `docker start llamacpp-server-p8001`. Проверка CDI: `docker run --rm --gpus all --entrypoint nvidia-smi <image> -L`.
- Статус после фикса: BM2 — в проде (`gemma4` UP); BM1 — toolkit+CDI готовы, контейнер оставлен остановленным
  (нода занята параллельным GPU-процессом; полный старт упирается в VRAM, не в конфиг).

## 11. Маршрутизация задач (по `policy/team-lead-orchestrator.md`)

- Сначала классифицировать: `trivial`/`non_trivial` × `repo_change`/`repo_read`/`content_task`/`general`.
- `repo_change` non-trivial → halt → research/plan → CC → реализация с проверкой. Операционные действия
  (рестарт сервисов, фиксы GPU-стека) — это не «repo_change», но требует той же дисциплины:
  объяснить → выполнить → **верифицировать** (`deploy.sh smoke`) → отчитаться.
- Контент/общие задачи — без git/commit хвоста. Commit — только `repo_change` с пройденной верификацией и без блокеров.
- Не заявлять завершение без evidence верификации (или принятого пользователем блокера).
