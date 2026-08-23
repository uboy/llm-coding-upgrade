#!/usr/bin/env bash
# needle-v100.sh <kv> <ctx> [extra...] - filled needle on GPU2
set -u
B=/data/home/<user>/proj/bigmodel-bench-v100
KV="$1"; CTX="$2"; shift 2; EXTRA="$*"
PORT=8081
TAG="v100-needle-$KV-$CTX"
docker rm -f v100run >/dev/null 2>&1
docker run --gpus "\"device=2\"" -d --name v100run -p "$PORT:8080" -v "$B/models:/models" llamacpp-turboquant:v100 \
  -m /models/qwen3.8-27b/UD-Q4_K_M.gguf -ngl 99 --ctx-size "$CTX" \
  --cache-type-k "$KV" --cache-type-v "$KV" $EXTRA --host 0.0.0.0 --port 8080 >/dev/null
i=0
while ! curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1; do
  if [ "$(docker inspect -f "{{.State.Running}}" v100run 2>/dev/null)" != "true" ]; then
    echo "RESULT kv=$KV ctx=$CTX status=DEAD_AT_LOAD"; docker logs v100run > "$B/$TAG.dead.log" 2>&1; docker rm -f v100run >/dev/null 2>&1; exit 1; fi
  sleep 3; i=$((i+1)); if [ "$i" -gt 240 ]; then echo "RESULT kv=$KV ctx=$CTX status=TIMEOUT"; docker rm -f v100run >/dev/null 2>&1; exit 1; fi
done
echo "=== $KV ctx=$CTX healthy, vram2: $(nvidia-smi --query-gpu=memory.used --format=csv,noheader -i 2) ==="
python3 $B/needle-test.py "http://localhost:$PORT" pos "$CTX"
python3 $B/needle-test.py "http://localhost:$PORT" neg "$CTX"
docker logs v100run > "$B/$TAG.log.full" 2>&1
grep -E "eval time|draft acceptance" "$B/$TAG.log.full" | tail -3
docker rm -f v100run >/dev/null 2>&1
