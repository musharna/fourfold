#!/usr/bin/env bash
# sol_until_done.sh <config> <arm> <seed>... — run_arm.sh across ChatGPT Plus usage windows: when a run stops on the
# usage limit, sleep until the reset time codex reports (+5 min) and resume. Any other stop exits loudly.
set -uo pipefail
cd "$(dirname "$0")/.."
cfg=$1; arm=$2; shift 2
for seed in "$@"; do
  rid="p0-${arm}-${seed}"
  for attempt in $(seq 1 12); do
    if bash scripts/run_arm.sh "$cfg" "$arm" "$seed"; then break; fi
    last=$(grep -o 'try again at [^"]*' "runs/${rid}.log" | tail -1)
    if ! tail -3 "runs/${rid}.log" | grep -q 'usage limit'; then
      echo "[$(date -Is)] ${rid} stopped for a reason other than the usage limit — aborting"; tail -5 "runs/${rid}.log"; exit 4
    fi
    when=$(echo "$last" | sed -E 's/try again at (.*)\.?$/\1/; s/\.$//; s/([0-9])(st|nd|rd|th)/\1/')
    t=$(date -d "$when" +%s) || { echo "cannot parse reset time: '$last'"; exit 5; }
    s=$(( t - $(date +%s) + 300 )); (( s < 300 )) && s=300
    echo "[$(date -Is)] ${rid} hit usage limit; sleeping ${s}s until $(date -d @$((t+300)))"
    sleep "$s"
  done
done
echo "[$(date -Is)] ${arm} seeds $* done"
