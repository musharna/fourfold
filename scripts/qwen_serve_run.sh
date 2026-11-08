#!/usr/bin/env bash
# Run a fourfold sim against a local Qwen vLLM server (agent-zoo's serve/with_vllm.sh), desktop host.
#   scripts/qwen_serve_run.sh <sim.py args ...>     (config is generated: configs/qwen.toml with the live port)
# Why the port loop: on the desktop WSL host a /health connect to a LISTENing vLLM port has hung in
# SYN-SENT inside jobd jobs (jobd 8811; agent-zoo 5586/5623) while the same port answers from ssh.
# Cause unnamed; the documented workaround is a fresh port. Each attempt is logged; exits other than the
# health-hang codes (7, 28) are real failures and stop the loop.
set -euo pipefail
LAB=$(cd "$(dirname "$0")/.." && pwd)
ZOO=${ZOO_DIR:-$HOME/agent-zoo}
echo "== in-job loopback probe (netns $(readlink /proc/self/ns/net))"
bash "$ZOO/scripts/loopback_probe.sh" || true
rc=1
for port in ${QWEN_PORTS:-8743 8757 8769}; do
  cfg=$LAB/runs/qwen-port$port.toml
  mkdir -p "$LAB/runs"
  sed "s#http://127.0.0.1:8731/v1#http://127.0.0.1:$port/v1#" "$LAB/${QWEN_CFG:-configs/qwen.toml}" > "$cfg"
  grep -q "127.0.0.1:$port/v1" "$cfg" || { echo "config rewrite failed for port $port" >&2; exit 3; }
  echo "== attempt port $port"
  set +e
  ( cd "$ZOO" && ZOO_PORT=$port ZOO_GPU_UTIL=${ZOO_GPU_UTIL:-0.70} serve/with_vllm.sh Qwen/Qwen3.5-9B \
      --language-model-only --reasoning-parser qwen3 --max-num-seqs 16 -- \
      bash -c "cd '$LAB' && .venv/bin/python sim.py --config '$cfg' $*" )
  rc=$?
  set -e
  echo "== port $port exit $rc"
  [[ $rc == 7 || $rc == 28 ]] || exit $rc
done
echo "all ports hit the health hang" >&2
exit $rc
