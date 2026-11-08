#!/usr/bin/env bash
# codex_jail.sh <workdir> <codex args...> — run the experiment's private codex inside a bubblewrap jail.
# visible: /usr, /etc (ro), the codex install (ro), ~/.codex/auth.json (rw, token refresh), <workdir> (rw).
# invisible: all of /home (incl. runs/, ~/.codex AGENTS.md/config/history), /tmp. network shared.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
work=$1; shift
exec bwrap --ro-bind /usr /usr --symlink usr/lib /lib --symlink usr/lib64 /lib64 \
  --symlink usr/bin /bin --symlink usr/sbin /sbin --ro-bind /etc /etc \
  --proc /proc --dev /dev --tmpfs /tmp --tmpfs /home --dir /home/u \
  --ro-bind "$here/.codex-cli" /opt/codex \
  --tmpfs /codexhome --bind "$HOME/.codex/auth.json" /codexhome/auth.json \
  --bind "$work" /work --chdir /work \
  --setenv HOME /home/u --setenv CODEX_HOME /codexhome \
  --unshare-pid --die-with-parent --share-net \
  /opt/codex/node_modules/.bin/codex "$@"
