#!/usr/bin/env bash
B=/data/home/<user>/proj/bigmodel-bench-v100
LOG=$B/run-all-v100.log
say() { echo "[$(date -Is)] $*" >> $LOG; }
{
  T0=$(date +%s)
  docker rm -f v100ds >/dev/null 2>&1
  docker run --gpus "\"device=2\"" -d --name v100ds -p 8081:8080 -v $B/models/deepseek-q4xl:/models llamacpp-turboquant:v100 \
    -m /models/DeepSeek-V4-Flash-0731-UD-Q4_K_XL-00001-of-00005.gguf \
    -ngl 99 --n-cpu-moe 999 -c 8192 --cache-type-k q8_0 --cache-type-v q8_0 \
    --host 0.0.0.0 --port 8080 >/dev/null
  i=0
  while ! curl -sf http://localhost:8081/health >/dev/null 2>&1; do
    if [ "$(docker inspect -f "{{.State.Running}}" v100ds 2>/dev/null)" != "true" ]; then
      echo "DEAD_AT_LOAD"; docker logs v100ds > $B/v100-deepseek.dead2.log 2>&1; exit 1; fi
    sleep 10; i=$((i+1)); if [ $i -gt 1080 ]; then echo "TIMEOUT_3H"; docker logs v100ds > $B/v100-deepseek.dead2.log 2>&1; exit 1; fi
  done
  echo "load_and_healthy_s=$(( $(date +%s) - T0 )) vram2=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader -i 2)"
  cd $B
  $B/ft-venv/bin/python bench-ft.py http://localhost:8081/v1/chat/completions x prompt-essay.txt 384
  $B/ft-venv/bin/python bench-ft.py http://localhost:8081/v1/chat/completions x prompt-essay.txt 384
  curl -s http://localhost:8081/v1/chat/completions -H "Content-Type: application/json" -d "{\"model\":\"x\",\"messages\":[{\"role\":\"user\",\"content\":\"What is the capital of France? One word.\"}],\"max_tokens\":300,\"temperature\":0}" | head -c 500
  echo
  docker logs v100ds > $B/v100-deepseek.log.full 2>&1
  grep -oE "eval time.*" $B/v100-deepseek.log.full | tail -2
  docker rm -f v100ds >/dev/null 2>&1
} > $B/v100-deepseek.txt 2>&1
say "DEEPSEEK2_DONE (v100-deepseek.txt)"
