#!/usr/bin/env bash
# opt-experiment.sh — Run a single experiment variant for V100 optimization
# Usage: bash scripts/opt-experiment.sh <config_id> [overrides...]
# Example: bash scripts/opt-experiment.sh B-ubatch-1024 LLAMA_UBATCH_SIZE=1024
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
STACK_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
CONFIG_ID="${1:?Usage: opt-experiment.sh <config_id> [overrides]}"
shift
OVERRIDES=("$@")

RUN_DIR="${OPT_RUN_DIR:-$(ls -td "$STACK_ROOT"/runs/v100-opt-* | head -1)}"
ENDPOINT="${OPT_ENDPOINT:-http://localhost:8001/v1}"
MODEL="${OPT_MODEL:-qwen}"
VARIANT_ENV="$RUN_DIR/stack.env.$CONFIG_ID"

echo "=== Experiment: $CONFIG_ID ==="
echo "Run dir: $RUN_DIR"
echo "Overrides: ${OVERRIDES[*]}"

# Create variant env from baseline
cp "$RUN_DIR/stack.env.baseline" "$VARIANT_ENV"

# Apply overrides
for override in "${OVERRIDES[@]}"; do
    key="${override%%=*}"
    value="${override#*=}"
    if grep -q "^${key}=" "$VARIANT_ENV"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$VARIANT_ENV"
    else
        echo "${key}=${value}" >> "$VARIANT_ENV"
    fi
done

echo "Variant env saved: $VARIANT_ENV"

# Restart with variant config
echo "Restarting stack with $CONFIG_ID..."
STACK_CONFIG_FILE="$VARIANT_ENV" bash "$SCRIPT_DIR/stack.sh" restart

# Wait for ready
echo "Waiting for health..."
if ! STACK_CONFIG_FILE="$VARIANT_ENV" bash "$SCRIPT_DIR/stack.sh" wait-ready 300; then
    echo "ERROR: Stack failed to start for $CONFIG_ID"
    echo "FAIL" > "$RUN_DIR/results/raw/status-$CONFIG_ID.txt"
    # Log failure
    docker logs --tail 50 llamacpp-server-p8001 > "$RUN_DIR/results/raw/crash-logs-$CONFIG_ID.txt" 2>&1 || true
    nvidia-smi > "$RUN_DIR/results/raw/vram-crash-$CONFIG_ID.txt" 2>&1 || true
    exit 1
fi

# Capture startup logs
docker logs llamacpp-server-p8001 2>&1 | head -100 > "$RUN_DIR/results/raw/startup-$CONFIG_ID.txt"
echo "OK" > "$RUN_DIR/results/raw/status-$CONFIG_ID.txt"

# Capture VRAM after model load
nvidia-smi --query-gpu=index,memory.used,memory.total,memory.free --format=csv,noheader,nounits \
    > "$RUN_DIR/results/raw/vram-loaded-$CONFIG_ID.txt"

# Save actual container command
docker inspect llamacpp-server-p8001 --format '{{json .Config.Cmd}}' \
    > "$RUN_DIR/results/raw/cmd-$CONFIG_ID.txt" 2>&1

# Smoke test
echo "Smoke test..."
if ! curl -fsS --max-time 60 "$ENDPOINT/chat/completions" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: ok\"}],\"max_tokens\":8,\"stream\":false}" > /dev/null 2>&1; then
    echo "WARNING: Smoke test FAILED for $CONFIG_ID"
    echo "SMOKE_FAIL" >> "$RUN_DIR/results/raw/status-$CONFIG_ID.txt"
fi

# Run speed benchmark
echo "Running speed benchmark..."
CONTEXT_LENGTHS="${OPT_CONTEXT_LENGTHS:-1k,10k,64k,128k}"
python3 "$SCRIPT_DIR/_opt_bench.py" \
    --config-id "$CONFIG_ID" \
    --run-dir "$RUN_DIR" \
    --endpoint "$ENDPOINT" \
    --model "$MODEL" \
    --context-lengths "$CONTEXT_LENGTHS" \
    --max-tokens 128 \
    --timeout 600

# Capture VRAM after benchmark
nvidia-smi --query-gpu=index,memory.used,memory.total,memory.free --format=csv,noheader,nounits \
    > "$RUN_DIR/results/raw/vram-after-bench-$CONFIG_ID.txt"

echo "=== $CONFIG_ID complete ==="
