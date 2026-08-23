#!/usr/bin/env bash
# bench-longctx.sh <kv> <ctx> <fill_frac> [extra...]
set -u
KV="$1"; CTX="$2"; FILL="${3:-0.92}"; shift 3; EXTRA="$*"
PORT=8081
TAG="lc-$(printf "%s-%s" "$KV" "$CTX")$( [ -n "$EXTRA" ] && echo -$(echo "$EXTRA" | tr -cd "a-z0-9" | cut -c1-16) )"
docker rm -f lc-run >/dev/null 2>&1
docker run --gpus all -d --name lc-run -p "$PORT:8080" -v /home/<user>/proj/dflash2-bench/models:/models llamacpp-turboquant:fork \
  -m /models/qwen3.8-27b/UD-Q4_K_M.gguf -ngl 99 --ctx-size "$CTX" \
  --cache-type-k "$KV" --cache-type-v "$KV" $EXTRA --host 0.0.0.0 --port 8080 >/dev/null
i=0
while ! curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1; do
  if [ "$(docker inspect -f "{{.State.Running}}" lc-run 2>/dev/null)" != "true" ]; then
    echo "RESULT kv=$KV ctx=$CTX extra=\"$EXTRA\" status=DEAD_AT_LOAD"
    docker logs lc-run > "$TAG.dead.log" 2>&1; docker rm -f lc-run >/dev/null 2>&1; exit 1; fi
  sleep 3; i=$((i+1)); if [ "$i" -gt 200 ]; then echo "RESULT kv=$KV ctx=$CTX status=TIMEOUT"; docker rm -f lc-run >/dev/null 2>&1; exit 1; fi
done
VRAM0=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
python3 - "$PORT" "$CTX" "$FILL" << "PYEOF"
import json, sys, time, urllib.request
port, ctx, fill = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
para = ("The quarterly infrastructure review covered rack allocations, cooling curves, "
        "firmware versions for the redundant power controllers, and the migration schedule "
        "for the legacy inventory database. Engineers presented latency histograms and "
        "capacity forecasts for the next three fiscal quarters. ")
target = int(ctx * fill)
est = int(len(para) / 6.8)
n = target // est
prompt = para * n + "\n\nQuestion: List the main recurring topics of the report above as a numbered list.\n"
body = json.dumps({"prompt": prompt, "n_predict": 256, "temperature": 0, "cache_prompt": False}).encode()
req = urllib.request.Request("http://localhost:%d/completion" % port, data=body, headers={"Content-Type": "application/json"})
t0 = time.time()
r = json.load(urllib.request.urlopen(req, timeout=3600))
wall = time.time() - t0
content = r.get("content", "")
print("RESP stop=%s len=%d head=%s" % (r.get("stop_type", r.get("stop")), len(content), repr(content[:70])))
print("PROMPT tokens_approx=%d chars=%d wall_s=%.1f" % (n * est, len(prompt), wall))
PYEOF
VRAM1=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
docker logs lc-run > "$TAG.log.full" 2>&1
PPT=$(grep -oE "prompt eval time.*" "$TAG.log.full" | tail -1)
EVT=$(grep -oE "eval time.*" "$TAG.log.full" | tail -1)
echo "RESULT kv=$KV ctx=$CTX fill=$FILL extra=\"$EXTRA\" status=OK vram_load=$VRAM0 vram_peak=$VRAM1"
echo "  $PPT"
echo "  $EVT"
docker rm -f lc-run >/dev/null 2>&1
