#!/usr/bin/env bash
# t_text_until_done.sh <arms> — run the T_text replay battery (prereg/T_text.md) for <arms> (comma list),
# retrying every 30 min across Plus usage windows (replay.py exit 3), then print the summary.
# afterwards: the Sol 1002 F0 floors, which also need Sol quota; a floor that hit the limit is deleted, not kept.
set -uo pipefail
cd "$(dirname "$0")/.."
arms=$1
for attempt in $(seq 1 24); do
  echo "[$(date -Is)] replay attempt $attempt arms=$arms"
  .venv/bin/python analysis/replay.py run --arms "$arms" --states S1,S2,S3 --n 20
  rc=$?
  [ $rc -eq 0 ] && break
  [ $rc -ne 3 ] && { echo "[$(date -Is)] replay failed rc=$rc — stopping"; exit 4; }
  sleep 1800
done
.venv/bin/python analysis/replay.py summary --n 20
for r in cued nocue; do
  run=p0-solcx-$r-1002
  [ -f runs/$run/eval-t0.json ] && continue
  .venv/bin/python eval.py $run --tick 0 > runs/$run.F0.txt 2>&1
  if grep -q "usage limit" runs/$run.F0.txt; then
    echo "[$(date -Is)] $run F0 hit the usage limit — deleted, rerun later"
    rm -f runs/$run/eval-t0.json runs/$run.F0.txt
  else
    echo "[$(date -Is)] $run F0: $(grep ' mean' runs/$run.F0.txt)"
  fi
done
