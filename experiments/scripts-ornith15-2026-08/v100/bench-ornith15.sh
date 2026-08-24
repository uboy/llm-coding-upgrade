#!/usr/bin/env bash
# bench-ornith15.sh <port> [label]
# Скоростной прогон по методике эпика (<internal> local-llm-inference):
#  - короткий ASCII-промпт (код) x3, замер wall time по стриму;
#  - тайминги берутся также из docker-лога llama-server (prompt eval time / eval time).
# Сервер должен быть поднят serve-ornith15.sh; имя контейнера ornith15-run.
# Результат: строки BENCH в stdout + полный лог сервера сохранён.
set -euo pipefail

PORT="${1:?port required}"
LABEL="${2:-run}"
NAME=ornith15-run
B=/data/home/<user>/proj/bigmodel-bench-v100

PROMPT='Write a Python function that merges two sorted lists into one sorted list without using sort(). Include a short docstring and three assert-based tests. Answer with code only.'

bench_once() {
  local t0 t1 out_file="$1"
  t0=$(date +%s.%N)
  curl -s "http://localhost:$PORT/v1/chat/completions" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"ornith\",\"messages\":[{\"role\":\"user\",\"content\":$(python3 -c "import json,sys;print(json.dumps(sys.argv[1]))" "$PROMPT")}],\"temperature\":0.6,\"top_p\":0.95,\"top_k\":20,\"max_tokens\":1024,\"stream\":true}" \
    > "$out_file"
  t1=$(date +%s.%N)
  local chunks answer_tokens
  chunks=$(grep -c '^data:' "$out_file" || true)
  # содержимое ответа (для негативной проверки пустого content, G-D3)
  python3 - "$out_file" <<'PYEOF'
import json, sys
out = ""
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line.startswith("data:") or "[DONE]" in line:
        continue
    try:
        d = json.loads(line[5:])
        delta = d["choices"][0].get("delta", {})
        r = delta.get("reasoning_content")
        c = delta.get("content")
        if r: out += "<think>"
        if c: out += c
    except Exception:
        pass
print("ANSWER_CHARS=%d THINK=%s" % (len(out), "<think>" in out))
PYEOF
  echo "BENCH label=$LABEL wall=$(python3 -c "print(f'{$t1-$t0:.1f}')")s stream_chunks=$chunks"
}

for n in 1 2 3; do
  bench_once "$B/ornith15-bench-$LABEL-$n.json"
done

docker logs "$NAME" > "$B/ornith15-$LABEL.log.full" 2>&1
echo "--- server timing (last run) ---"
grep -E "prompt eval time|eval time|tokens per second" "$B/ornith15-$LABEL.log.full" | tail -6 || echo "(no timing lines)"
