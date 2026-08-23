#!/usr/bin/env bash
# bench-turbo.sh <kvtype> <ctx> [extra flags...]
set -u
IMG=llamacpp-turboquant:fork
MODELS=/home/<user>/proj/dflash2-bench/models
OUT=/home/<user>/proj/bigmodel-bench
PORT=8081
KV="$1"; CTX="$2"; shift 2
EXTRA="$*"
TAG=$(printf "tq-%s-ctx%s" "$KV" "$CTX")
[ -n "$EXTRA" ] && TAG="$TAG-$(echo "$EXTRA" | tr -cd "a-z0-9" | cut -c1-24)"
docker rm -f tq-run >/dev/null 2>&1
docker run --gpus all -d --name tq-run -p "$PORT:8080" -v "$MODELS:/models" "$IMG" \
  -m /models/qwen3.8-27b/UD-Q4_K_M.gguf -ngl 99 --ctx-size "$CTX" \
  --cache-type-k "$KV" --cache-type-v "$KV" $EXTRA \
  --host 0.0.0.0 --port 8080 >/dev/null
i=0
while ! curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1; do
  if [ "$(docker inspect -f "{{.State.Running}}" tq-run 2>/dev/null)" != "true" ]; then
    echo "FATAL: tq-run exited (likely OOM at load) for $KV ctx=$CTX"
    docker logs tq-run > "$OUT/$TAG.dead.log" 2>&1; docker rm -f tq-run >/dev/null 2>&1
    echo "RESULT kv=$KV ctx=$CTX status=OOM_DEAD"; exit 1
  fi
  sleep 3; i=$((i+1)); if [ "$i" -gt 160 ]; then echo "RESULT kv=$KV ctx=$CTX status=TIMEOUT"; docker logs tq-run > "$OUT/$TAG.dead.log" 2>&1; docker rm -f tq-run >/dev/null 2>&1; exit 1; fi
done
sleep 2
VRAM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
# generation: short essay prompt, 256 tokens
curl -s http://localhost:$PORT/completion -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Write a short essay about the impact of artificial intelligence on software development practices.\",\"n_predict\":256,\"temperature\":0,\"cache_prompt\":false}" > "$OUT/$TAG-resp1.json" 2>/dev/null
sleep 1
docker logs tq-run > "$OUT/$TAG.log.full" 2>&1
PPT=$(grep -oE "prompt eval time.*" "$OUT/$TAG.log.full" | tail -1)
EVAL=$(grep -oE "eval time.*" "$OUT/$TAG.log.full" | tail -1)
CACHE=$(grep -iE "KV self size|kv cache|CUDA0 KV buffer" "$OUT/$TAG.log.full" | head -2 | tr "\n" " ")
echo "RESULT kv=$KV ctx=$CTX extra=\"$EXTRA\" status=OK vram_MiB=$VRAM"
echo "  $EVAL"
echo "  $CACHE"
docker rm -f tq-run >/dev/null 2>&1
