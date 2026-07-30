#!/usr/bin/env bash
# run-exec-benchmark.sh — Run executable benchmark suite against any endpoint
# Usage: bash scripts/run-exec-benchmark.sh <suite-file> <endpoint> <model-name> <max-tokens>
set -euo pipefail

SELFDIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SUITE_FILE="$1"
ENDPOINT="$2"
MODEL="$3"
MAX_TOKENS="${4:-16000}"
TIMEOUT="${5:-300}"

RESULT_DIR="${SELFDIR}/../runs/exec-benchmark-$(date +%Y%m%d-%H%M%S)-$(basename "$SUITE_FILE" .json)-$(echo "$MODEL" | tr '/' '_')"
mkdir -p "$RESULT_DIR"
HELPER="${RESULT_DIR}/_exec_bench_helper.py"

cd "$SELFDIR/.."  # project root

PYTHONPATH="${PYTHONPATH:-}"

cat > "$HELPER" << 'PYEOF'
#!/usr/bin/env python3
import json, sys, re

def make_request(model, prompt, max_tokens):
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False
    }
    print(json.dumps(data))

def parse_response():
    try:
        d = json.load(sys.stdin)
        c = d.get("choices", [{}])[0].get("message", {})
        content = c.get("content", "")
        print(content)
    except Exception:
        print("")

def extract_code(content, language=""):
    pattern = rf"```{language}\n(.*?)```"
    matches = re.findall(pattern, content, re.DOTALL)
    if matches:
        return matches[-1].strip()
    return content.strip()

def get_task_field(suite_file, task_id, field):
    with open(suite_file) as f:
        for t in json.load(f)["tasks"]:
            if t["id"] == task_id:
                val = t.get(field, "")
                if isinstance(val, list):
                    print("\n".join(val))
                else:
                    sys.stdout.write(str(val))
                return

def get_task_ids(suite_file):
    with open(suite_file) as f:
        for t in json.load(f)["tasks"]:
            if t.get("evaluation_mode") == "executable_test":
                print(t["id"])

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "make-request":
        make_request(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    elif cmd == "parse":
        parse_response()
    elif cmd == "extract-code":
        content = sys.stdin.read()
        lang = sys.argv[2] if len(sys.argv) > 2 else ""
        print(extract_code(content, lang))
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

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; BLUE='\033[0;34m'; NC='\033[0m'
total=0; passed=0; failed=0; skipped=0; compile_errors=0

echo '[' > "${RESULT_DIR}/results.json"
first=true

for task_id in $(python3 "$HELPER" task-ids "$SUITE_FILE"); do
    total=$((total + 1))
    task_name=$(python3 "$HELPER" task-field "$SUITE_FILE" "$task_id" "name")
    fixture_dir=$(python3 "$HELPER" task-field "$SUITE_FILE" "$task_id" "fixture_dir")
    target_file=$(python3 "$HELPER" task-field "$SUITE_FILE" "$task_id" "target_file")
    test_command=$(python3 "$HELPER" task-field "$SUITE_FILE" "$task_id" "test_command")
    code_lang=$(python3 "$HELPER" task-field "$SUITE_FILE" "$task_id" "code_lang")
    readme_path="${fixture_dir}/README.md"

    if [ ! -f "$readme_path" ]; then
        echo -e "${YELLOW}  ${task_id} ${task_name}: SKIP (no README)${NC}"
        skipped=$((skipped + 1))
        continue
    fi

    echo -n "  ${task_id} ${task_name}: "

    readme_content=$(cat "$readme_path")
    start_ms=$(date +%s%3N)
    response=$(curl -fsS --max-time "$TIMEOUT" "${ENDPOINT}/chat/completions" \
      -H 'Content-Type: application/json' \
      -d "$(python3 "$HELPER" make-request "$MODEL" "$readme_content" "$MAX_TOKENS")" 2>/dev/null) || {
        echo -e "${RED}REQUEST FAILED${NC}"
        skipped=$((skipped + 1))
        continue
    }
    end_ms=$(date +%s%3N)
    elapsed_ms=$((end_ms - start_ms))

    raw_content=$(echo "$response" | python3 "$HELPER" parse)
    generated_code=$(echo "$raw_content" | python3 "$HELPER" extract-code "$code_lang")

    if [ -z "$generated_code" ]; then
        generated_code="$raw_content"
    fi

    code_file="${fixture_dir}/${target_file}"
    echo "$generated_code" > "$code_file"

    comp_tokens=$(echo "$response" | python3 -c "
import json,sys; d=json.load(sys.stdin); c=d.get('usage',{}); print(c.get('completion_tokens',c.get('total_tokens',0)))
" 2>/dev/null || echo "0")

    set +e
    test_output=$(eval "$test_command" 2>&1)
    test_exit=$?
    set -e

    echo "$test_output" > "${RESULT_DIR}/${task_id}-test-output.txt"
    echo "$raw_content" > "${RESULT_DIR}/${task_id}-response.txt"

    tps=0
    if [[ $comp_tokens -gt 0 && $elapsed_ms -gt 0 ]]; then
        tps=$(python3 -c "print(f'{ $comp_tokens / ($elapsed_ms / 1000.0):.1f}')")
    fi

    if [ $test_exit -eq 0 ]; then
        passed=$((passed + 1))
        echo -e "${GREEN}PASS${NC} (${tps} tok/s, ${elapsed_ms}ms)"
    else
        failed=$((failed + 1))
        echo -e "${RED}FAIL${NC} (${tps} tok/s, ${elapsed_ms}ms)"
    fi

    [[ "$first" != "true" ]] && echo ',' >> "${RESULT_DIR}/results.json"
    first=false
    python3 -c "
import json
print(json.dumps({
    'task_id': '$task_id',
    'task_name': '''$task_name''',
    'passed': $test_exit == 0,
    'exit_code': $test_exit,
    'completion_tokens': $comp_tokens,
    'tps': '$tps',
    'elapsed_ms': $elapsed_ms,
    'code_length': ${#generated_code}
}, ensure_ascii=False))
" >> "${RESULT_DIR}/results.json"

    rm -f "$code_file"
done

echo ']' >> "${RESULT_DIR}/results.json"

echo ""
echo "--- Summary ---"
echo "  PASS:   ${passed}/${total}"
echo "  FAIL:   ${failed}/${total}"
echo "  SKIP:   ${skipped}/${total}"
if [ $failed -gt 0 ]; then
    echo ""
    echo "--- Failed Tasks ---"
    for task_id in $(python3 "$HELPER" task-ids "$SUITE_FILE"); do
        result_file="${RESULT_DIR}/results.json"
        pass_status=$(python3 -c "
import json
with open('$result_file') as f:
    data = json.load(f)
for r in data:
    if r['task_id'] == '$task_id':
        print('FAIL' if not r['passed'] else 'PASS')
" 2>/dev/null)
        if [ "$pass_status" = "FAIL" ]; then
            task_name=$(python3 "$HELPER" task-field "$SUITE_FILE" "$task_id" "name")
            echo "  ${task_id} ${task_name}"
            echo "    Test output: ${RESULT_DIR}/${task_id}-test-output.txt"
            echo "    Model response: ${RESULT_DIR}/${task_id}-response.txt"
        fi
    done
fi

cat > "${RESULT_DIR}/summary.json" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "suite": "$(basename "$SUITE_FILE")",
  "endpoint": "${ENDPOINT}",
  "model": "${MODEL}",
  "max_tokens": ${MAX_TOKENS},
  "total_tasks": ${total},
  "passed": ${passed},
  "failed": ${failed},
  "skipped": ${skipped}
}
EOF

rm -f "$HELPER"
echo ""
echo "Results saved to: ${RESULT_DIR}"
