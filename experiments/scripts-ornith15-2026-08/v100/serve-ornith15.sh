#!/usr/bin/env bash
# serve-ornith15.sh <quant> <ctx> [gpu] [extra llama-server flags...]
#   quant: q4km | q6k | q8  (файл в /models/ornith15/)
# Поднимает Ornith-1.5-35B-A3B-GGUF на одной V100 (по умолчанию GPU2),
# порт 8081, health-wait, печатает VRAM. Эксперимент фазы 11 <internal>
# (local-llm-inference), прод-стек не трогает.
# Пример: bash serve-ornith15.sh q4km 32768 2 --cache-type-k q4_0 --cache-type-v q4_0
set -euo pipefail

B=/data/home/<user>/proj/bigmodel-bench-v100
IMAGE=ghcr.io/ggml-org/llama.cpp:server-cuda
PORT=8081
NAME=ornith15-run

case "${1:-}" in
  q4km) F=Ornith-1.5-35B-Q4_K_M.gguf ;;
  q6k)  F=Ornith-1.5-35B-Q6_K.gguf ;;
  q8)   F=Ornith-1.5-35B-Q8_0.gguf ;;
  *) echo "usage: $0 q4km|q6k|q8 <ctx> [gpu] [extra...]"; exit 2 ;;
esac
QUANT="$1"; CTX="${2:?ctx required}"; GPU="${3:-2}"; shift 3 || { shift 2; GPU=2; }
EXTRA="$*"

docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run --gpus "\"device=$GPU\"" -d --name "$NAME" \
  -p "$PORT:8080" -v "$B/models:/models" "$IMAGE" \
  -m "/models/ornith15/$F" \
  -ngl 999 \
  --ctx-size "$CTX" \
  --parallel 1 \
  --batch-size 2048 --ubatch-size 2048 \
  --jinja \
  --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0 \
  --host 0.0.0.0 --port 8080 $EXTRA >/dev/null

i=0
while ! curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1; do
  if [ "$(docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null)" != "true" ]; then
    echo "RESULT quant=$QUANT ctx=$CTX gpu=$GPU status=DEAD_AT_LOAD"
    docker logs "$NAME" > "$B/ornith15-$QUANT-$CTX.dead.log" 2>&1
    tail -20 "$B/ornith15-$QUANT-$CTX.dead.log"
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    exit 1
  fi
  sleep 3; i=$((i+1))
  if [ "$i" -gt 200 ]; then echo "RESULT quant=$QUANT ctx=$CTX status=TIMEOUT"; exit 1; fi
done

echo "=== ornith15 $QUANT ctx=$CTX gpu=$GPU healthy ==="
echo "vram$GPU: $(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader -i "$GPU")"
echo "log: docker logs $NAME; stop: docker rm -f $NAME"
