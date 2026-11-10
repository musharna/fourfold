#!/usr/bin/env bash
# codex_queue4.sh — Codex order from 2026-11-10 18:00: founder 1002 1003 (resume) → sham-founder control seed 1001
# (prereg/P1_founder.md addendum). Replaces codex_queue3.sh; T_text stage 3 (verbosity run) is dropped from the queue.
set -uo pipefail
cd "$(dirname "$0")/.."
echo "[$(date -Is)] queue4 start; founder seeds 1002 1003"
bash scripts/sol_until_done.sh configs/sol_codex_founder.toml solcx-founder 1002 1003 >> runs/arm-solcx-founder.out 2>&1 || { echo "[$(date -Is)] founder 1002/1003 failed rc=$?"; exit 6; }
echo "[$(date -Is)] founders done; sham founder seed 1001"
bash scripts/sol_until_done.sh configs/sol_codex_sham.toml solcx-sham 1001 >> runs/arm-solcx-sham.out 2>&1 || { echo "[$(date -Is)] sham failed rc=$?"; exit 7; }
echo "[$(date -Is)] queue4 done"
