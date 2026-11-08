#!/usr/bin/env bash
# run_arm.sh <config.toml> <arm-label> <seed>...  — one arm, seeds in sequence, eval after each.
# a run that stops early (usage limit / error streak / cost cap) aborts the arm loudly.
set -euo pipefail
cd "$(dirname "$0")/.."
cfg=$1; arm=$2; shift 2
for seed in "$@"; do
  rid="p0-${arm}-${seed}"
  log="runs/${rid}.log"
  if [ -f "runs/${rid}/eval-t50.json" ]; then echo "skip ${rid} (done)"; continue; fi
  echo "[$(date -Is)] start ${rid}" | tee -a "$log"
  if [ -d "runs/${rid}" ]; then
    .venv/bin/python sim.py --resume "${rid}" --ticks 50 >>"$log" 2>&1
  else
    .venv/bin/python sim.py --config "$cfg" --world-seed "$seed" --run-id "$rid" >>"$log" 2>&1
  fi
  last=$(tail -1 "$log")
  case "$last" in tick\ \ \ 50*) ;; *) echo "[$(date -Is)] ${rid} did not reach tick 50: ${last}" | tee -a "$log"; exit 3;; esac
  .venv/bin/python eval.py "${rid}" >>"$log" 2>&1
  echo "[$(date -Is)] done ${rid}" | tee -a "$log"
done
