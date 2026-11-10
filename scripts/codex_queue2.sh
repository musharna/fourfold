#!/usr/bin/env bash
# codex_queue2.sh — Codex order after Sol 1003 (set 2026-11-10): founder seed 1001, then T_text stage 3
# (verbosity=medium, seed 1001), then founder 1002 1003 only if founder 1001 is VALID (>= 90% error-free; P1_founder prereg).
set -uo pipefail
cd "$(dirname "$0")/.."
while systemctl --user is-active --quiet fourfold-sol; do sleep 120; done
echo "[$(date -Is)] fourfold-sol done; founder seed 1001"
bash scripts/sol_until_done.sh configs/sol_codex_founder.toml solcx-founder 1001 >> runs/arm-solcx-founder.out 2>&1; f=$?
echo "[$(date -Is)] founder 1001 rc=$f; verbosity=medium seed 1001"
bash scripts/sol_until_done.sh configs/sol_codex_verbmed.toml solcx-verbmed 1001 >> runs/arm-solcx-verbmed.out 2>&1 || echo "[$(date -Is)] verbmed failed rc=$?"
[ "$f" -eq 0 ] || { echo "[$(date -Is)] founder 1001 failed — not running 1002/1003"; exit 4; }
ok=$(.venv/bin/python -c "
import json
rows=[json.loads(l) for l in open('runs/p0-solcx-founder-1001/ticks.jsonl') if l.strip()]
a=[x for r in rows if r.get('type')=='tick' for x in r['agents']]
print(sum(not x['errors'] for x in a)/len(a))")
echo "[$(date -Is)] founder 1001 error-free fraction $ok"
.venv/bin/python -c "import sys; sys.exit(0 if $ok >= 0.9 else 1)" || { echo "[$(date -Is)] founder 1001 VOID — stopping per prereg"; exit 5; }
bash scripts/sol_until_done.sh configs/sol_codex_founder.toml solcx-founder 1002 1003 >> runs/arm-solcx-founder.out 2>&1
echo "[$(date -Is)] queue done"
