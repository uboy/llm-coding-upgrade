#!/usr/bin/env bash
# run-benchmark.sh — Run benchmark suite against any endpoint
# Usage: bash scripts/run-benchmark.sh <suite-file> <endpoint> <model-name> <max-tokens>
set -euo pipefail

SELFDIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SUITE_FILE="$1"
ENDPOINT="$2"
MODEL="$3"
MAX_TOKENS="${4:-12000}"
TIMEOUT="${5:-300}"

HELPER="${SELFDIR}/_bench_helper.py"
RESULT_DIR="${SELFDIR}/../runs/benchmark-$(date +%Y%m%d-%H%M%S)-$(basename "$SUITE_FILE" .json)-$(echo "$MODEL" | tr '/' '_')"

# Create helper for JSON generation
cat > "$HELPER" << 'PYEOF'
#!/usr/bin/env python3
import json, sys

def make_request(model, prompt, max_tokens):
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False
    }
    print(json.dumps(data))

def parse_response(field):
    try:
        d = json.load(sys.stdin)
        if field == "content":
            c = d.get("choices", [{}])[0].get("message", {})
            content = c.get("content", "")
            print(content)
        elif field == "reasoning_content":
            c = d.get("choices", [{}])[0].get("message", {})
            rc = c.get("reasoning_content", "") or ""
            print(len(rc))
        elif field == "completion_tokens":
            print(d.get("usage", {}).get("completion_tokens", 0))
        elif field == "prompt_tokens":
            print(d.get("usage", {}).get("prompt_tokens", 0))
    except Exception:
        print("0")

def get_task_ids(suite_file):
    with open(suite_file) as f:
        for t in json.load(f)["tasks"]:
            print(t["id"])

def get_task_field(suite_file, task_id, field):
    with open(suite_file) as f:
        for t in json.load(f)["tasks"]:
            if t["id"] == task_id:
                val = t.get(field, "")
                sys.stdout.write(str(val))
                break

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "make-request":
        make_request(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    elif cmd == "parse":
        parse_response(sys.argv[2])
    elif cmd == "task-ids":
        get_task_ids(sys.argv[2])
    elif cmd == "task-field":
        get_task_field(sys.argv[2], sys.argv[3], sys.argv[4])
PYEOF

mkdir -p "$RESULT_DIR"
echo "Suite:    $(basename "$SUITE_FILE")"
echo "Endpoint: $ENDPOINT"
echo "Model:    $MODEL"
echo "Max tokens: $MAX_TOKENS"
echo "Results:  $RESULT_DIR"
echo ""

echo '[' > "${RESULT_DIR}/quality.json"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; BLUE='\033[0;34m'; NC='\033[0m'
total=0; ok=0; partial=0; empty=0; overflow=0; first=true

for task_id in $(python3 "$HELPER" task-ids "$SUITE_FILE"); do
    total=$((total + 1))
    task_name=$(python3 "$HELPER" task-field "$SUITE_FILE" "$task_id" "name")
    task_prompt=$(python3 "$HELPER" task-field "$SUITE_FILE" "$task_id" "prompt")
    echo -n "  ${task_id} ${task_name}: "

    start_ms=$(date +%s%3N)
    response=$(curl -fsS --max-time "$TIMEOUT" "${ENDPOINT}/chat/completions" \
      -H 'Content-Type: application/json' \
      -d "$(python3 "$HELPER" make-request "$MODEL" "$task_prompt" "$MAX_TOKENS")" 2>/dev/null) || {
        echo -e "${RED}REQUEST FAILED${NC}"
        continue
    }
    end_ms=$(date +%s%3N)
    elapsed_ms=$((end_ms - start_ms))

    content=$(echo "$response" | python3 "$HELPER" parse content)
    reasoning_len=$(echo "$response" | python3 "$HELPER" parse reasoning_content)
    comp_tokens=$(echo "$response" | python3 "$HELPER" parse completion_tokens)
    prompt_tokens=$(echo "$response" | python3 "$HELPER" parse prompt_tokens)

    tps=0
    if [[ $comp_tokens -gt 0 && $elapsed_ms -gt 0 ]]; then
        tps=$(python3 -c "print(f'{ $comp_tokens / ($elapsed_ms / 1000.0):.1f}')")
    fi

    quality="EMPTY"
    content_len=${#content}
    if [[ $content_len -gt 500 ]]; then
        quality="OK"; ok=$((ok + 1))
    elif [[ $content_len -gt 100 ]]; then
        quality="PARTIAL"; partial=$((partial + 1))
    else
        if [[ $comp_tokens -ge $((MAX_TOKENS - 100)) ]]; then
            quality="OVERFLOW"; overflow=$((overflow + 1))
        else
            quality="EMPTY"; empty=$((empty + 1))
        fi
    fi

    case "$quality" in
        OK) echo -e "${GREEN}OK${NC} (${content_len} chars, ${tps} tok/s, ${elapsed_ms}ms)" ;;
        PARTIAL) echo -e "${YELLOW}PARTIAL${NC} (${content_len} chars)" ;;
        OVERFLOW) echo -e "${RED}OVERFLOW${NC} (thinking=${reasoning_len} chars)" ;;
        EMPTY) echo -e "${RED}EMPTY${NC} (thinking=${reasoning_len} chars)" ;;
    esac

    [[ "$first" != "true" ]] && echo ',' >> "${RESULT_DIR}/quality.json"
    first=false
    python3 -c "
import json
print(json.dumps({
    'task_id': '$task_id',
    'task_name': '''$task_name''',
    'quality': '$quality',
    'content_len': $content_len,
    'thinking_len': $reasoning_len,
    'completion_tokens': $comp_tokens,
    'prompt_tokens': $prompt_tokens,
    'tps': '$tps',
    'elapsed_ms': $elapsed_ms
}, ensure_ascii=False))
" >> "${RESULT_DIR}/quality.json"

    echo "$response" > "${RESULT_DIR}/${task_id}-response.json"
done

echo ']' >> "${RESULT_DIR}/quality.json"

echo ""
echo "--- Summary ---"
echo "  OK:       ${ok}/${total}"
echo "  PARTIAL:  ${partial}/${total}"
echo "  EMPTY:    ${empty}/${total}"
echo "  OVERFLOW: ${overflow}/${total}"

cat > "${RESULT_DIR}/summary.json" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "suite": "$(basename "$SUITE_FILE")",
  "endpoint": "${ENDPOINT}",
  "model": "${MODEL}",
  "max_tokens": ${MAX_TOKENS},
  "total_tasks": ${total},
  "ok": ${ok},
  "partial": ${partial},
  "empty": ${empty},
  "overflow": ${overflow}
}
EOF

rm -f "$HELPER"
echo ""
echo "Results saved to: ${RESULT_DIR}"
