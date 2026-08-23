#!/usr/bin/env bash
B=/data/home/<user>/proj/bigmodel-bench-v100
LOG=$B/run-all-v100.log
say() { echo "[$(date -Is)] $*" >> $LOG; }
D=$B/models/deepseek-q4xl/dspark-DeepSeek-V4-Flash-0731-Q8_0.gguf
TARGET=10896057440
# download with verify-retry
for i in $(seq 1 60); do
  sz=$(stat -c%s "$D" 2>/dev/null || echo 0)
  [ "$sz" = "$TARGET" ] && break
  aria2c -x 16 -s 16 -k 4M --file-allocation=none --console-log-level=warn --summary-interval=0 \
    -c -d $B/models/deepseek-q4xl -o dspark-DeepSeek-V4-Flash-0731-Q8_0.gguf \
    "https://huggingface.co/unsloth/DeepSeek-V4-Flash-0731-GGUF/resolve/main/dspark-DeepSeek-V4-Flash-0731-Q8_0.gguf"
  sleep 15
done
sz=$(stat -c%s "$D" 2>/dev/null || echo 0)
[ "$sz" = "$TARGET" ] || { say "DSPARK_DL_FAIL"; exit 1; }
say "dspark weights ok (10.9GB)"
{
  T0=$(date +%s)
  docker rm -f v100ds2 >/dev/null 2>&1
  docker run --gpus "\"device=2\"" -d --name v100ds2 -p 8081:8080 -v $B/models/deepseek-q4xl:/models llamacpp-turboquant:v100 \
    -m /models/DeepSeek-V4-Flash-0731-UD-Q4_K_XL-00001-of-00005.gguf \
    -md /models/dspark-DeepSeek-V4-Flash-0731-Q8_0.gguf -ngld 99 \
    --spec-type draft-dspark --spec-draft-n-max 2 \
    -ngl 99 --n-cpu-moe 999 -c 8192 --cache-type-k q8_0 --cache-type-v q8_0 \
    --host 0.0.0.0 --port 8080 >/dev/null
  i=0
  while ! curl -sf http://localhost:8081/health >/dev/null 2>&1; do
    if [ "$(docker inspect -f "{{.State.Running}}" v100ds2 2>/dev/null)" != "true" ]; then
      echo "DEAD_AT_LOAD"; docker logs v100ds2 > $B/v100-dspark.dead.log 2>&1; exit 1; fi
    sleep 10; i=$((i+1)); if [ $i -gt 360 ]; then echo "TIMEOUT_1H"; docker logs v100ds2 > $B/v100-dspark.dead.log 2>&1; exit 1; fi
  done
  echo "load_and_healthy_s=$(( $(date +%s) - T0 )) vram2=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader -i 2)"
  cd $B
  $B/ft-venv/bin/python bench-ft.py http://localhost:8081/v1/chat/completions x prompt-essay.txt 384
  $B/ft-venv/bin/python bench-ft.py http://localhost:8081/v1/chat/completions x prompt-essay.txt 384
  $B/ft-venv/bin/python bench-ft.py http://localhost:8081/v1/chat/completions x prompt-coding.txt 384
  docker logs v100ds2 > $B/v100-dspark.log.full 2>&1
  grep -E "eval time|draft acceptance" $B/v100-dspark.log.full | tail -5
  docker rm -f v100ds2 >/dev/null 2>&1
} > $B/v100-dspark.txt 2>&1
say "DSPARK_DONE (v100-dspark.txt)"
