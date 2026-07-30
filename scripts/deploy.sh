#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
STACK_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
STACK_CONFIG="${STACK_CONFIG_FILE:-$STACK_ROOT/stack.env}"
LB_CONFIG="${LB_STACK_CONFIG_FILE:-$STACK_ROOT/lb-proxy.env}"

# ── Load configs ──────────────────────────────────────────────────────────────

load_config() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "Missing config: $file" >&2
    return 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "$file"
  set +a
}

load_stack()   { load_config "$STACK_CONFIG"; }
load_lb()      { load_config "$LB_CONFIG"; }
load_all()     { load_stack; load_lb; }

# ── Wait helpers ──────────────────────────────────────────────────────────────

wait_for_http() {
  local url="$1"
  local timeout="${2:-300}"
  local elapsed=0
  while (( elapsed < timeout )); do
    if curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 5
    (( elapsed += 5 ))
  done
  return 1
}

wait_for_remote_http() {
  local host="$1"
  local port="$2"
  local path="${3:-/health}"
  local timeout="${4:-300}"
  local elapsed=0
  while (( elapsed < timeout )); do
    if ssh -o ConnectTimeout=5 -o BatchMode=yes "$host" \
         "curl -fsS --max-time 5 http://127.0.0.1:${port}${path}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 5
    (( elapsed += 5 ))
  done
  return 1
}

# ── Local V100 stack ──────────────────────────────────────────────────────────

restart_local_stack() {
  echo "=== Restarting local V100 stack ==="
  STACK_CONFIG_FILE="$STACK_CONFIG" bash "$SCRIPT_DIR/stack.sh" restart
  echo "Waiting for llama.cpp..."
  if ! STACK_CONFIG_FILE="$STACK_CONFIG" bash "$SCRIPT_DIR/stack.sh" wait-ready 300; then
    echo "ERROR: llama.cpp failed to start" >&2
    return 1
  fi
  echo "V100 stack ready."
}

smoke_local_stack() {
  echo "--- V100 smoke ---"
  STACK_CONFIG_FILE="$STACK_CONFIG" bash "$SCRIPT_DIR/stack.sh" smoke
}

status_local_stack() {
  load_stack
  echo "--- V100 stack (config: ${STACK_CONFIG}) ---"

  # llama.cpp
  if docker inspect "$LLAMA_CONTAINER" >/dev/null 2>&1; then
    local state image ports uptime
    state=$(docker inspect --format '{{.State.Status}}' "$LLAMA_CONTAINER" 2>/dev/null || echo "unknown")
    image=$(docker inspect --format '{{.Config.Image}}' "$LLAMA_CONTAINER" 2>/dev/null || echo "?")
    ports=$(docker port "$LLAMA_CONTAINER" 2>/dev/null | head -1 || echo "?")
    # compute uptime
    local started
    started=$(docker inspect --format '{{.State.StartedAt}}' "$LLAMA_CONTAINER" 2>/dev/null || echo "")
    if [[ -n "$started" ]]; then
      uptime=$(python3 -c "
from datetime import datetime, timezone
raw = '${started}'.replace('Z','+00:00')
# Truncate microseconds to 6 digits for Python 3.10 compat
if '+' in raw:
    base, tz = raw.rsplit('+', 1)
    parts = base.split('.')
    if len(parts) == 2 and len(parts[1]) > 6:
        base = parts[0] + '.' + parts[1][:6]
    raw = base + '+' + tz
s = datetime.fromisoformat(raw)
delta = datetime.now(timezone.utc) - s
print(f'{delta.days}d {delta.seconds // 3600}h')
" 2>/dev/null || echo "?")
    else
      uptime="?"
    fi
    echo "  llama.cpp"
    echo "    container:  ${LLAMA_CONTAINER} (${state}, up ${uptime})"
    echo "    image:      ${image}"
    echo "    port:       ${ports}"
    echo "    model:      ${LLAMA_MODEL_PATH}"
    echo "    GPU:        ${LLAMA_GPU_DEVICES} (${LLAMA_GPU_LAYERS} layers, split=${LLAMA_SPLIT_MODE}, tensor=${LLAMA_TENSOR_SPLIT})"
    echo "    ctx:        ${LLAMA_CTX_SIZE}, parallel=${LLAMA_PARALLEL}, batch=${LLAMA_BATCH_SIZE:-2048}/${LLAMA_UBATCH_SIZE:-512}"
    echo "    cache:      k=${LLAMA_CACHE_TYPE_K:-q8_0}, v=${LLAMA_CACHE_TYPE_V:-q8_0}"
    echo "    reasoning:  ${LLAMA_REASONING:-off}"
    echo "    sampling:   temp=${LLAMA_TEMP:-1.0}, top_p=${LLAMA_TOP_P:-0.95}, top_k=${LLAMA_TOP_K:-40}, min_p=${LLAMA_MIN_P:-0.0}"
    echo "    fit:        ${LLAMA_FIT}"
    if [[ -n "${LLAMA_OVERRIDE_KV:-}" ]]; then
      echo "    override:   ${LLAMA_OVERRIDE_KV}"
    fi
  else
    echo "  llama.cpp: NOT RUNNING (container ${LLAMA_CONTAINER} not found)"
  fi

  echo

  # proxy
  if docker inspect "$PROXY_CONTAINER" >/dev/null 2>&1; then
    local state
    state=$(docker inspect --format '{{.State.Status}}' "$PROXY_CONTAINER" 2>/dev/null || echo "unknown")
    echo "  proxy"
    echo "    container:  ${PROXY_CONTAINER} (${state})"
    echo "    port:       :${PROXY_HOST_PORT} -> :${PROXY_CONTAINER_PORT}"
    echo "    alias:      ${PROXY_MODEL_ALIAS} -> ${PROXY_REAL_MODEL}"
    echo "    upstream:   ${PROXY_TARGET_HOST}:${PROXY_TARGET_PORT}"
  else
    echo "  proxy: NOT RUNNING (container ${PROXY_CONTAINER} not found)"
  fi

  echo

  # Open WebUI
  if [[ "${OPENWEBUI_ENABLED:-false}" == "true" ]]; then
    if docker inspect "$OPENWEBUI_CONTAINER" >/dev/null 2>&1; then
      local state
      state=$(docker inspect --format '{{.State.Status}}' "$OPENWEBUI_CONTAINER" 2>/dev/null || echo "unknown")
      echo "  open-webui"
      echo "    container:  ${OPENWEBUI_CONTAINER} (${state})"
      echo "    port:       :${OPENWEBUI_HOST_PORT} -> :${OPENWEBUI_CONTAINER_PORT}"
      echo "    GPU:        ${OPENWEBUI_GPU_DEVICES}"
      echo "    auth:       ${OPENWEBUI_WEBUI_AUTH}"
      echo "    upstream:   ${OPENWEBUI_OPENAI_BASE_URL}"
    else
      echo "  open-webui: NOT RUNNING (container ${OPENWEBUI_CONTAINER} not found)"
    fi
  else
    echo "  open-webui: DISABLED"
  fi
}

down_local_stack() {
  STACK_CONFIG_FILE="$STACK_CONFIG" bash "$SCRIPT_DIR/stack.sh" down
}

# ── LB proxy ──────────────────────────────────────────────────────────────────

restart_lb() {
  echo "=== Restarting LB proxy ==="
  LB_STACK_CONFIG_FILE="$LB_CONFIG" bash "$SCRIPT_DIR/lb-stack.sh" restart
  load_lb
  echo "Waiting for LB proxy on :${LB_PROXY_HOST_PORT}..."
  if ! wait_for_http "http://127.0.0.1:${LB_PROXY_HOST_PORT}/v1/models" 30; then
    echo "ERROR: LB proxy failed to start" >&2
    return 1
  fi
  echo "LB proxy ready."
}

smoke_lb() {
  echo "--- LB proxy smoke ---"
  LB_STACK_CONFIG_FILE="$LB_CONFIG" bash "$SCRIPT_DIR/lb-stack.sh" smoke
}

status_lb() {
  load_lb
  echo "--- LB proxy (config: ${LB_CONFIG}) ---"
  if docker inspect "$LB_PROXY_CONTAINER" >/dev/null 2>&1; then
    local state ports
    state=$(docker inspect --format '{{.State.Status}}' "$LB_PROXY_CONTAINER" 2>/dev/null || echo "unknown")
    ports=$(docker port "$LB_PROXY_CONTAINER" 2>/dev/null | head -1 || echo "?")
    echo "  container:  ${LB_PROXY_CONTAINER} (${state})"
    echo "  port:       ${ports}"
    echo "  alias:      ${LB_PROXY_MODEL_ALIAS} -> ${LB_PROXY_REAL_MODEL}"

    # Show backend health from /lb-status
    local lb_status
    lb_status=$(curl -fsS --max-time 5 "http://127.0.0.1:${LB_PROXY_HOST_PORT}/lb-status" 2>/dev/null || echo "")
    if [[ -n "$lb_status" ]]; then
      echo "$lb_status" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for b in d.get('backends', []):
    label = b['backend']
    h = 'UP' if b['healthy'] else 'DOWN'
    fails = b.get('consecutiveFails', 0)
    print(f'  backend:    {label} ({h}, fails={fails})')
" 2>/dev/null || echo "  backends:   (unable to parse)"
    else
      echo "  backends:   (lb-status endpoint unreachable)"
    fi
  else
    echo "  NOT RUNNING (container ${LB_PROXY_CONTAINER} not found)"
  fi
}

down_lb() {
  LB_STACK_CONFIG_FILE="$LB_CONFIG" bash "$SCRIPT_DIR/lb-stack.sh" down
}

# ── BM1/BM2 remote nodes ──────────────────────────────────────────────────────

restart_bm_node() {
  local label="$1"
  local ssh_host="$2"
  local container="$3"
  echo "Restarting ${label} (${ssh_host}, container=${container})..."
  if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$ssh_host" \
       "docker restart ${container}" 2>/dev/null; then
    echo "WARNING: failed to restart ${label} via SSH" >&2
    return 1
  fi
}

wait_bm_node() {
  local label="$1"
  local ssh_host="$2"
  local timeout="${3:-300}"
  echo "Waiting for ${label}..."
  if ! wait_for_remote_http "$ssh_host" 8001 "/health" "$timeout"; then
    echo "WARNING: ${label} did not become ready within ${timeout}s" >&2
    return 1
  fi
  echo "${label} ready."
}

restart_bm() {
  load_stack
  echo "=== Restarting BM1/BM2 ==="

  local fail=0

  if [[ -n "${BM1_HOST:-}" ]]; then
    restart_bm_node "BM1" "${BM1_HOST}" "${BM1_CONTAINER:-llamacpp-server-p8001}" || fail=1
  else
    echo "BM1_HOST not configured, skipping BM1."
  fi

  if [[ -n "${BM2_HOST:-}" ]]; then
    restart_bm_node "BM2" "${BM2_HOST}" "${BM2_CONTAINER:-llamacpp-server-p8001}" || fail=1
  else
    echo "BM2_HOST not configured, skipping BM2."
  fi

  if [[ -n "${BM1_HOST:-}" ]]; then
    wait_bm_node "BM1" "${BM1_HOST}" 300 || fail=1
  fi
  if [[ -n "${BM2_HOST:-}" ]]; then
    wait_bm_node "BM2" "${BM2_HOST}" 300 || fail=1
  fi

  return $fail
}

status_bm() {
  load_stack
  echo "--- BM nodes ---"
  for entry in "BM1:${BM1_HOST:-}:${BM1_CONTAINER:-llamacpp-server-p8001}" \
               "BM2:${BM2_HOST:-}:${BM2_CONTAINER:-llamacpp-server-p8001}"; do
    local label host container rest
    label="${entry%%:*}"
    rest="${entry#*:}"
    host="${rest%%:*}"
    container="${rest#*:}"
    if [[ -z "$host" ]]; then
      echo "  ${label}: not configured"
      continue
    fi
    echo "  ${label} (${host})"

    local state
    state=$(ssh -o ConnectTimeout=5 -o BatchMode=yes "$host" \
      "docker inspect --format '{{.State.Status}}' ${container} 2>/dev/null || echo missing" \
      2>/dev/null) || state="unreachable"
    state="${state// /}"
    echo "    container:  ${container} (${state})"

    if [[ "$state" == "running" ]]; then
      # Uptime — compute remotely with date to avoid Python nanosecond issues
      local uptime
      uptime=$(ssh -o ConnectTimeout=5 -o BatchMode=yes "$host" "
        started=\$(docker inspect --format '{{.State.StartedAt}}' ${container} 2>/dev/null | cut -d. -f1)
        if [ -n \"\$started\" ]; then
          epoch_s=\$(date -d \"\$started\" +%s 2>/dev/null || echo 0)
          epoch_n=\$(date +%s)
          if [ \"\$epoch_s\" -gt 0 ] 2>/dev/null; then
            diff=\$((epoch_n - epoch_s))
            echo \"\$((diff / 86400))d \$(( (diff % 86400) / 3600 ))h\"
          fi
        fi
      " 2>/dev/null) || uptime=""
      if [[ -n "$uptime" ]]; then
        echo "    uptime:     ${uptime}"
      else
        echo "    uptime:     ?"
      fi

      # Model props — fetch JSON via SSH, parse locally
      local bm_json
      bm_json=$(ssh -o ConnectTimeout=5 -o BatchMode=yes "$host" \
        "curl -fsS --max-time 5 http://127.0.0.1:8001/props 2>/dev/null" \
        2>/dev/null) || bm_json=""
      if [[ -n "$bm_json" ]]; then
        local props
        props=$(echo "$bm_json" | python3 -c "
import json, sys
d = json.load(sys.stdin)
ds = d.get('default_generation_settings', {})
gs = ds.get('params', {})
model = d.get('model_alias', '?')
n_ctx = ds.get('n_ctx', '?')
slots = d.get('total_slots', '?')
temp = round(gs.get('temperature', 0), 2)
top_p = round(gs.get('top_p', 0), 2)
top_k = gs.get('top_k', '?')
print(f'model={model}')
print(f'n_ctx={n_ctx}')
print(f'slots={slots}')
print(f'temp={temp}')
print(f'top_p={top_p}')
print(f'top_k={top_k}')
" 2>/dev/null) || props=""
        if [[ -n "$props" ]]; then
          local model n_ctx slots temp top_p top_k
          model=$(echo "$props" | grep '^model=' | cut -d= -f2-)
          n_ctx=$(echo "$props" | grep '^n_ctx=' | cut -d= -f2-)
          slots=$(echo "$props" | grep '^slots=' | cut -d= -f2-)
          temp=$(echo "$props" | grep '^temp=' | cut -d= -f2-)
          top_p=$(echo "$props" | grep '^top_p=' | cut -d= -f2-)
          top_k=$(echo "$props" | grep '^top_k=' | cut -d= -f2-)
          echo "    model:      ${model}"
          echo "    ctx:        ${n_ctx}, slots=${slots}"
          echo "    sampling:   temp=${temp}, top_p=${top_p}, top_k=${top_k}"
        else
          echo "    model:      (unable to parse props)"
        fi
      else
        echo "    model:      (unable to query)"
      fi

      # Health
      if ssh -o ConnectTimeout=5 -o BatchMode=yes "$host" \
           "curl -fsS --max-time 3 http://127.0.0.1:8001/health" >/dev/null 2>&1; then
        echo "    health:     OK"
      else
        echo "    health:     FAILING"
      fi
    fi
    echo
  done
}

# ── Composite commands ────────────────────────────────────────────────────────

do_restart() {
  local fail=0
  restart_local_stack || fail=1
  restart_bm || fail=1
  restart_lb || fail=1
  if (( fail )); then
    echo "WARNING: one or more services failed to restart" >&2
  fi
  echo "=== All restarts complete ==="
}

do_restart_local() {
  local fail=0
  restart_local_stack || fail=1
  restart_lb || fail=1
  if (( fail )); then
    echo "WARNING: one or more services failed to restart" >&2
  fi
  echo "=== Local restarts complete ==="
}

do_status() {
  status_local_stack
  echo
  status_bm
  echo
  status_lb
}

do_smoke() {
  smoke_local_stack
  echo
  smoke_lb
}

do_down() {
  down_lb
  down_local_stack
  echo "All local services stopped."
}

do_logs() {
  local target="${1:-all}"
  case "$target" in
    bm1)
      load_stack
      ssh -o BatchMode=yes "${BM1_HOST}" "docker logs --tail 100 ${BM1_CONTAINER}" 2>/dev/null || echo "Cannot reach BM1"
      ;;
    bm2)
      load_stack
      ssh -o BatchMode=yes "${BM2_HOST}" "docker logs --tail 100 ${BM2_CONTAINER}" 2>/dev/null || echo "Cannot reach BM2"
      ;;
    v100|stack)
      STACK_CONFIG_FILE="$STACK_CONFIG" bash "$SCRIPT_DIR/stack.sh" logs all
      ;;
    lb|proxy)
      LB_STACK_CONFIG_FILE="$LB_CONFIG" bash "$SCRIPT_DIR/lb-stack.sh" logs
      ;;
    all)
      STACK_CONFIG_FILE="$STACK_CONFIG" bash "$SCRIPT_DIR/stack.sh" logs all
      echo
      echo "=== LB proxy ==="
      LB_STACK_CONFIG_FILE="$LB_CONFIG" bash "$SCRIPT_DIR/lb-stack.sh" logs
      ;;
    *)
      echo "Unknown log target: $target" >&2
      echo "Use: v100, lb, bm1, bm2, all" >&2
      return 1
      ;;
  esac
}

# ── CLI ────────────────────────────────────────────────────────────────────────

usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [options]

Commands:
  restart            Restart ALL services (V100 + BM1/BM2 + LB proxy)
  restart-local      Restart only local services (V100 + LB proxy)
  restart-bm         Restart only BM1/BM2 via SSH
  status             Show health status of all services
  smoke              End-to-end smoke test on all endpoints
  down               Stop all local services
  logs [target]      Show logs: v100, lb, bm1, bm2, all

Options:
  --env FILE         Use alternate stack.env (default: $STACK_CONFIG)
  --lb-env FILE      Use alternate lb-proxy.env (default: $LB_CONFIG)

Restart order with health waits:
  1. V100 llama.cpp  -> wait /health (up to 5 min)
  2. BM1 llama.cpp   -> wait /health via SSH (up to 5 min)
  3. BM2 llama.cpp   -> wait /health via SSH (up to 5 min)
  4. LB proxy        -> wait port ready (up to 30s)
EOF
}

# Parse global flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      STACK_CONFIG="$2"
      shift 2
      ;;
    --lb-env)
      LB_CONFIG="$2"
      shift 2
      ;;
    *)
      break
      ;;
  esac
done

cmd="${1:-}"
shift || true

case "$cmd" in
  restart)
    do_restart
    ;;
  restart-local)
    do_restart_local
    ;;
  restart-bm)
    restart_bm
    ;;
  status)
    do_status
    ;;
  smoke)
    do_smoke
    ;;
  down)
    do_down
    ;;
  logs)
    do_logs "${1:-all}"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage
    exit 1
    ;;
esac
