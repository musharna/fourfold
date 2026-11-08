#!/usr/bin/env bash
# replace_until_valid.sh <config> <arm> <n_needed> <seed>...  — prereg deviation 6 replacement rule:
# run replacement seeds in order, stop once n_needed of them are valid (analysis/p0_readout.py row()).
set -euo pipefail
cd "$(dirname "$0")/.."
cfg=$1; arm=$2; need=$3; shift 3
got=0
for seed in "$@"; do
  (( got >= need )) && { echo "have $got valid replacement(s); skip $seed onward"; break; }
  scripts/run_arm.sh "$cfg" "$arm" "$seed"
  v=$(.venv/bin/python -I -c "import sys; sys.path.insert(0,'analysis'); from p0_readout import row; from pathlib import Path; r=row(Path('runs/p0-$arm-$seed')); print('VOID' if r['void'] else 'VALID', r['frac_ok'])")
  echo "[$(date -Is)] p0-$arm-$seed $v"
  [[ $v == VALID* ]] && got=$((got + 1))
done
echo "[$(date -Is)] $arm replacements: $got/$need valid"
