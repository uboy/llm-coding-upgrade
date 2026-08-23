#!/usr/bin/env bash
# Autonomous V100 phase-8 runner (GPU2 only). Survives network breaks.
B=/data/home/<user>/proj/bigmodel-bench-v100
LOG=$B/run-all-v100.log
say() { echo "[$(date -Is)] $*" >> $LOG; }
say "=== run-all-v100 started ==="

wait_marker() { for i in $(seq 1 1440); do [ -f "$B/$1" ] && return 0; sleep 60; done; return 1; }

# V2: wait for image
for i in $(seq 1 240); do docker image inspect llamacpp-turboquant:v100 >/dev/null 2>&1 && break; sleep 30; done
docker image inspect llamacpp-turboquant:v100 >/dev/null 2>&1 || { say "FAIL no image"; exit 1; }
say "image ready"

# V1+V3: KV ladder 32k + MTP 8k (needs qwen weights)
if wait_marker DONE-qwen; then
  {
    bash $B/bench-turbo-v100.sh q8_0 32768
    bash $B/bench-turbo-v100.sh q4_0 32768
    bash $B/bench-turbo-v100.sh turbo3 32768
    bash $B/bench-turbo-v100.sh turbo4 32768
    bash $B/bench-turbo-v100.sh q8_0 8192
    bash $B/bench-turbo-v100.sh q8_0 8192 --spec-type draft-mtp --spec-draft-n-max 2
  } > $B/v100-kv-ladder.txt 2>&1
  say "V3_KV_LADDER_DONE (v100-kv-ladder.txt)"
else say "V3_FAIL no qwen marker"; fi

# V4: long-ctx ladder (the 200-250k question)
if wait_marker DONE-qwen; then
  {
    echo "--- 160k turbo3+MTP filled ---"
    bash $B/needle-v100.sh turbo3 163840 --spec-type draft-mtp --spec-draft-n-max 2
    echo "--- 196k turbo3+MTP (draft-KV check; may fail by own reason) ---"
    bash $B/needle-v100.sh turbo3 196608 --spec-type draft-mtp --spec-draft-n-max 2
    echo "--- 196k turbo3 noMTP ubatch2048 filled ---"
    bash $B/needle-v100.sh turbo3 196608 --ubatch-size 2048
    echo "--- 262k turbo3 noMTP ubatch2048 filled ---"
    bash $B/needle-v100.sh turbo3 262144 --ubatch-size 2048
  } > $B/v100-longctx.txt 2>&1
  say "V4_LONGCTX_DONE (v100-longctx.txt)"
fi

# V5: dense ceiling on 32GB
if wait_marker DONE-qwen; then
  {
    bash $B/bench-turbo-v100.sh q8_0 8192  # warm
    docker rm -f v100run >/dev/null 2>&1
    docker run --gpus "\"device=2\"" -d --name v100run -p 8081:8080 -v $B/models:/models llamacpp-turboquant:v100 \
      -m /models/qwen3.8-27b/UD-Q6_K.gguf -ngl 99 --ctx-size 8192 --cache-type-k q8_0 --cache-type-v q8_0 --host 0.0.0.0 --port 8080 >/dev/null
    i=0; while ! curl -sf http://localhost:8081/health >/dev/null 2>&1; do
      [ "$(docker inspect -f "{{.State.Running}}" v100run 2>/dev/null)" != "true" ] && { echo "Q6_K: DEAD_AT_LOAD"; docker logs v100run > $B/v100-q6k.dead.log 2>&1; break; }
      sleep 3; i=$((i+1)); [ $i -gt 120 ] && { echo "Q6_K: TIMEOUT"; break; }; done
    if curl -sf http://localhost:8081/health >/dev/null 2>&1; then
      echo "Q6_K healthy vram2=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader -i 2)"
      curl -s http://localhost:8081/completion -H "Content-Type: application/json" -d "{\"prompt\":\"Write a short essay about AI impact on software development.\",\"n_predict\":256,\"temperature\":0}" >/dev/null
      sleep 1; docker logs v100run > $B/v100-q6k.log.full 2>&1
      grep -oE "eval time.*" $B/v100-q6k.log.full | tail -1
    fi
    docker rm -f v100run >/dev/null 2>&1
  } > $B/v100-dense.txt 2>&1
  say "V5_DENSE_DONE (v100-dense.txt)"
fi

# V6: FreeToken on cc 7.0 (expected incompatibility - document reason)
if wait_marker DONE-20b; then
  export PATH="$HOME/.local/bin:$PATH"
  if [ ! -f $B/ft-venv/bin/ft ]; then
    for i in 1 2 3 4 5 6 7 8 9 10; do
      UV_HTTP_TIMEOUT=30 uv pip install --python $B/ft-venv/bin/python "freetoken[accel]" >> $B/ft-install.log 2>&1 && [ -f $B/ft-venv/bin/ft ] && break
      sleep 60
    done
  fi
  {
    cd $B
    setsid nohup env CUDA_VISIBLE_DEVICES=2 $B/ft-venv/bin/ft serve --model $B/models/gpt-oss-20b > $B/ft-serve-v100.log 2>&1 < /dev/null &
    FTPID=$!
    ok=""
    for i in $(seq 1 120); do
      grep -q "ready to serve" $B/ft-serve-v100.log 2>/dev/null && { ok=1; break; }
      kill -0 $FTPID 2>/dev/null || break
      sleep 5
    done
    if [ -n "$ok" ]; then
      echo "UNEXPECTED_SUCCESS: ft ready on V100"
      $B/ft-venv/bin/python $B/bench-ft.py http://127.0.0.1:1919/v1/chat/completions x $B/prompt-essay.txt 384 || true
    else
      echo "EXPECTED_FAIL_OR_TIMEOUT (see ft-serve-v100.log tail):"
      tail -n 15 $B/ft-serve-v100.log
    fi
    pkill -f "ft serve" 2>/dev/null
  } > $B/v100-freetoken.txt 2>&1
  say "V6_FREETOKEN_DONE (v100-freetoken.txt)"
fi

# V7: llama.cpp --n-cpu-moe baseline on GPU2 (needs GGUF 63GB)
if wait_marker DONE-gguf120; then
  {
    T0=$(date +%s)
    docker rm -f v100moe >/dev/null 2>&1
    docker run --gpus "\"device=2\"" -d --name v100moe -p 8081:8080 -v $B/models/gpt-oss-120b-gguf:/models ghcr.io/ggml-org/llama.cpp:server-cuda \
      -m /models/gpt-oss-120b-MXFP4.gguf -ngl 99 --n-cpu-moe 99 -c 8192 --host 0.0.0.0 --port 8080 >/dev/null
    i=0; while ! curl -sf http://localhost:8081/health >/dev/null 2>&1; do
      [ "$(docker inspect -f "{{.State.Running}}" v100moe 2>/dev/null)" != "true" ] && { echo "DEAD_AT_LOAD"; docker logs v100moe > $B/v100-moe.dead.log 2>&1; break; }
      sleep 5; i=$((i+1)); [ $i -gt 360 ] && { echo "TIMEOUT"; break; }; done
    if curl -sf http://localhost:8081/health >/dev/null 2>&1; then
      echo "load_s=$(( $(date +%s) - T0 )) vram2=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader -i 2)"
      cd $B
      $B/ft-venv/bin/python $B/bench-ft.py http://localhost:8081/v1/chat/completions x $B/prompt-essay.txt 384 || python3 -c "print(bench unavailable)"
      docker logs v100moe > $B/v100-moe.log.full 2>&1
      grep -oE "eval time.*" $B/v100-moe.log.full | tail -1
    fi
    docker rm -f v100moe >/dev/null 2>&1
  } > $B/v100-moe.txt 2>&1
  say "V7_MOE_DONE (v100-moe.txt)"
fi
say "=== run-all-v100 finished ==="
