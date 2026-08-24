# Ornith-1.5 vs модели стенда - эксперимент (фаза 11 <internal> local-llm-inference)

> Статус: подготовка (2026-08-24). Замеры - после освобождения V100 (владелец сигнализирует).
> Карточка: <internal> `work/local-llm-inference/task-local-llm-inference-ornith15-compare.md`.
> Скрипты: `experiments/scripts-ornith15-2026-08/v100/{serve,bench}-ornith15.sh`.

## Что сравниваем

**Кандидат:** Ornith-1.5-35B-A3B-GGUF (ornith-ai, MIT; 36B total / ~3B active;
arch qwen35moe - та же MoE-архитектура, что у продакшн Qwen3.5-122B-A10B;
native ctx 262k; reasoning qwen3-style; sampling: temp 0.6 / top_p 0.95 /
top_k 20 - совпадает с каноном стенда).
Веса: v100-host:`/data/home/<user>/proj/bigmodel-bench-v100/models/ornith15/`.

**Бейслайны (записанные числа стенда):**

| Модель | Железо | Decode | PP | Источник |
|---|---|---|---|---|
| Qwen3.5-122B-A10B UD-Q4_K_XL | 3xV100 | 42-48 @0-2k, 14-25 @100k+ | 370-450 | config-card (D-038) |
| Gemma4-26B-A4B Q4_K_M | 1x3090 | 140.7 | 471 | config-card smoke |
| Qwen3.8-27B UD-Q4 + DFlash2 R1 | 1x3090 | 95 (код) | - | dflash2 фазы 1-3 |
| Qwen3.8-27B UD-Q6_K + MTP | 1xV100 | 16.5 @8k, 26.5 @124k | - | R5/V100-repeat |

Внимание: прямое сравнение 3090-vs-V100 некорректно по железу (разные карты);
для Ornith на V100 честная пара - Qwen3.8-27B Q6 на V100 (R5) и прод Qwen3.5-122B
(тот же хост, но 3 карты против одной).

## Протокол замеров

1. `serve-ornith15.sh q4km 32768 2` - одна V100, health-wait, фиксация VRAM.
2. `bench-ornith15.sh 8081 <label>` - ASCII coding-промпт x3, wall time по стриму
   + prompt eval time / eval time из лога сервера; проверка пустого content (G-D3,
   reasoning-модель: max_tokens >= 3500 при форматных задачах - здесь 1024 только
   для speed-прогона кода, content проверяется).
3. Long-ctx: подъём с большим ctx + needle pos/neg (переиспользовать
   `$B/needle-test.py` из фазы 8); таймаут клиента >= 7200s (G-C4).
4. **Mini-eval качества обязателен** (решение владельца 2026-08-24):
   `agent-eval-ornith15.py http://localhost:8081/v1 <label>` - те же 5 машинных
   задач, что в фазе 10; адаптация: max_tokens 4000 и strip_think() перед
   парсингом (reasoning-модель, G-D3). Бейслайны: Qwen Q4 5/5, Qwen Q6 5/5,
   gpt-oss-120b 4/5.
5. Негативный кейс (ожидаемый): Q6_K (29.2 GiB весов) на одной V100 - потолок ctx
   или OOM; фиксировать причину из лога, не считать фиаско провалом эксперимента.
6. Сравнение скоростей только внутри одного железа; cross-железо - с оговоркой.

Скоуп подтверждён владельцем 2026-08-24: 35B-A3B (+9B бонус), mini-eval
обязателен, 397B НЕ делаем, докачка Q8_0 разрешена.

## Результаты

(заполняется после прогонов; артефакты: `$B/ornith15-*.{json,log.full}`,
`$B/download.log`, маркер `DONE-ornith15-q4km` = веса сверены sha256)

| Конфиг | VRAM | PP tk/s | Decode tk/s | Примечание |
|---|---|---|---|---|
| Q4_K_M, ctx 32k, 1xV100 | - | - | - | базовый |
| Q4_K_M, long-ctx | - | - | - | needle pos/neg |
| Q6_K, 1xV100 | - | - | - | ожидаем впритык |

## Вывод

(решение о внедрении на стенд - через decision-log D-XXX; model-suite.models.json
править только после принятого решения)
