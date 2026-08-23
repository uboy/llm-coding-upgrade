#!/usr/bin/env bash
# needle-run.sh <kvtype> <ctx>
set -u
KV="$1"; CTX="$2"
PORT=8081
TAG="needle-$KV-$CTX"
docker rm -f needle-run >/dev/null 2>&1
docker run --gpus all -d --name needle-run -p "$PORT:8080" -v /home/<user>/proj/dflash2-bench/models:/models llamacpp-turboquant:fork \
  -m /models/qwen3.8-27b/UD-Q4_K_M.gguf -ngl 99 --ctx-size "$CTX" \
  --cache-type-k "$KV" --cache-type-v "$KV" --host 0.0.0.0 --port 8080 >/dev/null
i=0
while ! curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1; do
  if [ "$(docker inspect -f "{{.State.Running}}" needle-run 2>/dev/null)" != "true" ]; then
    echo "RESULT kv=$KV ctx=$CTX status=DEAD_AT_LOAD"; docker logs needle-run > "$TAG.dead.log" 2>&1; docker rm -f needle-run >/dev/null 2>&1; exit 1; fi
  sleep 3; i=$((i+1)); if [ "$i" -gt 200 ]; then echo "RESULT kv=$KV ctx=$CTX status=TIMEOUT"; docker rm -f needle-run >/dev/null 2>&1; exit 1; fi
done
echo "=== $KV ctx=$CTX healthy, vram: $(nvidia-smi --query-gpu=memory.used --format=csv,noheader) ==="
python3 ~/proj/bigmodel-bench/needle-test.py "http://localhost:$PORT" pos "$CTX"
python3 ~/proj/bigmodel-bench/needle-test.py "http://localhost:$PORT" neg "$CTX"
docker logs needle-run > "$TAG.log.full" 2>&1
docker rm -f needle-run >/dev/null 2>&1
