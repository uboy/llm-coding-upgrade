#!/usr/bin/env bash
B=/data/home/<user>/proj/bigmodel-bench-v100
LOG=$B/run-all-v100.log
say() { echo "[$(date -Is)] $*" >> $LOG; }
{
  T0=$(date +%s)
  docker rm -f v100ds3 >/dev/null 2>&1
  docker run --gpus "\"device=2\"" -d --name v100ds3 -p 8081:8080 -v $B/models/deepseek-q4xl:/models llamacpp-turboquant:v100 \
    -m /models/DeepSeek-V4-Flash-0731-UD-Q4_K_XL-00001-of-00005.gguf \
    -ngl 99 --n-cpu-moe 999 -c 131072 --ubatch-size 2048 \
    --cache-type-k q8_0 --cache-type-v q8_0 \
    --host 0.0.0.0 --port 8080 >/dev/null
  i=0
  while ! curl -sf http://localhost:8081/health >/dev/null 2>&1; do
    if [ "$(docker inspect -f "{{.State.Running}}" v100ds3 2>/dev/null)" != "true" ]; then
      echo "DEAD_AT_LOAD"; docker logs v100ds3 > $B/v100-ds-longctx.dead.log 2>&1; exit 1; fi
    sleep 10; i=$((i+1)); if [ $i -gt 180 ]; then echo "TIMEOUT_30MIN_LOAD"; docker logs v100ds3 > $B/v100-ds-longctx.dead.log 2>&1; exit 1; fi
  done
  echo "load_and_healthy_s=$(( $(date +%s) - T0 )) vram2=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader -i 2)"
  python3 $B/needle-test.py http://localhost:8081 pos 131072
  python3 $B/needle-test.py http://localhost:8081 neg 131072
  docker logs v100ds3 > $B/v100-ds-longctx.log.full 2>&1
  grep -E "eval time|KV|buffer" $B/v100-ds-longctx.log.full | tail -6
  nvidia-smi --query-gpu=memory.used --format=csv,noheader -i 2
  docker rm -f v100ds3 >/dev/null 2>&1
} > $B/v100-ds-longctx.txt 2>&1
say "DS_LONGCTX_DONE (v100-ds-longctx.txt)"
