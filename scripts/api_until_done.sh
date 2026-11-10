#!/usr/bin/env bash
# api_until_done.sh <config> <arm> <seed>... — OpenRouter arm: run/resume each seed to t50 in cost-capped steps,
# stopping if the balance drops below $1.50 (a 402 also stops sim.py), then eval.py.
set -uo pipefail
cd "$(dirname "$0")/.."
cfg=$1; arm=$2; shift 2
export OPENROUTER_API_KEY=$(grep -o "sk-or-[A-Za-z0-9_-]*" "$HOME/.config/openrouter/credentials" | head -1)
bal() { curl -s -m 20 https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPENROUTER_API_KEY" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(round(d['total_credits']-d['total_usage'],2))"; }
for seed in "$@"; do
  rid="p0-${arm}-${seed}"; log="runs/${rid}.log"
  for step in $(seq 1 8); do
    n=$( [ -f runs/$rid/ticks.jsonl ] && grep -c '"type": "tick"' runs/$rid/ticks.jsonl || echo 0 )
    [ "$n" -ge 50 ] && break
    b=$(bal); echo "[$(date -Is)] $rid at t$n, balance \$$b" | tee -a "$log"
    python3 -c "import sys; sys.exit(0 if $b >= 1.5 else 1)" || { echo "[$(date -Is)] balance low — stopping" | tee -a "$log"; exit 3; }
    if [ -d runs/$rid ]; then .venv/bin/python sim.py --resume "$rid" --ticks 50 >>"$log" 2>&1
    else .venv/bin/python sim.py --config "$cfg" --world-seed "$seed" --run-id "$rid" >>"$log" 2>&1; fi
    tail -1 "$log" | grep -q "402 Payment Required" && { echo "[$(date -Is)] 402 — stopping" | tee -a "$log"; exit 3; }
  done
  n=$(grep -c '"type": "tick"' runs/$rid/ticks.jsonl)
  [ "$n" -ge 50 ] || { echo "[$(date -Is)] $rid stuck at t$n" | tee -a "$log"; exit 4; }
  [ -f runs/$rid/eval-t50.json ] || .venv/bin/python eval.py "$rid" >>"$log" 2>&1
  echo "[$(date -Is)] done $rid" | tee -a "$log"
done
