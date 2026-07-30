#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
STACK_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
CONFIG_FILE="${STACK_CONFIG_FILE:-$STACK_ROOT/stack.env}"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Missing config file: $CONFIG_FILE" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$CONFIG_FILE"
set +a

container_exists() {
  docker inspect "$1" >/dev/null 2>&1
}

remove_container_if_exists() {
  local name="$1"
  if container_exists "$name"; then
    docker rm -f "$name" >/dev/null
  fi
}

render_proxy() {
  mkdir -p "$(dirname "$PROXY_FILE")"
  cat >"$PROXY_FILE" <<EOF
const http = require("http");

const LISTEN_PORT = ${PROXY_CONTAINER_PORT};
const TARGET_HOST = "${PROXY_TARGET_HOST}";
const TARGET_PORT = ${PROXY_TARGET_PORT};
const MODEL_ALIAS = "${PROXY_MODEL_ALIAS}";
const REAL_MODEL = "${PROXY_REAL_MODEL}";

function handleModels(res) {
  const body = JSON.stringify({
    object: "list",
    data: [
      {
        id: MODEL_ALIAS,
        object: "model",
        created: Date.now(),
        owned_by: "local",
      },
    ],
  });
  res.writeHead(200, {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

const server = http.createServer((clientReq, clientRes) => {
  if (clientReq.method === "OPTIONS") {
    clientRes.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
      "Access-Control-Max-Age": "86400",
    });
    clientRes.end();
    return;
  }

  const url = clientReq.url;

  if (clientReq.method === "GET" && /\/?v1\/models|^\/models/.test(url)) {
    console.log(\`[models] GET \${url}\`);
    return handleModels(clientRes);
  }

  const chunks = [];
  clientReq.on("data", (chunk) => chunks.push(chunk));
  clientReq.on("end", () => {
    let rawBody = Buffer.concat(chunks);

    if (rawBody.length > 0) {
      try {
        const json = JSON.parse(rawBody);
        if (json.model === MODEL_ALIAS) {
          json.model = REAL_MODEL;
        }
        rawBody = Buffer.from(JSON.stringify(json));
      } catch {
      }
    }

    let targetPath = url;
    if (!targetPath.startsWith("/v1")) {
      targetPath = "/v1" + targetPath;
    }

    console.log(
      \`[proxy] \${clientReq.method} \${url} -> \${TARGET_HOST}:\${TARGET_PORT}\${targetPath} (\${rawBody.length} bytes)\`
    );

    let upstreamResponded = false;

    const proxyReq = http.request(
      {
        hostname: TARGET_HOST,
        port: TARGET_PORT,
        path: targetPath,
        method: clientReq.method,
        headers: {
          "Content-Type": "application/json",
          "Content-Length": rawBody.length,
        },
      },
      (proxyRes) => {
        upstreamResponded = true;
        // Clear connect timeout — we got headers, upstream is alive
        clearTimeout(connectTimer);

        // Response timeout: 600s (10 min) for long LLM generations
        proxyRes.setTimeout(600000, () => {
          console.error("[timeout] upstream response stalled");
          proxyRes.destroy(new Error("upstream response timeout"));
        });

        const headers = { ...proxyRes.headers };
        headers["access-control-allow-origin"] = "*";
        clientRes.writeHead(proxyRes.statusCode, headers);
        proxyRes.pipe(clientRes);

        // Handle upstream disconnecting mid-stream
        proxyRes.on("error", (err) => {
          console.error(\`[upstream error] \${err.message}\`);
          if (!clientRes.writableEnded) {
            clientRes.end();
          }
        });
      }
    );

    // Connect timeout: 10s — fail fast if upstream is unreachable
    // Uses socket event to detect actual TCP connect, not inactivity timer
    const connectTimer = setTimeout(() => {
      console.error("[timeout] upstream connect timeout");
      proxyReq.destroy(new Error("connect timeout"));
    }, 10000);

    proxyReq.on("socket", (socket) => {
      if (socket.connecting) {
        socket.once("connect", () => {
          clearTimeout(connectTimer);
        });
      } else {
        // Already connected (keep-alive)
        clearTimeout(connectTimer);
      }
    });

    proxyReq.on("error", (err) => {
      console.error(\`[error] \${err.message}\`);
      if (!clientRes.headersSent) {
        clientRes.writeHead(502, { "Content-Type": "application/json" });
      }
      clientRes.end(
        JSON.stringify({ error: { message: \`Proxy error: \${err.message}\` } })
      );
    });

    // If client disconnects prematurely (before upstream responded),
    // abort upstream request to free resources
    // Note: clientReq "close" fires when the readable side finishes, which
    // is normal after reading the request body. We detect real client
    // disconnection via the writable response side closing.
    clientRes.on("close", () => {
      if (!upstreamResponded && !proxyReq.destroyed) {
        proxyReq.destroy();
      }
    });

    proxyReq.write(rawBody);
    proxyReq.end();
  });

  clientReq.on("error", (err) => {
    console.error(\`[client error] \${err.message}\`);
  });
});

server.listen(LISTEN_PORT, "0.0.0.0", () => {
  console.log(\`LLM Proxy listening on :\${LISTEN_PORT}\`);
  console.log(\`  -> forwarding to \${TARGET_HOST}:\${TARGET_PORT}\`);
  console.log(\`  Model alias: "\${MODEL_ALIAS}" -> "\${REAL_MODEL}"\`);
  console.log(\`  Models endpoint: http://localhost:\${LISTEN_PORT}/v1/models\`);
  console.log(\`  Chat endpoint: http://localhost:\${LISTEN_PORT}/v1/chat/completions\`);
});
EOF
}

start_llama() {
  if [[ ! -f "${LLAMA_MODELS_HOST_DIR}/${LLAMA_MODEL_PATH#/models/}" ]]; then
    echo "Missing model file: ${LLAMA_MODELS_HOST_DIR}/${LLAMA_MODEL_PATH#/models/}" >&2
    exit 1
  fi

  # draft model: mount <user> models dir as /models_<user> if draft is configured
  local draft_volume_args=()
  local draft_args=()
  if [[ -n "${LLAMA_DRAFT_MODEL_PATH:-}" ]]; then
    draft_volume_args=(-v "/data/shared/<user>/models:/models_<user>")
    draft_args=(
      --model-draft  "${LLAMA_DRAFT_MODEL_PATH}"
      -ngld          "${LLAMA_DRAFT_GPU_LAYERS:-100}"
      --draft-max    "${LLAMA_DRAFT_MAX:-16}"
      --draft-min    "${LLAMA_DRAFT_MIN:-5}"
      --draft-p-min  "${LLAMA_DRAFT_P_MIN:-0.75}"
    )
    echo "Speculative decoding enabled: ${LLAMA_DRAFT_MODEL_PATH}"
  fi

  docker run -d \
    --name "$LLAMA_CONTAINER" \
    --restart unless-stopped \
    --log-opt max-size=100m \
    --log-opt max-file=3 \
    --gpus all \
    -e "CUDA_VISIBLE_DEVICES=${LLAMA_GPU_DEVICES}" \
    ${LLAMA_ARG_FLASH_ATTN:+-e "LLAMA_ARG_FLASH_ATTN=${LLAMA_ARG_FLASH_ATTN}"} \
    -p "${LLAMA_HOST_PORT}:${LLAMA_CONTAINER_PORT}" \
    -v "${LLAMA_MODELS_HOST_DIR}:/models" \
    "${draft_volume_args[@]}" \
    "$LLAMA_IMAGE" \
    -m "$LLAMA_MODEL_PATH" \
    --host 0.0.0.0 \
    --port "${LLAMA_CONTAINER_PORT}" \
    --n-gpu-layers "${LLAMA_GPU_LAYERS}" \
    --ctx-size "${LLAMA_CTX_SIZE}" \
    --split-mode "${LLAMA_SPLIT_MODE}" \
    ${LLAMA_MAIN_GPU:+--main-gpu "${LLAMA_MAIN_GPU}"} \
    --tensor-split "${LLAMA_TENSOR_SPLIT}" \
    --parallel "${LLAMA_PARALLEL}" \
    --batch-size "${LLAMA_BATCH_SIZE:-2048}" \
    --ubatch-size "${LLAMA_UBATCH_SIZE:-512}" \
    --fit "${LLAMA_FIT}" \
    ${LLAMA_FIT_TARGET:+--fit-target "${LLAMA_FIT_TARGET}"} \
    --cache-type-k "${LLAMA_CACHE_TYPE_K:-q8_0}" \
    --cache-type-v "${LLAMA_CACHE_TYPE_V:-q8_0}" \
    --reasoning "${LLAMA_REASONING:-off}" \
    --jinja \
    --temp "${LLAMA_TEMP:-1.0}" \
    --top-p "${LLAMA_TOP_P:-0.95}" \
    --top-k "${LLAMA_TOP_K:-40}" \
    --min-p "${LLAMA_MIN_P:-0.0}" \
    --repeat-penalty "${LLAMA_REPEAT_PENALTY:-1.1}" \
    ${LLAMA_OVERRIDE_KV:+--override-kv "$LLAMA_OVERRIDE_KV"} \
    ${LLAMA_NO_KV_OFFLOAD:+--no-kv-offload} \
    "${draft_args[@]}"
}

start_proxy() {
  render_proxy

  docker run -d \
    --name "$PROXY_CONTAINER" \
    --restart unless-stopped \
    -p "${PROXY_HOST_PORT}:${PROXY_CONTAINER_PORT}" \
    --add-host=host.docker.internal:host-gateway \
    -v "${PROXY_FILE}:/app/proxy.js:ro" \
    "$PROXY_IMAGE" \
    node /app/proxy.js
}

start_openwebui() {
  if [[ "${OPENWEBUI_ENABLED}" != "true" ]]; then
    return
  fi

  local openwebui_openai_base_urls="${OPENWEBUI_OPENAI_BASE_URLS:-${OPENWEBUI_OPENAI_BASE_URL:-}}"
  local openwebui_openai_api_keys="${OPENWEBUI_OPENAI_API_KEYS:-${OPENWEBUI_OPENAI_API_KEY:-}}"

  if [[ -z "$openwebui_openai_base_urls" ]]; then
    echo "Missing Open WebUI base URL(s): set OPENWEBUI_OPENAI_BASE_URLS or OPENWEBUI_OPENAI_BASE_URL" >&2
    exit 1
  fi

  if [[ -z "$openwebui_openai_api_keys" ]]; then
    echo "Missing Open WebUI API key(s): set OPENWEBUI_OPENAI_API_KEYS or OPENWEBUI_OPENAI_API_KEY" >&2
    exit 1
  fi

  docker run -d \
    --name "$OPENWEBUI_CONTAINER" \
    --restart unless-stopped \
    --gpus "device=${OPENWEBUI_GPU_DEVICES}" \
    --log-opt max-size=100m \
    --log-opt max-file=3 \
    -v "${OPENWEBUI_DATA_VOLUME}:/app/backend/data" \
    -v "${OPENWEBUI_EMBEDDING_HOST_DIR}:/app/backend/data/cache/embedding/models/intfloat_multilingual-e5-large:ro" \
    -p "${OPENWEBUI_HOST_PORT}:${OPENWEBUI_CONTAINER_PORT}" \
    -e "OPENAI_API_BASE_URLS=${openwebui_openai_base_urls}" \
    -e "OPENAI_API_KEYS=${openwebui_openai_api_keys}" \
    -e "WEBUI_AUTH=${OPENWEBUI_WEBUI_AUTH}" \
    -e "OFFLINE_MODE=${OPENWEBUI_OFFLINE_MODE}" \
    -e "HF_HUB_OFFLINE=${OPENWEBUI_HF_HUB_OFFLINE}" \
    -e "RAG_EMBEDDING_MODEL=${OPENWEBUI_RAG_EMBEDDING_MODEL}" \
    -e "RAG_EMBEDDING_MODEL_AUTO_UPDATE=${OPENWEBUI_RAG_EMBEDDING_MODEL_AUTO_UPDATE}" \
    -e "RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE=${OPENWEBUI_RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE}" \
    -e "WHISPER_MODEL_AUTO_UPDATE=${OPENWEBUI_WHISPER_MODEL_AUTO_UPDATE}" \
    -e "ENABLE_VERSION_UPDATE_CHECK=${OPENWEBUI_ENABLE_VERSION_UPDATE_CHECK}" \
    -e "CUDA_VISIBLE_DEVICES=${OPENWEBUI_GPU_DEVICES}" \
    --add-host=host.docker.internal:host-gateway \
    "$OPENWEBUI_IMAGE" \
    bash start.sh
}

down_stack() {
  remove_container_if_exists "$PROXY_CONTAINER"
  remove_container_if_exists "$LLAMA_CONTAINER"
  if [[ "${OPENWEBUI_ENABLED}" == "true" ]]; then
    remove_container_if_exists "$OPENWEBUI_CONTAINER"
  fi
}

up_stack() {
  down_stack
  start_llama
  start_proxy
  start_openwebui
}

status_stack() {
  if [[ "${OPENWEBUI_ENABLED}" == "true" ]]; then
    docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E "^(${LLAMA_CONTAINER}|${PROXY_CONTAINER}|${OPENWEBUI_CONTAINER})\b" || true
  else
    docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E "^(${LLAMA_CONTAINER}|${PROXY_CONTAINER})\b" || true
  fi
}

logs_stack() {
  local target="${2:-all}"
  case "$target" in
    llama) docker logs -f "$LLAMA_CONTAINER" ;;
    proxy) docker logs -f "$PROXY_CONTAINER" ;;
    webui) docker logs -f "$OPENWEBUI_CONTAINER" ;;
    all)
      docker logs --tail 100 "$LLAMA_CONTAINER" || true
      docker logs --tail 100 "$PROXY_CONTAINER" || true
      if [[ "${OPENWEBUI_ENABLED}" == "true" ]]; then
        docker logs --tail 100 "$OPENWEBUI_CONTAINER" || true
      fi
      ;;
    *)
      echo "Unknown log target: $target" >&2
      exit 1
      ;;
  esac
}

wait_ready() {
  local timeout="${1:-300}"
  local elapsed=0
  echo "Waiting for llama.cpp to become ready (timeout=${timeout}s)..."
  while (( elapsed < timeout )); do
    if curl -fsS --max-time 5 "http://127.0.0.1:${LLAMA_HOST_PORT}/health" >/dev/null 2>&1; then
      echo "llama.cpp ready after ${elapsed}s"
      return 0
    fi
    sleep 5
    (( elapsed += 5 ))
    if (( elapsed % 30 == 0 )); then
      echo "  ... still waiting (${elapsed}s/${timeout}s)"
    fi
  done
  echo "llama.cpp did not become ready within ${timeout}s" >&2
  return 1
}

smoke_stack() {
  curl -fsS --max-time 10 "http://127.0.0.1:${PROXY_HOST_PORT}/v1/models"
  echo
  curl -fsS --max-time 120 "http://127.0.0.1:${PROXY_HOST_PORT}/v1/chat/completions" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"${PROXY_MODEL_ALIAS}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: ok\"}],\"max_tokens\":8,\"stream\":false}"
  echo
}

usage() {
  cat <<EOF
Usage: $(basename "$0") <up|down|restart|status|logs|smoke|wait-ready|render-proxy> [target]

Commands:
  up            Recreate and start the whole stack.
  down          Stop and remove stack containers.
  restart       Recreate and start the whole stack.
  status        Show stack container status.
  logs [target] Show logs for all, llama, proxy, or webui.
  smoke         Run a basic API smoke test via the proxy.
  wait-ready [timeout]
                Wait for llama.cpp /health endpoint (default 300s).
  render-proxy  Regenerate ${PROXY_FILE} from ${CONFIG_FILE}.
EOF
}

cmd="${1:-}"

case "$cmd" in
  up|restart)
    up_stack
    ;;
  down)
    down_stack
    ;;
  status)
    status_stack
    ;;
  logs)
    logs_stack "$@"
    ;;
  smoke)
    smoke_stack
    ;;
  wait-ready)
    wait_ready "${2:-300}"
    ;;
  render-proxy)
    render_proxy
    ;;
  *)
    usage
    exit 1
    ;;
esac
