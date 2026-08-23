#!/usr/bin/env bash
B=/data/home/<user>/proj/bigmodel-bench-v100
cd $B/models/deepseek-q4xl || exit 1
for round in $(seq 1 200); do
  alldone=1
  while read -r path size; do
    sz=$(stat -c%s "$path" 2>/dev/null || echo 0)
    [ "$sz" = "$size" ] && continue
    alldone=0
    aria2c -x 16 -s 16 -k 4M --file-allocation=none --console-log-level=warn --summary-interval=0 -c -o "$path" "https://huggingface.co/unsloth/DeepSeek-V4-Flash-0731-GGUF/resolve/main/UD-Q4_K_XL/$path"
  done < files.txt
  [ "$alldone" = "1" ] && { touch $B/DONE-deepseek; echo "[$(date -Is)] deepseek complete" >> $B/dl-deepseek.log; exit 0; }
  echo "[$(date -Is)] retry round $round" >> $B/dl-deepseek.log
  sleep 30
done
