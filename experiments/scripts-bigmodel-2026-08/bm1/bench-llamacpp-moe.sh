#!/usr/bin/env bash
# llama.cpp vanilla baseline on gpt-oss-120b GGUF with --n-cpu-moe (experts on CPU)
set -u
PORT=8081
IMG=ghcr.io/ggml-org/llama.cpp:server-cuda
GGUF=/home/<user>/proj/bigmodel-bench/models/gpt-oss-120b-gguf/gpt-oss-120b-MXFP4.gguf
T0=$(date +%s)
docker rm -f moe-run >/dev/null 2>&1
docker run --gpus all -d --name moe-run -p "$PORT:8080" -v "/home/<user>/proj/bigmodel-bench/models/gpt-oss-120b-gguf:/models" "$IMG" \
  -m /models/gpt-oss-120b-MXFP4.gguf -ngl 99 --n-cpu-moe 99 -c 8192 --host 0.0.0.0 --port 8080 >/dev/null
i=0
while ! curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1; do
  if [ "$(docker inspect -f "{{.State.Running}}" moe-run 2>/dev/null)" != "true" ]; then
    echo "RESULT baseline status=DEAD_AT_LOAD"; docker logs moe-run > llamacpp-moe.dead.log 2>&1; docker rm -f moe-run >/dev/null 2>&1; exit 1; fi
  sleep 5; i=$((i+1)); if [ "$i" -gt 240 ]; then echo "RESULT baseline status=TIMEOUT"; docker logs moe-run > llamacpp-moe.dead.log 2>&1; docker rm -f moe-run >/dev/null 2>&1; exit 1; fi
done
T1=$(date +%s)
echo "load_and_healthy_s=$((T1-T0)) vram_MiB=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader)"
cd ~/proj/bigmodel-bench
./ft-venv/bin/python bench-ft.py "http://localhost:$PORT/v1/chat/completions" x prompt-essay.txt 384
./ft-venv/bin/python bench-ft.py "http://localhost:$PORT/v1/chat/completions" x prompt-essay.txt 384
./ft-venv/bin/python bench-ft.py "http://localhost:$PORT/v1/chat/completions" x prompt-coding.txt 384
docker logs moe-run > llamacpp-moe.log.full 2>&1
grep -E "eval time|prompt eval" llamacpp-moe.log.full | tail -4
docker rm -f moe-run >/dev/null 2>&1
