#!/usr/bin/env bash
# opt-run-all.sh — Run all V100 optimization experiments sequentially
# Each experiment: restart container + speed test + capture state
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
STACK_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
RUN_DIR="${OPT_RUN_DIR:-$(ls -td "$STACK_ROOT"/runs/v100-opt-* | head -1)}"
ENDPOINT="${OPT_ENDPOINT:-http://localhost:8001/v1}"
MODEL="${OPT_MODEL:-qwen}"
BASELINE_ENV="$RUN_DIR/stack.env.baseline"
CONTEXT_LENGTHS="${OPT_CONTEXT_LENGTHS:-1k,10k}"

echo "=== V100 Optimization Experiment Runner ==="
echo "Run dir: $RUN_DIR"
echo "Endpoint: $ENDPOINT"
echo "Context lengths: $CONTEXT_LENGTHS"
echo ""

run_experiment() {
    local config_id="$1"
    shift
    local overrides=("$@")
    local variant_env="$RUN_DIR/stack.env.$config_id"

    echo ""
    echo "================================================================"
    echo "=== Experiment: $config_id ==="
    echo "Overrides: ${overrides[*]:-none}"
    echo "================================================================"

    # Create variant env from baseline
    cp "$BASELINE_ENV" "$variant_env"

    # Apply overrides
    for override in "${overrides[@]}"; do
        local key="${override%%=*}"
        local value="${override#*=}"
        if grep -q "^${key}=" "$variant_env"; then
            sed -i "s|^${key}=.*|${key}=${value}|" "$variant_env"
        else
            echo "${key}=${value}" >> "$variant_env"
        fi
    done

    # Restart with variant config (only llama container, not proxy/webui)
    echo "Restarting llama.cpp..."
    STACK_CONFIG_FILE="$variant_env" bash "$SCRIPT_DIR/stack.sh" restart

    # Wait for health
    echo "Waiting for health..."
    if ! STACK_CONFIG_FILE="$variant_env" bash "$SCRIPT_DIR/stack.sh" wait-ready 300; then
        echo "ERROR: Stack failed to start for $config_id"
        echo "FAIL" > "$RUN_DIR/results/raw/status-$config_id.txt"
        docker logs --tail 50 llamacpp-server-p8001 > "$RUN_DIR/results/raw/crash-logs-$config_id.txt" 2>&1 || true
        nvidia-smi > "$RUN_DIR/results/raw/vram-crash-$config_id.txt" 2>&1 || true
        echo "SKIP: $config_id (failed to start)"
        return 1
    fi

    # Capture startup state
    docker logs llamacpp-server-p8001 2>&1 | head -80 > "$RUN_DIR/results/raw/startup-$config_id.txt"
    echo "OK" > "$RUN_DIR/results/raw/status-$config_id.txt"
    nvidia-smi --query-gpu=index,memory.used,memory.total,memory.free --format=csv,noheader,nounits \
        > "$RUN_DIR/results/raw/vram-loaded-$config_id.txt"
    docker inspect llamacpp-server-p8001 --format '{{json .Config.Cmd}}' \
        > "$RUN_DIR/results/raw/cmd-$config_id.txt" 2>&1

    # Smoke test
    echo "Smoke test..."
    if ! curl -fsS --max-time 120 "$ENDPOINT/chat/completions" \
        -H 'Content-Type: application/json' \
        -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: ok\"}],\"max_tokens\":8,\"stream\":false}" > /dev/null 2>&1; then
        echo "WARNING: Smoke test FAILED for $config_id"
        echo "SMOKE_FAIL" >> "$RUN_DIR/results/raw/status-$config_id.txt"
    fi

    # Run speed benchmark
    echo "Speed benchmark ($CONTEXT_LENGTHS)..."
    python3 "$SCRIPT_DIR/_opt_bench.py" \
        --config-id "$config_id" \
        --run-dir "$RUN_DIR" \
        --endpoint "$ENDPOINT" \
        --model "$MODEL" \
        --context-lengths "$CONTEXT_LENGTHS" \
        --max-tokens 128 \
        --timeout 600

    # Capture VRAM after benchmark
    nvidia-smi --query-gpu=index,memory.used,memory.total,memory.free --format=csv,noheader,nounits \
        > "$RUN_DIR/results/raw/vram-after-bench-$config_id.txt"

    echo "=== $config_id COMPLETE ==="
}

# ── Experiment A: Flash Attention ──────────────────────────────────────────────
echo ""
echo "========== EXPERIMENT A: Flash Attention =========="
run_experiment A1-flash-on LLAMA_ARG_FLASH_ATTN=on || true
run_experiment A2-flash-off LLAMA_ARG_FLASH_ATTN=off || true

# ── Experiment B: ubatch tuning ───────────────────────────────────────────────
echo ""
echo "========== EXPERIMENT B: ubatch tuning =========="
run_experiment B1-ubatch-256 LLAMA_UBATCH_SIZE=256 || true
run_experiment B2-ubatch-768 LLAMA_UBATCH_SIZE=768 || true
run_experiment B3-ubatch-1024 LLAMA_UBATCH_SIZE=1024 || true
run_experiment B4-ubatch-1536 LLAMA_UBATCH_SIZE=1536 || true
run_experiment B5-ubatch-2048 LLAMA_UBATCH_SIZE=2048 || true

# ── Experiment D: KV cache type ───────────────────────────────────────────────
echo ""
echo "========== EXPERIMENT D: KV cache type =========="
run_experiment D1-kv-q8q8 LLAMA_CACHE_TYPE_K=q8_0 LLAMA_CACHE_TYPE_V=q8_0 || true
run_experiment D2-kv-q4q8 LLAMA_CACHE_TYPE_K=q4_0 LLAMA_CACHE_TYPE_V=q8_0 || true

# ── Experiment E: tensor-split rebalance ──────────────────────────────────────
echo ""
echo "========== EXPERIMENT E: tensor-split rebalance =========="
run_experiment E1-ts-95-1025-1025 LLAMA_TENSOR_SPLIT=0.95,1.025,1.025 || true
run_experiment E2-ts-90-105-105 LLAMA_TENSOR_SPLIT=0.90,1.05,1.05 || true
run_experiment E3-ts-85-1075-1075 LLAMA_TENSOR_SPLIT=0.85,1.075,1.075 || true

# ── Experiment G: fit on/off ─────────────────────────────────────────────────
echo ""
echo "========== EXPERIMENT G: fit on/off =========="
run_experiment G1-fit-off LLAMA_FIT=off || true

# ── Restore baseline config ──────────────────────────────────────────────────
echo ""
echo "========== Restoring baseline config =========="
STACK_CONFIG_FILE="$BASELINE_ENV" bash "$SCRIPT_DIR/stack.sh" restart
STACK_CONFIG_FILE="$BASELINE_ENV" bash "$SCRIPT_DIR/stack.sh" wait-ready 300 || true
echo "Baseline restored."

echo ""
echo "=== ALL EXPERIMENTS COMPLETE ==="
echo "Results: $RUN_DIR/results/"
