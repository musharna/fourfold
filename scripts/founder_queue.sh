#!/usr/bin/env bash
# founder_queue.sh — P1_founder (prereg/P1_founder.md): wait for the Sol 1003 unit, run founder seed 1001,
# then 1002 and 1003 only if 1001 is VALID (>= 90% error-free agent-ticks). adoption is not looked at here.
set -uo pipefail
cd "$(dirname "$0")/.."
while systemctl --user is-active --quiet fourfold-sol; do sleep 120; done
echo "[$(date -Is)] fourfold-sol done; founder seed 1001"
bash scripts/sol_until_done.sh configs/sol_codex_founder.toml solcx-founder 1001 || { echo "[$(date -Is)] 1001 failed"; exit 4; }
ok=$(.venv/bin/python -c "
import json
rows=[json.loads(l) for l in open('runs/p0-solcx-founder-1001/ticks.jsonl') if l.strip()]
a=[x for r in rows if r.get('type')=='tick' for x in r['agents']]
print(sum(not x['errors'] for x in a)/len(a))")
echo "[$(date -Is)] founder 1001 error-free fraction $ok"
.venv/bin/python -c "import sys; sys.exit(0 if $ok >= 0.9 else 1)" || { echo "[$(date -Is)] 1001 VOID — stopping per prereg"; exit 5; }
bash scripts/sol_until_done.sh configs/sol_codex_founder.toml solcx-founder 1002 1003
