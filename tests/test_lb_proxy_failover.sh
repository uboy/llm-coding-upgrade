#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TMP_DIR=$(mktemp -d)
PIDS=()

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
  rm -rf "$TMP_DIR"
}

trap cleanup EXIT

readarray -t PORTS < <(python3 - <<'PY'
import socket

ports = []
for _ in range(3):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    ports.append(str(sock.getsockname()[1]))
    sock.close()
print("\n".join(ports))
PY
)

LB_PORT="${PORTS[0]}"
FAIL_PORT="${PORTS[1]}"
OK_PORT="${PORTS[2]}"

python3 - <<'PY' "$FAIL_PORT" &
import socketserver
import sys

port = int(sys.argv[1])

class ResetHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            self.request.recv(1)
        except Exception:
            pass
        try:
            self.request.shutdown(2)
        except Exception:
            pass
        self.request.close()

with socketserver.ThreadingTCPServer(("127.0.0.1", port), ResetHandler) as server:
    server.daemon_threads = True
    server.serve_forever()
PY
PIDS+=("$!")

python3 - <<'PY' "$OK_PORT" &
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sys

port = int(sys.argv[1])

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length).decode("utf-8"))
        body = json.dumps(
            {
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "model": request["model"],
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "ok"},
                    }
                ],
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass

with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
    server.serve_forever()
PY
PIDS+=("$!")

python3 - <<'PY' "$ROOT_DIR/llm-lb-proxy/lb-proxy.js" "$TMP_DIR/lb-proxy.js" "$LB_PORT" "$FAIL_PORT" "$OK_PORT"
from pathlib import Path
import sys

src = Path(sys.argv[1]).read_text()
src = src.replace("const LISTEN_PORT = 4002;", f"const LISTEN_PORT = {sys.argv[3]};")
src = src.replace(
    'const BACKENDS_CONFIG = [\n  { host: "bm1", port: 8001 },\n  { host: "bm2", port: 8001 },\n];',
    'const BACKENDS_CONFIG = [\n'
    f'  {{ host: "127.0.0.1", port: {sys.argv[4]} }},\n'
    f'  {{ host: "127.0.0.1", port: {sys.argv[5]} }},\n'
    '];',
)
src = src.replace("const HEALTH_INTERVAL_MS = 15000;", "const HEALTH_INTERVAL_MS = 1000;")
Path(sys.argv[2]).write_text(src)
PY

node "$TMP_DIR/lb-proxy.js" >"$TMP_DIR/lb.log" 2>&1 &
PIDS+=("$!")

python3 - <<'PY' "$LB_PORT"
import sys
import time
import urllib.request

port = int(sys.argv[1])
deadline = time.time() + 10
last_error = None
while time.time() < deadline:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=1):
            sys.exit(0)
    except Exception as exc:
        last_error = exc
        time.sleep(0.1)
raise SystemExit(f"LB did not start in time: {last_error}")
PY

python3 - <<'PY' "$LB_PORT" "$OK_PORT"
import json
import sys
import urllib.request

lb_port = int(sys.argv[1])
ok_port = int(sys.argv[2])
payload = json.dumps(
    {
        "model": "qwen27b",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 8,
        "stream": False,
    }
).encode("utf-8")

req = urllib.request.Request(
    f"http://127.0.0.1:{lb_port}/v1/chat/completions",
    data=payload,
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=10) as resp:
    body = json.loads(resp.read().decode("utf-8"))
    assert resp.status == 200, resp.status
    assert resp.headers["x-lb-attempt"] == "2", resp.headers
    assert resp.headers["x-lb-backend"] == f"127.0.0.1:{ok_port}", resp.headers
    assert body["choices"][0]["message"]["content"] == "ok", body
PY

python3 - <<'PY' "$LB_PORT" "$FAIL_PORT" "$OK_PORT"
import json
import sys
import urllib.request

lb_port = int(sys.argv[1])
fail_port = int(sys.argv[2])
ok_port = int(sys.argv[3])

with urllib.request.urlopen(f"http://127.0.0.1:{lb_port}/lb-status", timeout=5) as resp:
    body = json.loads(resp.read().decode("utf-8"))

statuses = {item["backend"]: item for item in body["backends"]}
assert statuses[f"127.0.0.1:{fail_port}"]["healthy"] is False, statuses
assert statuses[f"127.0.0.1:{ok_port}"]["healthy"] is True, statuses
PY

grep -F "[lb retry] request retrying via" "$TMP_DIR/lb.log" >/dev/null

echo "lb proxy failover: ok"
