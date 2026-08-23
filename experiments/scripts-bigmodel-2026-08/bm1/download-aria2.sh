#!/usr/bin/env bash
REPO="$1"; DEST="$2"; PAT="${3:-.}"
mkdir -p "$DEST"; cd "$DEST" || exit 1
curl -s "https://huggingface.co/api/models/$REPO?blobs=true" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for f in d.get(\"siblings\",[]):
    p=f.get(\"rfilename\",\"\"); s=f.get(\"size\")
    if s and p.endswith((\".safetensors\",\".gguf\",\".json\",\".txt\",\".jinja\",\".model\")):
        print(p, s)
" > files.txt
while read -r path size; do
  case "$path" in original/*|metal/*|bootstrap/*) continue ;; esac
  echo "$path" | grep -iqE "$PAT" || continue
  mkdir -p "$(dirname "$path")"
  sz=$(stat -c%s "$path" 2>/dev/null || echo 0)
  if [ "$sz" = "$size" ]; then echo "SKIP $path"; continue; fi
  aria2c -x 8 -s 8 -k 4M --file-allocation=none --console-log-level=warn \
    --summary-interval=0 -c -o "$path" "https://huggingface.co/$REPO/resolve/main/$path"
  sz2=$(stat -c%s "$path" 2>/dev/null || echo 0)
  if [ "$sz2" = "$size" ]; then echo "OK $path $sz2"; else echo "MISMATCH $path got=$sz2 want=$size"; fi
done < files.txt
echo "DONE_ALL $(date -Is)"
