#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
STACK_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
CONFIG_FILE="${LB_STACK_CONFIG_FILE:-$STACK_ROOT/lb-proxy.env}"

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

render_lb_proxy() {
  # lb-proxy.js is managed as a static file with full health-check logic.
  # Only create it if it does not exist yet; otherwise leave it untouched.
  if [[ -f "$LB_PROXY_FILE" ]]; then
    return 0
  fi
  mkdir -p "$(dirname "$LB_PROXY_FILE")"

  local _backends_js=""
  IFS=',' read -ra _pairs <<< "$LB_PROXY_BACKENDS"
  for _pair in "${_pairs[@]}"; do
    local _h="${_pair%%:*}"
    local _p="${_pair##*:}"
    _backends_js+="  { host: \"${_h}\", port: ${_p} },"$'\n'
  done

  cat >"$LB_PROXY_FILE" <<EOF
const http = require("http");

const LISTEN_PORT = ${LB_PROXY_CONTAINER_PORT};
const MODEL_ALIAS = "${LB_PROXY_MODEL_ALIAS}";
const REAL_MODEL = "${LB_PROXY_REAL_MODEL}";
const BACKENDS = [
${_backends_js}];

let _rrIdx = 0;
function nextBackend(exclude = new Set()) {
  const pool = BACKENDS.filter((b) => !exclude.has(b));
  if (pool.length === 0) {
    return null;
  }
  const b = pool[_rrIdx % pool.length];
  _rrIdx++;
  return b;
}

function backendLabel(backend) {
  return `${backend.host}:${backend.port}`;
}

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
      } catch {}
    }

    let targetPath = url;
    if (!targetPath.startsWith("/v1")) {
      targetPath = "/v1" + targetPath;
    }

    const attempted = new Set();

    const tryBackend = (backend, attempt) => {
      attempted.add(backend);

      console.log(
        \`[lb] \${clientReq.method} \${url} -> \${backendLabel(backend)}\${targetPath} (\${rawBody.length} bytes, attempt=\${attempt})\`
      );

      const proxyReq = http.request(
        {
          hostname: backend.host,
          port: backend.port,
          path: targetPath,
          method: clientReq.method,
          headers: {
            "Content-Type": "application/json",
            "Content-Length": rawBody.length,
          },
        },
        (proxyRes) => {
          const headers = { ...proxyRes.headers };
          headers["access-control-allow-origin"] = "*";
          headers["x-lb-backend"] = backendLabel(backend);
          headers["x-lb-attempt"] = String(attempt);
          clientRes.writeHead(proxyRes.statusCode, headers);
          proxyRes.pipe(clientRes);
        }
      );

      proxyReq.on("error", (err) => {
        console.error(
          \`[lb error] backend=\${backendLabel(backend)} attempt=\${attempt} \${err.message}\`
        );

        const fallback = nextBackend(attempted);
        if (!clientRes.headersSent && fallback) {
          console.warn(
            \`[lb retry] request retrying via \${backendLabel(fallback)} after \${backendLabel(backend)} failed\`
          );
          return tryBackend(fallback, attempt + 1);
        }

        if (!clientRes.headersSent) {
          clientRes.writeHead(502, { "Content-Type": "application/json" });
        }
        clientRes.end(
          JSON.stringify({ error: { message: \`LB proxy error: \${err.message}\` } })
        );
      });

      proxyReq.write(rawBody);
      proxyReq.end();
    };

    const backend = nextBackend();
    if (!backend) {
      clientRes.writeHead(503, { "Content-Type": "application/json" });
      clientRes.end(JSON.stringify({ error: { message: "LB proxy error: no backend available" } }));
      return;
    }

    tryBackend(backend, 1);
  });

  clientReq.on("error", (err) => {
    console.error(\`[client error] \${err.message}\`);
  });
});

server.listen(LISTEN_PORT, "0.0.0.0", () => {
  console.log(\`LLM LB Proxy listening on :\${LISTEN_PORT}\`);
  console.log(\`  Model alias: "\${MODEL_ALIAS}" -> "\${REAL_MODEL}"\`);
  BACKENDS.forEach((b, i) => console.log(\`  Backend[\${i}]: \${b.host}:\${b.port}\`));
  console.log(\`  Models endpoint: http://localhost:\${LISTEN_PORT}/v1/models\`);
  console.log(\`  Chat endpoint:   http://localhost:\${LISTEN_PORT}/v1/chat/completions\`);
});
EOF
}

start_lb_proxy() {
  render_lb_proxy

  docker run -d \
    --name "$LB_PROXY_CONTAINER" \
    --restart unless-stopped \
    --log-opt max-size=100m \
    --log-opt max-file=3 \
    -p "${LB_PROXY_HOST_PORT}:${LB_PROXY_CONTAINER_PORT}" \
    -v "${LB_PROXY_FILE}:/app/lb-proxy.js:ro" \
    "$LB_PROXY_IMAGE" \
    node /app/lb-proxy.js
}

up_stack() {
  remove_container_if_exists "$LB_PROXY_CONTAINER"
  start_lb_proxy
}

down_stack() {
  remove_container_if_exists "$LB_PROXY_CONTAINER"
}

status_stack() {
  docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' \
    | grep -E "^${LB_PROXY_CONTAINER}\b" || true
}

logs_stack() {
  docker logs -f "$LB_PROXY_CONTAINER"
}

smoke_stack() {
  curl -fsS --max-time 10 "http://127.0.0.1:${LB_PROXY_HOST_PORT}/v1/models"
  echo
  curl -fsS --max-time 120 "http://127.0.0.1:${LB_PROXY_HOST_PORT}/v1/chat/completions" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"${LB_PROXY_MODEL_ALIAS}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: ok\"}],\"max_tokens\":8,\"stream\":false}"
  echo
}

usage() {
  cat <<EOF
Usage: $(basename "$0") <up|down|restart|status|logs|smoke|render-proxy>

Commands:
  up            Start the LB proxy container.
  down          Stop and remove the LB proxy container.
  restart       Recreate and start the LB proxy container.
  status        Show container status.
  logs          Follow container logs.
  smoke         Run a basic API smoke test.
  render-proxy  Regenerate ${LB_PROXY_FILE} from ${CONFIG_FILE}.
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
    logs_stack
    ;;
  smoke)
    smoke_stack
    ;;
  render-proxy)
    render_lb_proxy
    ;;
  *)
    usage
    exit 1
    ;;
esac
