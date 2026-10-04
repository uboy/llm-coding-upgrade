#!/usr/bin/env bash
# bench-map-refresh.sh - обновляемые данные карты бенчмарков (docs/task-benchmarks-map.md).
#
# Запускать с asrock или ПК1: OpenRouter режет датацентровые IP (403 от Cloudflare,
# проверено 2026-10-04 - с v100-host API отдаёт 403, с asrock отвечает).
#
# Что делает:
#   1) проверка живости всех ссылок из docs/task-benchmarks-map.md
#      -> benchmarks-map/linkcheck-<дата>.txt
#   2) снапшот моделей+цен OpenRouter -> benchmarks-map/openrouter-<дата>.tsv
#      (колонки: модель, контекст, $/M токенов ввод, $/M вывод; сортировка по цене вывода)
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DOC="$REPO/docs/task-benchmarks-map.md"
OUT="$REPO/benchmarks-map"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
mkdir -p "$OUT"
[ -f "$DOC" ] || { echo "нет $DOC" >&2; exit 1; }

D="$(date +%F)"
echo "== 1) проверка ссылок -> $OUT/linkcheck-$D.txt =="
grep -oE 'https?://[A-Za-z0-9./_#?=%&:+~-]+' "$DOC" | sed 's/[).,]*$//' | sort -u |
while read -r u; do
  code=$(curl -s -o /dev/null -m 15 -w "%{http_code}" -L -A "$UA" "$u")
  echo "$code $u"
done | tee "$OUT/linkcheck-$D.txt"
awk '$1 != 200 {n++} END {print "не-200 ссылок:", n+0}' "$OUT/linkcheck-$D.txt"

echo "== 2) снапшот OpenRouter -> $OUT/openrouter-$D.tsv =="
JSON="$OUT/openrouter-$D.json"
if ! curl -sf -m 60 -A "$UA" "https://openrouter.ai/api/v1/models" -o "$JSON"; then
  rm -f "$JSON"
  echo "OpenRouter недоступен отсюда (403 из датацентров) - запусти скрипт с asrock/ПК1" >&2
  echo "linkcheck готов: $OUT/linkcheck-$D.txt"
  exit 2
fi
python3 -u - "$JSON" "${JSON%.json}.tsv" <<'EOF' || { rm -f "$JSON"; exit 3; }
import json, sys
src, dst = sys.argv[1], sys.argv[2]
ms = json.load(open(src))["data"]
rows = []
for m in ms:
    p = m.get("pricing", {})
    try:
        pin = float(p.get("prompt", 0)) * 1e6
        pout = float(p.get("completion", 0)) * 1e6
    except (TypeError, ValueError):
        pin = pout = -1
    rows.append((pout, m["id"], m.get("context_length", 0), pin, pout))
rows.sort()
with open(dst, "w", encoding="utf-8") as f:
    f.write("model\tcontext\tusd_per_M_prompt\tusd_per_M_completion\n")
    for _, mid, ctx, pin, pout in rows:
        f.write(f"{mid}\t{ctx}\t{pin:.3f}\t{pout:.3f}\n")
free = sum(1 for r in rows if r[4] == 0)
print(f"{len(rows)} моделей, из них бесплатных (completion=0): {free}")
print("топ-5 дешёвых с контекстом >= 32k:")
for _, mid, ctx, pin, pout in [r for r in rows if r[2] >= 32768][:5]:
    print(f"  {mid}  ctx={ctx}  in=${pin:.3f}/M  out=${pout:.3f}/M")
EOF
rm -f "$JSON"
TSV="${JSON%.json}.tsv"
[ -s "$TSV" ] || { echo "TSV пуст - см. сообщение выше" >&2; exit 3; }
echo "готово: $OUT/linkcheck-$D.txt, $TSV"
