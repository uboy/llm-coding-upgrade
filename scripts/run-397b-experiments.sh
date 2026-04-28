#!/usr/bin/env bash
# Runs 2 and 3 of the V100 RAM overflow experiment.
# Prerequisite: IQ2_XXS and IQ2_XS files must be fully downloaded.
# Run after downloads complete. Temporarily stops V100 prod for each run.
set -uo pipefail

STACK_SCRIPT="/data/home/<user>/proj/llm-coding-upgrade/scripts/stack.sh"
EXP_DOC="/data/home/<user>/proj/llm-coding-upgrade/experiments/v100-ram-overflow-397b-exp.md"
MODEL_BASE="/data/shared/<user>/models/Qwen3.5-397B-A17B-GGUF"
LLAMA_IMAGE="ghcr.io/ggml-org/llama.cpp:server-cuda"
EXP_CONTAINER="llamacpp-exp-p8002"

run_experiment() {
  local run_name="$1"   # e.g. "Run2_IQ2_XXS"
  local model_dir="$2"  # e.g. /models/.../IQ2_XXS/Qwen_...
  local model_path="$3" # path inside container

  echo ""
  echo "========================================="
  echo "  $run_name"
  echo "========================================="

  # Wait for model file to exist and be complete
  local host_model="${model_dir}"
  echo "Checking model file: $host_model"
  if [[ ! -f "$host_model" ]]; then
    echo "ERROR: model file not found: $host_model"
    exit 1
  fi

  # Stop prod
  echo "[1/5] Stopping prod V100 container..."
  docker stop llamacpp-server-p8001 2>/dev/null || true
  docker rm   llamacpp-server-p8001 2>/dev/null || true
  sleep 5

  nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader

  # Start experiment container
  echo "[2/5] Starting $run_name container..."
  docker run -d --name "$EXP_CONTAINER" \
    --gpus '"device=0,1,2"' \
    --restart no \
    -v /data/shared/<user>/models:/models \
    -p 8002:8080 \
    "$LLAMA_IMAGE" \
    --model "$model_path" \
    --ctx-size 8192 \
    --cache-type-k q8_0 --cache-type-v q8_0 \
    --split-mode layer \
    --tensor-split 1,1,1 \
    --parallel 1 \
    --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0 \
    --host 0.0.0.0 --port 8080 \
    -ngl 100

  # Wait for it to load (large model, give up to 15 min)
  echo "[3/5] Waiting for model to load (up to 15 min)..."
  for i in $(seq 1 90); do
    sleep 10
    STATUS=$(docker inspect "$EXP_CONTAINER" --format "{{.State.Health.Status}}" 2>/dev/null || echo "unknown")
    VRAM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader | paste -sd'+' | bc 2>/dev/null || echo "?")
    echo "  [${i}/90] health=$STATUS  VRAM_used=${VRAM} MiB"
    if [[ "$STATUS" == "healthy" ]]; then
      break
    fi
  done

  # VRAM snapshot
  echo "[4/5] VRAM snapshot:"
  nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader

  # Warmup
  echo "[5/5] Warmup + measurements..."
  curl -s --max-time 300 -X POST http://localhost:8002/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"local","messages":[{"role":"user","content":"Write a Python quicksort."}],"max_tokens":128}' \
    | python3 -c "import sys,json; d=json.load(sys.stdin); t=d['timings']; print(f'  warmup  decode={t[\"predicted_per_second\"]:.2f} tok/s  prompt={t[\"prompt_per_second\"]:.2f} tok/s')" 2>&1 || true

  for i in 1 2 3; do
    curl -s --max-time 180 -X POST http://localhost:8002/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d "{\"model\":\"local\",\"messages\":[{\"role\":\"user\",\"content\":\"Implement binary search in Python.\"}],\"max_tokens\":128}" \
      | python3 -c "
import sys, json
d = json.load(sys.stdin)
t = d['timings']
vram_cmd = 'nvidia-smi --query-gpu=memory.used --format=csv,noheader'
print(f'  run $i  decode={t[\"predicted_per_second\"]:.2f} tok/s  prompt={t[\"prompt_per_second\"]:.2f} tok/s')
" 2>&1 || true
  done

  # Cleanup
  docker stop "$EXP_CONTAINER" && docker rm "$EXP_CONTAINER"

  # Restart prod
  echo "Restarting prod V100..."
  bash "$STACK_SCRIPT" restart
  echo "  waiting for prod to become healthy..."
  for i in $(seq 1 30); do
    sleep 20
    STATUS=$(docker inspect llamacpp-server-p8001 --format "{{.State.Health.Status}}" 2>/dev/null || echo "unknown")
    echo "  [${i}] prod health=$STATUS"
    [[ "$STATUS" == "healthy" ]] && break
  done

  echo "$run_name DONE."
}

# ─── Run 2: IQ2_XXS ───────────────────────────────────────────────────────────
IQ2_XXS_DIR="$MODEL_BASE/IQ2_XXS"
IQ2_XXS_FILE=$(find "$IQ2_XXS_DIR" -name "*IQ2_XXS*-00001-of-*.gguf" 2>/dev/null | head -1)

if [[ -z "$IQ2_XXS_FILE" ]]; then
  echo "IQ2_XXS not yet downloaded. Waiting (checking every 2 min)..."
  while [[ -z "$IQ2_XXS_FILE" ]]; do
    sleep 120
    IQ2_XXS_FILE=$(find "$IQ2_XXS_DIR" -name "*IQ2_XXS*-00001-of-*.gguf" 2>/dev/null | head -1)
    echo "  $(date '+%H:%M') still waiting... size=$(du -sh "$IQ2_XXS_DIR" 2>/dev/null | cut -f1)"
  done
fi

IQ2_XXS_MODEL_PATH=$(echo "$IQ2_XXS_FILE" | sed 's|/data/shared/<user>/models|/models|')
run_experiment "Run2_IQ2_XXS" "$IQ2_XXS_FILE" "$IQ2_XXS_MODEL_PATH"

# ─── Run 3: IQ2_XS ────────────────────────────────────────────────────────────
IQ2_XS_DIR="$MODEL_BASE/IQ2_XS"
IQ2_XS_FILE=$(find "$IQ2_XS_DIR" -name "*IQ2_XS*-00001-of-*.gguf" 2>/dev/null | head -1)

if [[ -z "$IQ2_XS_FILE" ]]; then
  echo "IQ2_XS not yet downloaded. Waiting (checking every 2 min)..."
  while [[ -z "$IQ2_XS_FILE" ]]; do
    sleep 120
    IQ2_XS_FILE=$(find "$IQ2_XS_DIR" -name "*IQ2_XS*-00001-of-*.gguf" 2>/dev/null | head -1)
    echo "  $(date '+%H:%M') still waiting... size=$(du -sh "$IQ2_XS_DIR" 2>/dev/null | cut -f1)"
  done
fi

IQ2_XS_MODEL_PATH=$(echo "$IQ2_XS_FILE" | sed 's|/data/shared/<user>/models|/models|')
run_experiment "Run3_IQ2_XS" "$IQ2_XS_FILE" "$IQ2_XS_MODEL_PATH"

echo ""
echo "All runs complete. Update experiments/v100-ram-overflow-397b-exp.md with results."
