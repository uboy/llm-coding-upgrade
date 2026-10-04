# Карта задач и бенчмарков LLM: «какая модель справится достаточно и дешевле»

Снимок ссылок: **2026-10-04** (все ссылки проверены в этот день, см. «Обновление»).
Назначение: ответ на вопрос владельца «у меня есть задача - какая конкретно модель
справится лучше за меньшее время и деньги», включая вариант «локальной достаточно».
Живой документ: правки вносятся сюда, данные цен обновляются скриптом.

## Как отвечать на вопрос (методика)

1. **Определить класс задачи** по таблице ниже (одна задача - обычно 1-2 класса).
2. Взять **топ-3-5 кандидатов из лидерборда этого класса** - не из общего «интеллект-рейтинга»,
   а профильного; кандидатов делить на «фронтендер» (1 шт., судья качества) и «дешёвые» (остальные).
3. Собрать **мини-eval на СВОИХ 20-50 реальных задачах** этого класса (как
   `evals/exam-suite-v2/` - задачи не из открытых датасетов, с эталоном и анти-контаминацией).
   Чужие бенчмарки дают шорт-лист, «достаточно» доказывается только на своих задачах.
4. Прогнать кандидатов, посчитать **цену за решённую задачу**:
   облачные - цена токенов (OpenRouter API, скрипт ниже) × токены задачи;
   локальные - GPU-секунды (своя скорость замеряется на стенде, таблица ниже).
5. Порог «достаточно» фиксирует заказчик до прогона (например, «решает ≥90% моих задач»),
   иначе выбор превращается в подгонку под любимую модель. Дорогая модель в прогоне
   работает судьёй/потолком (LLM-as-judge), дешёвые сравниваются с ним.

## Классы задач → бенчмарки

| Класс | Типовые задачи | Чем мерить (проверено 2026-10-04) |
|---|---|---|
| Агентная разработка (SWE) | починить issue в реальном репо, multi-file PR | [SWE-bench](https://www.swebench.com) (Verified 500 / Lite / Multilingual / Multimodal, % resolved) |
| Терминал/ops-агент | работа в shell, деплой, отладка окружения | [Terminal-Bench](https://github.com/laude-institute/terminal-bench) |
| Редактирование кода в проекте | точечные правки по инструкции | [Aider polyglot leaderboard](https://aider.chat/docs/leaderboards/) |
| Код по описанию | функции/алгоритмы из условия | [LiveCodeBench](https://livecodebench.github.io) (свежие задачи, стоек к заучиванию), [BigCodeBench](https://github.com/bigcode-project/bigcodebench) |
| Автодополнение (FIM) | middle-infill в коде | канонического живого лидерборда нет; в проекте свой FIM-бенч (1C) + LiveCodeBench completion-часть |
| Tool/function calling | вызов API, передача аргументов, multi-turn | [BFCL v4](https://gorilla.cs.berkeley.edu/leaderboard.html) (AST + relevance + multi-turn + agentic) |
| Бизнес-агент с инструментами | сценарии с политиками (поддержка, продажи) | [tau-bench](https://github.com/sierra-research/tau-bench) |
| GUI/веб-агент | кликать интерфейс, браузер, десктоп | [OSWorld](https://os-world.github.io), [GAIA](https://huggingface.co/spaces/gaia-benchmark/leaderboard) |
| Длинный контекст | поиск иголки, сводные по 100+ страниц | [HELMET](https://github.com/princeton-nlp/HELMET), [LongBench v2](https://huggingface.co/datasets/THUDM/LongBench-v2) |
| RAG / поиск по документам | ответы с цитатами по базе | [BEIR](https://github.com/beir-cellar/beir) (retrieval) + свой eval ответов; качество генерации поверх - LiveBench |
| Эмбеддинги | векторный поиск, кластеризация | [MTEB](https://github.com/embeddings-benchmark/mteb) |
| Следование инструкциям | формат, ограничения, длина | [IFEval](https://github.com/google-research/google-research/tree/master/instruction_following_eval) |
| Знания/экзамены | широкие знания, проф. уровни | [MMLU-Pro](https://github.com/TIGER-AI-Lab/MMLU-Pro); потолок знаний - [HLE](https://huggingface.co/datasets/cais/hle) |
| Рассуждение/математика | логика, анализ данных, задачи | [LiveBench](https://livebench.ai) (категории reasoning/math/data-analysis, вопросы обновляются) |
| Чат-качество (человеческий вкус) | стиль, полезность ответа | [LMArena](https://lmarena.ai) (слепое сравнение, Elo) |
| Креативное письмо | сценарии, тексты, роль | [EQ-Bench](https://eqbench.com) (creative writing), категория LMArena |
| Русский язык | понимание/рассуждение на русском | [MERA](https://github.com/ai-forever/MERA) (сьют русскоязычных бенчмарков) |
| Безопасность/отказы | где отказывает, не оглупела ли «uncensored» | свой probe-набор (прецедент: `experiments/gemma4-uncensored-v100-2026-10-04.md`) |
| Извлечение/структурирование | JSON, классификация, NER | канонического лидерборда нет - только свой mini-eval (методика выше); LiveBench data-analysis близко |

## Живые мета-источники (кто где сейчас)

- [Artificial Analysis - методология](https://artificialanalysis.ai/methodology): Intelligence Index
  (средневзвешенный балл), **Cost per Task** ($ за задачу по весам индекса), Output Speed (ток/с),
  TTFT, blended price (7:2:1 cache-hit/input/output). Главный источник «интеллект vs цена vs скорость».
- [LMArena](https://lmarena.ai): человеческие предпочтения (Elo), категории; хорошо для «вкусовых» классов.
- [LiveBench](https://livebench.ai): контаминационно-стойкий сьют (вопросы обновляются), категории
  reasoning/coding/math/data-analysis.
- [OpenRouter Rankings](https://openrouter.ai/rankings): реальные объёмы использования по токенам -
  прокси «что реально берут разработчики» (в браузере; API из датацентров отдаёт 403).
- [llm-stats.com](https://llm-stats.com): агрегатор счётов по многим бенчмаркам на одной странице.
- [Open LLM Leaderboard (HF)](https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard):
  **архив** - исторические снимки открытых моделей, свежих данных не ждём.
- Scale SEAL - браузером (403 для curl из датацентров).

## Цена и скорость: обновляемые данные

- **Облачные модели:** OpenRouter API `GET https://openrouter.ai/api/v1/models` - все модели с
  ценами за токен и контекстом; ключ не нужен. **Запускать с asrock/ПК1** (датацентровые IP
  ловят 403 от Cloudflare - проверено 2026-10-04: с v100-host 403, с asrock 466 моделей).
  Скрипт: `scripts/bench-map-refresh.sh` → `benchmarks-map/openrouter-<дата>.tsv`.
- **Локальные:** скорость меряется только на своём железе. Замеры стенда (V100 32GB, GPU2,
  llama.cpp server-cuda, Q4_K_M, fast mode, temp 0.6):
| Модель | VRAM весов | Скорость decode | Контекст |
|---|---|---|---|
| Gemma-4-26B-A4B (MoE, 4B активных) uncensored/base | 16.8 GB | 86.6 / 83.2 ток/с | 64k |
| Gemma-4-31B (dense) uncensored/base | 18.7 GB | 28.1 / 28.6 ток/с | 32k |

  Цена локального токена = (потребление GPU кВт × тариф × сек/токен); при этой скорости
  31B на V100 даёт ~100k ток/час - локальная выгодна при большом постоянном трафике,
  офлайн-требовании или приватности, иначе облако дешевле амортизации.
- **Бесплатный тир:** в снапшоте 2026-10-04 у OpenRouter 22 модели с $0, среди них
  `google/gemma-4-26b-a4b-it:free` и `google/gemma-4-31b-it:free` (ctx 256-512k) - те же
  модели, что проверены локально (см. таблицу выше), можно пробить «достаточно ли» бесплатно
  до скачивания весов.
- VRAM-математика квантов: Q4_K_M ≈ 0.57 ГБ/млрд параметров (+1-3 ГБ KV-кэш на 32k при q8);
  правило выбора: weights + KV + ~1 ГБ буферы ≤ VRAM минус чужие процессы на карте.

## Источники локальных GGUF (проверено 2026-10-04)

- [unsloth](https://huggingface.co/unsloth) - быстрые кванты свежих моделей, включая негейтед зеркала google.
- [mradermacher](https://huggingface.co/mradermacher) - кванты почти всего («i1» = динамические).
- [huihui-ai](https://huggingface.co/huihui-ai) - abliterated-версии (снятие отказов).

## Устаревшие бенчмарки (не использовать для свежих выводов)

[HumanEval](https://github.com/openai/human-eval), [MMLU](https://github.com/hendrycks/test),
GSM8K - заучены при обучении; годятся только как исторический контекст. Современные аналоги -
LiveCodeBench, MMLU-Pro, LiveBench (обновляемые/свежие задачи).

## Обновление документа

1. `scripts/bench-map-refresh.sh` (с asrock/ПК1): проверка живости всех ссылок этого файла +
   свежий снапшот цен OpenRouter. Результаты - в `benchmarks-map/`.
2. Квартальный проход по лидербордам: AA (Intelligence Index/Cost per Task), LMArena,
   LiveBench - появились ли классы/бенчмарки, которых тут нет.
3. Новые ссылки добавлять только проверенными (HTTP 200 или осмысленный ответ) в день снимка;
   дату снимка в шапке менять. Непроверяемые из датацентра (OpenRouter Rankings, SEAL) - пометка
   «браузером» сохраняется.
