#!/usr/bin/env bash
# needle-sweep-ornith15.sh [url] [targets...]
# Обёртка над needle-test.py (фаза 8) для long-ctx свипа ornith15.
# Прогоняет pos/neg на каждом target; 6/6 = все находки и ни одной галлюцинации.
# Результаты эксперимента 2026-08-24: 6/6 на 16k/24k/32k у Q4_K_M, Q6_K, 9B.
# Использование: bash needle-sweep-ornith15.sh http://localhost:8081 16384 24576 32768
set -uo pipefail
URL="${1:-http://localhost:8081}"; shift || true
TARGETS=("$@"); [ ${#TARGETS[@]} -eq 0 ] && TARGETS=(16384 24576 32768)
B=/data/home/<user>/proj/bigmodel-bench-v100
cd "$B"
for target in "${TARGETS[@]}"; do
  for mode in pos neg; do
    echo "=== NEEDLE mode=$mode target=$target ==="
    timeout 900 python3 ./needle-test.py "$URL" "$mode" "$target" 2>&1 | tail -4
  done
done
echo "=== SWEEP_DONE ==="
