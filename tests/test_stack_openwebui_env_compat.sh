#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$TMP_DIR/bin" "$TMP_DIR/models/test-model" "$TMP_DIR/openwebui-cache"
touch "$TMP_DIR/models/test-model/model.gguf"

cat >"$TMP_DIR/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

log_file="${FAKE_DOCKER_LOG:?}"

case "${1:-}" in
  inspect)
    exit 1
    ;;
  rm)
    exit 0
    ;;
  run)
    printf '%s\n' "$*" >>"$log_file"
    echo fake-container-id
    exit 0
    ;;
  ps|logs)
    exit 0
    ;;
  *)
    echo "unsupported docker subcommand: $*" >&2
    exit 1
    ;;
esac
EOF
chmod +x "$TMP_DIR/bin/docker"

write_config() {
  local config_path="$1"
  local openwebui_url_key="$2"
  local openwebui_url_value="$3"
  local openwebui_key_key="$4"
  local openwebui_key_value="$5"

  cat >"$config_path" <<EOF
LLAMA_CONTAINER=llamacpp-server-p8001
LLAMA_IMAGE=fake-llama
LLAMA_HOST_PORT=8001
LLAMA_CONTAINER_PORT=8080
LLAMA_MODELS_HOST_DIR=$TMP_DIR/models
LLAMA_MODEL_PATH=/models/test-model/model.gguf
LLAMA_GPU_DEVICES=0
LLAMA_GPU_LAYERS=100
LLAMA_CTX_SIZE=32768
LLAMA_SPLIT_MODE=layer
LLAMA_TENSOR_SPLIT=1
LLAMA_PARALLEL=1
LLAMA_FIT=on
LLAMA_CACHE_TYPE_K=q8_0
LLAMA_CACHE_TYPE_V=q8_0
LLAMA_REASONING=on
LLAMA_TEMP=0.6
LLAMA_TOP_P=0.95
LLAMA_TOP_K=20
LLAMA_MIN_P=0.0

PROXY_CONTAINER=llm-proxy-p4001
PROXY_IMAGE=fake-proxy
PROXY_HOST_PORT=4001
PROXY_CONTAINER_PORT=4001
PROXY_FILE=$TMP_DIR/proxy.js
PROXY_MODEL_ALIAS=qwen
PROXY_REAL_MODEL=model.gguf
PROXY_TARGET_HOST=host.docker.internal
PROXY_TARGET_PORT=8001

OPENWEBUI_ENABLED=true
OPENWEBUI_CONTAINER=open-webui-p3001
OPENWEBUI_IMAGE=fake-openwebui
OPENWEBUI_HOST_PORT=3001
OPENWEBUI_CONTAINER_PORT=8080
OPENWEBUI_GPU_DEVICES=0
OPENWEBUI_DATA_VOLUME=$TMP_DIR/openwebui-cache
OPENWEBUI_EMBEDDING_HOST_DIR=$TMP_DIR/models
OPENWEBUI_WEBUI_AUTH=true
OPENWEBUI_OFFLINE_MODE=true
OPENWEBUI_HF_HUB_OFFLINE=1
OPENWEBUI_RAG_EMBEDDING_MODEL=intfloat/multilingual-e5-large
OPENWEBUI_RAG_EMBEDDING_MODEL_AUTO_UPDATE=false
OPENWEBUI_RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE=false
OPENWEBUI_WHISPER_MODEL_AUTO_UPDATE=false
OPENWEBUI_ENABLE_VERSION_UPDATE_CHECK=false
$openwebui_url_key=$openwebui_url_value
$openwebui_key_key=$openwebui_key_value
EOF
}

run_case() {
  local case_name="$1"
  local url_key="$2"
  local url_value="$3"
  local key_key="$4"
  local key_value="$5"
  local expected_url="$6"
  local expected_key="$7"
  local config_path="$TMP_DIR/$case_name.env"
  local log_path="$TMP_DIR/$case_name.log"

  : >"$log_path"
  write_config "$config_path" "$url_key" "$url_value" "$key_key" "$key_value"

  PATH="$TMP_DIR/bin:$PATH" \
  FAKE_DOCKER_LOG="$log_path" \
  STACK_CONFIG_FILE="$config_path" \
  bash "$ROOT_DIR/scripts/stack.sh" up >/dev/null

  grep -F "OPENAI_API_BASE_URLS=$expected_url" "$log_path" >/dev/null
  grep -F "OPENAI_API_KEYS=$expected_key" "$log_path" >/dev/null
}

run_case \
  singular_only \
  OPENWEBUI_OPENAI_BASE_URL \
  http://example.local/v1 \
  OPENWEBUI_OPENAI_API_KEY \
  dummy \
  http://example.local/v1 \
  dummy

run_case \
  plural_priority \
  OPENWEBUI_OPENAI_BASE_URLS \
  http://plural.example/v1 \
  OPENWEBUI_OPENAI_API_KEYS \
  plural-dummy \
  http://plural.example/v1 \
  plural-dummy

echo "stack OpenWebUI env compatibility: ok"
