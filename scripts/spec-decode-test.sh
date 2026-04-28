#!/usr/bin/env bash
# spec-decode-test.sh — тестирует speculative decoding:
#   - скорость (tok/s)
#   - acceptance rate (% draft-токенов принятых главной моделью)
#   - качество (сравнение выводов с baseline при temp=0)
#
# Режимы:
#   baseline   — сохранить эталонные ответы (без draft)
#   compare    — сравнить текущий режим с эталоном
#   speed      — только замер скорости / acceptance rate (по умолчанию)
#
# Примеры:
#   bash scripts/spec-decode-test.sh speed       # текущая скорость
#   bash scripts/spec-decode-test.sh baseline    # сохранить эталон
#   bash scripts/spec-decode-test.sh compare     # проверить деградацию

set -euo pipefail

MODE="${1:-speed}"
PROXY_URL="${SPEC_TEST_URL:-http://127.0.0.1:4001}"
MODEL="${SPEC_TEST_MODEL:-qwen}"
BASELINE_DIR="/data/home/<user>/proj/llm-coding-upgrade/runs/spec-baseline"

# Промпты: coding (высокая дraftability), reasoning (низкая) — по 3 каждого типа
PROMPTS_CODING=(
  "Write a Python function that checks if a number is prime. Return only the function, no explanation."
  "Write a bash one-liner to count total lines in all .py files recursively."
  "Implement a simple LRU cache in Python using OrderedDict. Return only the class, no explanation."
)
PROMPTS_REASONING=(
  "What is 17 multiplied by 23? Show calculation."
  "List three differences between TCP and UDP protocols."
  "Explain in two sentences why KV cache quantization saves GPU memory."
)
ALL_PROMPTS=("${PROMPTS_CODING[@]}" "${PROMPTS_REASONING[@]}")

call_api() {
  local prompt="$1" temp="$2"
  local body
  body=$(python3 -c "
import json, sys
print(json.dumps({
  'model': '${MODEL}',
  'messages': [{'role': 'user', 'content': sys.argv[1]}],
  'max_tokens': 300,
  'temperature': float('${temp}'),
  'stream': False
}))" "$prompt")
  curl -sf --max-time 120 "${PROXY_URL}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "$body"
}

extract_text() {
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'].strip())"
}

extract_speed() {
  python3 -c "import sys,json; d=json.load(sys.stdin); t=d.get('timings',{}); print(f\"{t.get('predicted_per_second',0):.1f}\")"
}

extract_draft_info() {
  python3 -c "
import sys, json
d = json.load(sys.stdin)
t = d.get('timings', {})
dn = t.get('draft_n', 0)
da = t.get('draft_n_accepted', 0)
rate = (da/dn*100) if dn > 0 else -1
print(f'{dn}:{da}:{rate:.0f}')
"
}

print_header() {
  echo "=== Speculative Decode Test — mode: ${MODE} ==="
  echo "Endpoint: ${PROXY_URL}  Model: ${MODEL}"
  echo ""
}

# ────────────────────────────────────────────────
# MODE: speed — только скорость и acceptance rate
# ────────────────────────────────────────────────
run_speed() {
  print_header
  echo "Замер скорости на ${#ALL_PROMPTS[@]} промптах (temp=1.0, случайные ответы)..."
  echo ""

  local total_speed=0 total_dn=0 total_da=0 n=0

  for prompt in "${ALL_PROMPTS[@]}"; do
    n=$((n+1))
    label="[${n}/${#ALL_PROMPTS[@]}]"
    echo -n "${label} ${prompt:0:55}... "

    resp=$(call_api "$prompt" "1.0") || { echo "ERROR"; continue; }

    speed=$(echo "$resp" | extract_speed)
    draft=$(echo "$resp" | extract_draft_info)
    dn=$(echo "$draft" | cut -d: -f1)
    da=$(echo "$draft" | cut -d: -f2)
    rate=$(echo "$draft" | cut -d: -f3)

    total_speed=$(python3 -c "print(${total_speed}+${speed})")
    total_dn=$((total_dn + dn))
    total_da=$((total_da + da))

    if [[ "$rate" == "-1" ]]; then
      echo "${speed} tok/s  [no draft]"
    else
      echo "${speed} tok/s  [draft: ${da}/${dn} = ${rate}% accepted]"
    fi
  done

  echo ""
  echo "─── Summary ────────────────────────────────────"
  avg=$(python3 -c "print(f'{${total_speed}/${#ALL_PROMPTS[@]}:.1f}')")
  echo "Avg speed: ${avg} tok/s"

  if [[ $total_dn -gt 0 ]]; then
    overall=$(python3 -c "print(f'{${total_da}/${total_dn}*100:.1f}')")
    echo "Overall acceptance rate: ${overall}%  (${total_da}/${total_dn} tokens)"
    echo ""
    if python3 -c "exit(0 if ${total_da}/${total_dn} >= 0.6 else 1)" 2>/dev/null; then
      echo "✓ ≥60% — отличная конфигурация. Попробуй увеличить --draft-max"
    elif python3 -c "exit(0 if ${total_da}/${total_dn} >= 0.4 else 1)" 2>/dev/null; then
      echo "~ 40–60% — умеренно. Попробуй --draft-p-min 0.5"
    else
      echo "✗ <40% — draft не подходит. Откатить: закомментировать LLAMA_DRAFT_MODEL_PATH в stack.env"
    fi
  else
    echo "(Speculative decoding не активен)"
    echo ""
    echo "Включить: раскомментировать LLAMA_DRAFT_MODEL_PATH в stack.env → stack.sh restart"
  fi
}

# ────────────────────────────────────────────────
# MODE: baseline — сохранить эталонные ответы (temp=0)
# ────────────────────────────────────────────────
run_baseline() {
  print_header
  echo "Сохраняем эталонные ответы при temp=0 в: ${BASELINE_DIR}"
  echo "ВАЖНО: запускать без draft-модели."
  echo ""

  mkdir -p "${BASELINE_DIR}"
  local n=0

  for prompt in "${ALL_PROMPTS[@]}"; do
    n=$((n+1))
    label="[${n}/${#ALL_PROMPTS[@]}]"
    echo -n "${label} ${prompt:0:55}... "

    resp=$(call_api "$prompt" "0.0") || { echo "ERROR — пропуск"; continue; }
    text=$(echo "$resp" | extract_text)
    speed=$(echo "$resp" | extract_speed)

    out_file="${BASELINE_DIR}/prompt_${n}.txt"
    echo "$text" > "$out_file"
    echo "${speed} tok/s  (${#text} chars)"
  done

  echo ""
  echo "Эталон сохранён: ${BASELINE_DIR}/"
  echo "Теперь включи draft в stack.env → stack.sh restart → bash scripts/spec-decode-test.sh compare"
}

# ────────────────────────────────────────────────
# MODE: compare — сравнить с baseline (temp=0)
# ────────────────────────────────────────────────
run_compare() {
  print_header

  if [[ ! -d "${BASELINE_DIR}" ]]; then
    echo "Baseline не найден. Сначала запусти:"
    echo "  bash scripts/spec-decode-test.sh baseline"
    exit 1
  fi

  echo "Сравниваем с baseline при temp=0..."
  echo "При корректном speculative decoding ответы должны быть ИДЕНТИЧНЫ."
  echo ""

  local n=0 matched=0 total=0 total_speed=0 total_dn=0 total_da=0

  for prompt in "${ALL_PROMPTS[@]}"; do
    n=$((n+1))
    base_file="${BASELINE_DIR}/prompt_${n}.txt"

    if [[ ! -f "$base_file" ]]; then
      echo "[${n}] SKIP — baseline файл отсутствует"
      continue
    fi

    echo -n "[${n}/${#ALL_PROMPTS[@]}] ${prompt:0:50}... "
    resp=$(call_api "$prompt" "0.0") || { echo "ERROR"; continue; }

    text=$(echo "$resp" | extract_text)
    speed=$(echo "$resp" | extract_speed)
    draft=$(echo "$resp" | extract_draft_info)
    dn=$(echo "$draft" | cut -d: -f1)
    da=$(echo "$draft" | cut -d: -f2)
    rate=$(echo "$draft" | cut -d: -f3)

    baseline_text=$(cat "$base_file")
    total=$((total+1))
    total_speed=$(python3 -c "print(${total_speed}+${speed})")
    total_dn=$((total_dn + dn))
    total_da=$((total_da + da))

    if [[ "$text" == "$baseline_text" ]]; then
      matched=$((matched+1))
      quality="✓ identical"
    else
      # Подробная разница
      diff_chars=$(python3 -c "
a=open('${base_file}').read(); b='''$(echo "$text" | python3 -c "import sys; print(sys.stdin.read().replace(\"'\", \"'\\\"'\\\"'\"))")'''
print(abs(len(a)-len(b)))
" 2>/dev/null || echo "?")
      quality="✗ differs (${diff_chars} chars diff)"
    fi

    if [[ "$rate" == "-1" ]]; then
      echo "${speed} tok/s  ${quality}"
    else
      echo "${speed} tok/s  draft=${rate}%  ${quality}"
    fi
  done

  echo ""
  echo "─── Quality Summary ─────────────────────────────"
  echo "Identical outputs: ${matched}/${total}"

  avg=$(python3 -c "print(f'{${total_speed}/${total}:.1f}')" 2>/dev/null || echo "?")
  echo "Avg speed: ${avg} tok/s"

  if [[ $total_dn -gt 0 ]]; then
    overall=$(python3 -c "print(f'{${total_da}/${total_dn}*100:.1f}')")
    echo "Acceptance rate: ${overall}%"
  fi

  echo ""
  if [[ "$matched" -eq "$total" ]]; then
    echo "✓ Все ответы совпали с baseline — деградации качества нет"
    echo "  Speculative decoding работает корректно."
  else
    diff_count=$((total - matched))
    echo "⚠ ${diff_count}/${total} ответов отличаются от baseline"
    echo "  При temp=0 ответы должны быть идентичны — проверь конфигурацию draft-модели."
    echo "  Возможные причины: несовместимый токенайзер, неправильный --draft-p-min."
  fi
}

# ────────────────────────────────────────────────
case "$MODE" in
  baseline) run_baseline ;;
  compare)  run_compare ;;
  speed|"") run_speed ;;
  *)
    echo "Использование: $0 [speed|baseline|compare]"
    echo "  speed    — скорость + acceptance rate (по умолчанию)"
    echo "  baseline — сохранить эталонные ответы (без draft)"
    echo "  compare  — сравнить с эталоном (с draft)"
    exit 1
    ;;
esac
