#!/usr/bin/env bash
# bench-turbo-v100.sh <kv> <ctx> [extra...] - GPU2 only
set -u
B=/data/home/<user>/proj/bigmodel-bench-v100
KV="$1"; CTX="$2"; shift 2; EXTRA="$*"
PORT=8081
TAG="v100-$KV-$CTX$( [ -n "$EXTRA" ] && echo -$(echo "$EXTRA" | tr -cd "a-z0-9" | cut -c1-16) )"
docker rm -f v100run >/dev/null 2>&1
docker run --gpus "\"device=2\"" -d --name v100run -p "$PORT:8080" -v "$B/models:/models" llamacpp-turboquant:v100 \
  -m /models/qwen3.8-27b/UD-Q4_K_M.gguf -ngl 99 --ctx-size "$CTX" \
  --cache-type-k "$KV" --cache-type-v "$KV" $EXTRA --host 0.0.0.0 --port 8080 >/dev/null
i=0
while ! curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1; do
  if [ "$(docker inspect -f "{{.State.Running}}" v100run 2>/dev/null)" != "true" ]; then
    echo "RESULT kv=$KV ctx=$CTX extra=\"$EXTRA\" status=DEAD_AT_LOAD"
    docker logs v100run > "$B/$TAG.dead.log" 2>&1; docker rm -f v100run >/dev/null 2>&1; exit 1; fi
  sleep 3; i=$((i+1)); if [ "$i" -gt 240 ]; then echo "RESULT kv=$KV ctx=$CTX status=TIMEOUT"; docker rm -f v100run >/dev/null 2>&1; exit 1; fi
done
VRAM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 2)
curl -s http://localhost:$PORT/completion -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Write a short essay about the impact of artificial intelligence on software development practices.\",\"n_predict\":256,\"temperature\":0,\"cache_prompt\":false}" > "$B/$TAG-resp.json" 2>/dev/null
sleep 1; docker logs v100run > "$B/$TAG.log.full" 2>&1
PPT=$(grep -oE "prompt eval time.*" "$B/$TAG.log.full" | tail -1)
EVT=$(grep -oE "eval time.*" "$B/$TAG.log.full" | tail -1)
echo "RESULT kv=$KV ctx=$CTX extra=\"$EXTRA\" status=OK vram2_MiB=$VRAM"
echo "  $PPT"; echo "  $EVT"
docker rm -f v100run >/dev/null 2>&1
