#!/usr/bin/env bash
# ft-launch.sh <model_path> <logfile> [extra...]
MODEL=$1; LOG=$2; shift 2
cd ~/proj/bigmodel-bench
setsid nohup ./ft-venv/bin/ft serve --model "$MODEL" "$@" > "$LOG" 2>&1 < /dev/null &
echo launched_pid=$!
