#!/usr/bin/env bash
# v100-benchmark.sh — Benchmark V100 stack: speed + quality (10 coding tasks)
# Usage: bash scripts/v100-benchmark.sh [--speed-only] [--quality-only] [--task Q01]
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
STACK_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
SUITE_FILE="${STACK_ROOT}/evals/benchmark-suite.json"
HELPER="${SCRIPT_DIR}/_bench_helper.py"

# Configuration
ENDPOINT="${BENCH_ENDPOINT:-http://localhost:4001/v1}"
MODEL="${BENCH_MODEL:-qwen}"
MAX_TOKENS="${BENCH_MAX_TOKENS:-7000}"
TIMEOUT="${BENCH_TIMEOUT:-300}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
SPEED_ONLY=false
QUALITY_ONLY=false
TASK_FILTER=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --speed-only) SPEED_ONLY=true; shift ;;
    --quality-only) QUALITY_ONLY=true; shift ;;
    --task) TASK_FILTER="$2"; shift 2 ;;
    --endpoint) ENDPOINT="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# Ensure dependencies
command -v jq >/dev/null || { echo "Error: jq required" >&2; exit 1; }
command -v python3 >/dev/null || { echo "Error: python3 required" >&2; exit 1; }

# Create helper script for JSON generation
cat > "$HELPER" << 'PYEOF'
#!/usr/bin/env python3
"""Helper for v100-benchmark.sh — generates JSON payloads and parses responses."""
import json, sys

def make_request(model, prompt, max_tokens):
    """Generate JSON request body."""
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False
    }
    print(json.dumps(data))

def parse_response(field):
    """Extract a field from the JSON response on stdin."""
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
        if field == "reasoning_content":
            print("0")
        else:
            print("0")

def get_task_ids(suite_file):
    """List all task IDs from the suite."""
    with open(suite_file) as f:
        for t in json.load(f)["tasks"]:
            print(t["id"])

def get_task_field(suite_file, task_id, field):
    """Get a specific field from a task."""
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

RESULT_DIR="${STACK_ROOT}/runs/benchmark-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RESULT_DIR"

echo -e "${BLUE}=== V100 Benchmark ===${NC}"
echo "Endpoint: $ENDPOINT"
echo "Model:    $MODEL"
echo "Max tokens: $MAX_TOKENS"
echo "Results:  $RESULT_DIR"
echo ""

# --- Speed benchmark ---
run_speed_benchmark() {
  echo -e "${BLUE}--- Speed Benchmark ---${NC}"

  # Warmup
  echo -n "Warmup... "
  curl -fsS --max-time 60 "${ENDPOINT}/chat/completions" \
    -H 'Content-Type: application/json' \
    -d "$(python3 "$HELPER" make-request "$MODEL" "Reply with exactly: ok" 8)" >/dev/null 2>&1
  echo "done"

  # Decode speed
  echo -n "Decode speed (256 tokens)... "
  local decode_start decode_end decode_ms
  decode_start=$(date +%s%3N)

  local decode_response
  decode_response=$(curl -fsS --max-time "$TIMEOUT" "${ENDPOINT}/chat/completions" \
    -H 'Content-Type: application/json' \
    -d "$(python3 "$HELPER" make-request "$MODEL" "Count from 1 to 100, one number per line." 512)")

  decode_end=$(date +%s%3N)
  decode_ms=$((decode_end - decode_start))

  local completion_tokens prompt_tokens
  completion_tokens=$(echo "$decode_response" | python3 "$HELPER" parse completion_tokens)
  prompt_tokens=$(echo "$decode_response" | python3 "$HELPER" parse prompt_tokens)

  local decode_tps=0
  if [[ $completion_tokens -gt 0 && $decode_ms -gt 0 ]]; then
    decode_tps=$(python3 -c "print(f'{$completion_tokens / ($decode_ms / 1000):.1f}')")
  fi
  echo -e "${GREEN}${decode_tps} tok/s${NC} (${completion_tokens} tokens in ${decode_ms}ms)"

  # Prompt speed
  echo -n "Prompt speed (~500 tokens input)... "
  local pp_start pp_end pp_ms
  pp_start=$(date +%s%3N)

  local pp_response
  pp_response=$(curl -fsS --max-time "$TIMEOUT" "${ENDPOINT}/chat/completions" \
    -H 'Content-Type: application/json' \
    -d "$(python3 "$HELPER" make-request "$MODEL" "Write a haiku about each of these 50 programming languages: Python, JavaScript, TypeScript, Rust, Go, C, C++, Java, Kotlin, Swift, Ruby, PHP, Perl, Haskell, Erlang, Elixir, Clojure, Scala, OCaml, F#, Dart, Lua, R, MATLAB, Julia, Zig, Nim, Crystal, V, Carbon, Mojo, Fortran, COBOL, Ada, Prolog, Lisp, Scheme, Smalltalk, Objective-C, C#, Visual Basic, SQL, HTML, CSS, Bash, PowerShell, Assembly, Brainfuck, Malbolge. Format: one haiku per line." 16)")

  pp_end=$(date +%s%3N)
  pp_ms=$((pp_end - pp_start))

  local pp_prompt_tokens pp_completion_tokens
  pp_prompt_tokens=$(echo "$pp_response" | python3 "$HELPER" parse prompt_tokens)
  pp_completion_tokens=$(echo "$pp_response" | python3 "$HELPER" parse completion_tokens)

  local pp_tps=0
  if [[ $pp_prompt_tokens -gt 0 && $pp_ms -gt 0 ]]; then
    pp_tps=$(python3 -c "print(f'{$pp_prompt_tokens / ($pp_ms / 1000):.1f}')")
  fi
  echo -e "${GREEN}${pp_tps} tok/s${NC} (${pp_prompt_tokens} input tokens in ${pp_ms}ms)"

  # Save
  cat > "${RESULT_DIR}/speed.json" <<EOF
{
  "decode_tps": ${decode_tps},
  "decode_tokens": ${completion_tokens},
  "decode_ms": ${decode_ms},
  "pp_tps": ${pp_tps},
  "pp_tokens": ${pp_prompt_tokens},
  "pp_ms": ${pp_ms}
}
EOF
  echo ""
}

# --- Quality benchmark ---
run_quality_benchmark() {
  echo -e "${BLUE}--- Quality Benchmark (10 tasks) ---${NC}"

  local total_tasks=0 ok_count=0 partial_count=0 empty_count=0 overflow_count=0
  local first=true

  local tasks
  tasks=$(python3 "$HELPER" task-ids "$SUITE_FILE")

  echo '[' > "${RESULT_DIR}/quality.json"

  for task_id in $tasks; do
    if [[ -n "$TASK_FILTER" && "$task_id" != "$TASK_FILTER" ]]; then
      continue
    fi
    total_tasks=$((total_tasks + 1))

    local task_name task_prompt
    task_name=$(python3 "$HELPER" task-field "$SUITE_FILE" "$task_id" "name")
    task_prompt=$(python3 "$HELPER" task-field "$SUITE_FILE" "$task_id" "prompt")

    echo -n "  ${task_id} ${task_name}: "

    local start_time end_time elapsed_ms
    start_time=$(date +%s%3N)

    local response
    response=$(curl -fsS --max-time "$TIMEOUT" "${ENDPOINT}/chat/completions" \
      -H 'Content-Type: application/json' \
      -d "$(python3 "$HELPER" make-request "$MODEL" "$task_prompt" "$MAX_TOKENS")" 2>/dev/null) || {
      echo -e "${RED}REQUEST FAILED${NC}"
      continue
    }

    end_time=$(date +%s%3N)
    elapsed_ms=$((end_time - start_time))

    local content reasoning_content completion_tokens prompt_tokens
    content=$(echo "$response" | python3 "$HELPER" parse content)
    reasoning_content=$(echo "$response" | python3 "$HELPER" parse reasoning_content)
    completion_tokens=$(echo "$response" | python3 "$HELPER" parse completion_tokens)
    prompt_tokens=$(echo "$response" | python3 "$HELPER" parse prompt_tokens)

    local tps=0
    if [[ $completion_tokens -gt 0 && $elapsed_ms -gt 0 ]]; then
      tps=$(python3 -c "print(f'{$completion_tokens / ($elapsed_ms / 1000):.1f}')")
    fi

    local quality="EMPTY"
    local content_len=${#content}

    if [[ $content_len -gt 500 ]]; then
      quality="OK"; ok_count=$((ok_count + 1))
    elif [[ $content_len -gt 100 ]]; then
      quality="PARTIAL"; partial_count=$((partial_count + 1))
    else
      if [[ $completion_tokens -ge $((MAX_TOKENS - 100)) ]]; then
        quality="OVERFLOW"; overflow_count=$((overflow_count + 1))
      else
        quality="EMPTY"; empty_count=$((empty_count + 1))
      fi
    fi

    case "$quality" in
      OK) echo -e "${GREEN}OK${NC} (${content_len} chars, ${tps} tok/s, ${elapsed_ms}ms)" ;;
      PARTIAL) echo -e "${YELLOW}PARTIAL${NC} (${content_len} chars, ${tps} tok/s)" ;;
      OVERFLOW) echo -e "${RED}OVERFLOW${NC} (thinking=${reasoning_content} chars, ${tps} tok/s)" ;;
      EMPTY) echo -e "${RED}EMPTY${NC} (thinking=${reasoning_content} chars)" ;;
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
    'thinking_len': $reasoning_content,
    'completion_tokens': $completion_tokens,
    'prompt_tokens': $prompt_tokens,
    'tps': '$tps',
    'elapsed_ms': $elapsed_ms
}, ensure_ascii=False))
" >> "${RESULT_DIR}/quality.json"

    echo "$response" > "${RESULT_DIR}/${task_id}-response.json"
  done

  echo ']' >> "${RESULT_DIR}/quality.json"

  echo ""
  echo -e "${BLUE}--- Quality Summary ---${NC}"
  echo "  OK:       ${ok_count}/${total_tasks}"
  echo "  PARTIAL:  ${partial_count}/${total_tasks}"
  echo "  EMPTY:    ${empty_count}/${total_tasks}"
  echo "  OVERFLOW: ${overflow_count}/${total_tasks}"

  cat > "${RESULT_DIR}/summary.json" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "endpoint": "${ENDPOINT}",
  "model": "${MODEL}",
  "max_tokens": ${MAX_TOKENS},
  "total_tasks": ${total_tasks},
  "ok": ${ok_count},
  "partial": ${partial_count},
  "empty": ${empty_count},
  "overflow": ${overflow_count}
}
EOF
}

# --- Main ---
if [[ "$SPEED_ONLY" == "true" ]]; then
  run_speed_benchmark
elif [[ "$QUALITY_ONLY" == "true" ]]; then
  run_quality_benchmark
else
  run_speed_benchmark
  run_quality_benchmark
fi

# Cleanup helper
rm -f "$HELPER"

echo ""
echo -e "${GREEN}Results saved to: ${RESULT_DIR}${NC}"
echo "  speed.json   - decode + prompt speed"
echo "  quality.json - per-task quality results"
echo "  summary.json - overall summary"
