# Подключение AI-клиентов к локальным моделям

## Эндпоинты

| Модель | URL | API key | Назначение |
|--------|-----|---------|------------|
| `qwen` | `http://v100-host:4001/v1` | `dummy` | Qwen3.5-122B-A10B (V100) — coding |
| `qwen36` | `http://v100-host:4002/v1` | `dummy` | Qwen3.6-35B-A3B (bm1+2) — general + vision |

> Оба эндпоинта — OpenAI-compatible API. Никакие данные не покидают локальную сеть.

---

## Гарантия приватности

- Все запросы идут на `v100-host` — сервер внутри локальной сети.
- Ни один из эндпоинтов не имеет выхода в интернет.
- Каждый клиент ниже настраивается с отключённой телеметрией.
- Проверить можно через: `ss -tnp | grep <pid_клиента>` или `tcpdump -i any host v100-host`.

---

## 1. Cline (VSCode)

**Extension:** `saoudrizwan.claude-dev`

### Настройка

1. Открыть Cline → нажать иконку настроек (шестерёнка)
2. **API Provider** → выбрать `OpenAI Compatible`
3. Заполнить:
   - **Base URL:** `http://v100-host:4001/v1`
   - **API Key:** `dummy`
   - **Model ID:** `qwen`
4. Сохранить.

### Отключение телеметрии

В `settings.json` (Ctrl+Shift+P → "Open User Settings JSON"):
```json
{
  "cline.telemetryEnabled": false
}
```

### Проверка изоляции

Cline не имеет встроенной телеметрии, которая бы утекала запросы. Все completion-запросы идут на указанный Base URL.

---

## 2. Continue (VSCode / JetBrains)

**Extension:** `Continue.continue`

### Настройка (~/.continue/config.yaml)

```yaml
models:
  - title: Qwen Coder (local)
    provider: openai
    model: qwen
    apiBase: http://v100-host:4001/v1
    apiKey: dummy
    contextLength: 294912

  - title: Qwen 36B (local)
    provider: openai
    model: qwen36
    apiBase: http://v100-host:4002/v1
    apiKey: dummy
    contextLength: 327680

tabAutocompleteModel:
  title: Qwen Coder Autocomplete
  provider: openai
  model: qwen
  apiBase: http://v100-host:4001/v1
  apiKey: dummy

analytics:
  posthog:
    apiKey: ""
```

### Отключение телеметрии

В том же `config.yaml` убедиться что `analytics.posthog.apiKey` пустой (как выше). Дополнительно в VSCode settings.json:
```json
{
  "continue.telemetryEnabled": false
}
```

---

## 3. OpenCode

**Конфиг:** `~/.config/opencode/opencode.json` (или `opencode.json` в корне проекта)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "providers": {
    "llamacpp": {
      "name": "llamacpp",
      "apiKey": "dummy",
      "models": {
        "qwen": {
          "id": "qwen",
          "name": "Qwen Coder (local)",
          "contextLength": 294912,
          "maxTokens": 8192,
          "reasoning": true
        },
        "qwen36": {
          "id": "qwen36",
          "name": "Qwen 36B (local)",
          "contextLength": 327680,
          "maxTokens": 8192,
          "reasoning": true
        }
      },
      "baseURL": "http://v100-host:4001/v1"
    }
  },
  "model": "llamacpp/qwen",
  "autoshare": false,
  "disabled_providers": ["anthropic", "openai", "google", "groq", "mistral"]
}
```

> Для `qwen36` создать отдельный `opencode.json` в нужном проекте с `"baseURL": "http://v100-host:4002/v1"` и `"model": "llamacpp/qwen36"`.

---

## 4. Cursor

### Настройка

1. `Cursor Settings` → `Models` → прокрутить вниз до **OpenAI API Key**
2. Вставить `dummy` как API key
3. Найти **Override OpenAI Base URL** → вставить `http://v100-host:4001/v1`
4. В поле модели написать `qwen`

### Отключение телеметрии

`Cursor Settings` → `General`:
- **Send usage data** → выключить
- **Send crash reports** → выключить

> Внимание: Cursor — проприетарный редактор. Даже при локальном LLM-эндпоинте Cursor может отправлять метаданные (код контекста, diff-ы) в свои серверы через другие каналы (автодополнение, индексация). Для полной изоляции предпочтительнее использовать VSCode + Cline/Continue.

---

## 5. Aider

**Установка:** `pip install aider-chat`

### Запуск

```bash
# Через переменные окружения (рекомендуется)
export OPENAI_API_KEY=dummy
export OPENAI_API_BASE=http://v100-host:4001/v1

aider --model openai/qwen --no-check-update
```

Или через флаги:
```bash
aider \
  --openai-api-key dummy \
  --openai-api-base http://v100-host:4001/v1 \
  --model openai/qwen \
  --no-check-update \
  --no-analytics
```

### `.aider.conf.yml` в корне проекта

```yaml
openai-api-key: dummy
openai-api-base: http://v100-host:4001/v1
model: openai/qwen
no-check-update: true
analytics: false
```

### Отключение телеметрии

Флаг `--no-analytics` отключает отправку данных. `--no-check-update` запрещает запросы к PyPI.

---

## 6. Claude Code (этот инструмент)

Claude Code использует Anthropic API. Для работы с локальными моделями через OpenAI-compatible эндпоинт нужно настроить кастомный provider.

```bash
# Создать кастомный провайдер в настройках Claude Code
# ~/.claude/settings.json

{
  "env": {
    "ANTHROPIC_BASE_URL": ""
  }
}
```

> Полная поддержка произвольных OpenAI-compatible эндпоинтов в Claude Code — через будущие версии с кастомными провайдерами. Для coding-задач с локальными моделями рекомендуется **OpenCode** или **Cline**.

---

## 7. Jan

**Сайт:** jan.ai — desktop-приложение.

### Настройка

1. Открыть Jan → `Settings` → `Integrations` → `OpenAI`
2. **API Key:** `dummy`
3. **API URL:** `http://v100-host:4002/v1`
4. В чате выбрать **Remote** → указать модель `qwen36`

### Телеметрия

`Settings` → `Privacy` → выключить все опции аналитики.

---

## 8. Open WebUI (уже настроен)

Доступен по адресу: `http://v100-host:3000`

Модели доступны автоматически:
- `qwen` — Qwen3.5-122B-A10B через прокси :4001
- `qwen36` — Qwen3.6-35B-A3B через LB-прокси :4002 (round-robin bm1/2)

---

## Быстрая проверка эндпоинтов

```bash
# Проверить доступность моделей
curl http://v100-host:4001/v1/models
curl http://v100-host:4002/v1/models

# Тестовый запрос
curl http://v100-host:4001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen","messages":[{"role":"user","content":"Say: ok"}],"max_tokens":5}'
```
