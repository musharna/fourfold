#!/usr/bin/env bash
# codex_queue3.sh — Codex order from 2026-11-10 13:40, after codex cued 1003 wrote text 9/9 (stage 3's premise,
# "codex never writes text", is false): founder 1001 (resume) → F0 floors for the 1003 runs → founder 1002 1003
# (only if founder 1001 is VALID, P1_founder prereg) → T_text stage 3 (verbosity=medium) last.
set -uo pipefail
cd "$(dirname "$0")/.."
echo "[$(date -Is)] queue3 start; founder seed 1001"
bash scripts/sol_until_done.sh configs/sol_codex_founder.toml solcx-founder 1001 >> runs/arm-solcx-founder.out 2>&1; f=$?
echo "[$(date -Is)] founder 1001 rc=$f"
[ "$f" -eq 0 ] || { echo "[$(date -Is)] founder 1001 failed — stopping"; exit 4; }
for run in p0-solcx-cued-1003 p0-solcx-nocue-1003; do
  [ -f runs/$run/eval-t0.json ] && continue
  .venv/bin/python eval.py $run --tick 0 > runs/$run.F0.txt 2>&1
  if grep -q 'usage limit' runs/$run.F0.txt; then
    echo "[$(date -Is)] F0 $run hit the usage limit — discarded, not retried here"; rm -f runs/$run/eval-t0.json runs/$run.F0.txt
  else echo "[$(date -Is)] F0 $run done"; fi
done
ok=$(.venv/bin/python -c "
import json
rows=[json.loads(l) for l in open('runs/p0-solcx-founder-1001/ticks.jsonl') if l.strip()]
a=[x for r in rows if r.get('type')=='tick' for x in r['agents']]
print(sum(not x['errors'] for x in a)/len(a))")
echo "[$(date -Is)] founder 1001 error-free fraction $ok"
.venv/bin/python -c "import sys; sys.exit(0 if $ok >= 0.9 else 1)" || { echo "[$(date -Is)] founder 1001 VOID — stopping per prereg"; exit 5; }
bash scripts/sol_until_done.sh configs/sol_codex_founder.toml solcx-founder 1002 1003 >> runs/arm-solcx-founder.out 2>&1 || { echo "[$(date -Is)] founder 1002/1003 failed rc=$?"; exit 6; }
echo "[$(date -Is)] founders done; verbosity=medium seed 1001"
bash scripts/sol_until_done.sh configs/sol_codex_verbmed.toml solcx-verbmed 1001 >> runs/arm-solcx-verbmed.out 2>&1 || echo "[$(date -Is)] verbmed failed rc=$?"
echo "[$(date -Is)] queue3 done"
