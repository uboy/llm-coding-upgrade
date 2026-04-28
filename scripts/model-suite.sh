#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PYTHON_BIN="${PYTHON_BIN:-python3}"

export PYTHONUNBUFFERED=1
exec "$PYTHON_BIN" "$SCRIPT_DIR/model_suite.py" "$@"
