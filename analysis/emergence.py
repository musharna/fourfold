"""emergence: when does readable text appear in port traffic, and when have all agents used it.

what it does   decodes every output port of a run (hex -> bytes) and flags a port as TEXT when
               its bytes hold a maximal run of printable ascii (0x20-0x7e) of length >= L that
               contains >= 5 letters and >= 4 distinct characters (so "AAAA..." probes don't count).
when to use    any fourfold run in hex port mode; the P0 replication readout R2.
output         t_first (first tick any agent wrote a text port), t_all (first tick by which every
               agent had written one), adopted (agents that ever did), per-tick counts.
               t_first/t_all = None means no text appeared. A non-hex or pixel run raises.
must pass      analysis/gates_p0.py: null false-event rate on random ports < 0.05 per 3x3x50 run at
               the chosen L, and the sol-50 example matches erin's README timeline (t6 / t14).
"""

from __future__ import annotations

import json
import string
import sys
from pathlib import Path

PRINTABLE = set(range(0x20, 0x7F))
LETTERS = set(string.ascii_letters.encode())
MIN_LETTERS, MIN_DISTINCT = 5, 4


def longest_text_run(b: bytes) -> bytes:
    best, cur = b"", bytearray()
    for x in b + b"\x00":
        if x in PRINTABLE:
            cur.append(x)
            continue
        if len(cur) > len(best):
            best = bytes(cur)
        cur = bytearray()
    return best


def is_text(hexval: str, L: int) -> bool:
    run = longest_text_run(bytes.fromhex(hexval))
    return (
        len(run) >= L
        and sum(c in LETTERS for c in run) >= MIN_LETTERS
        and len(set(run)) >= MIN_DISTINCT
    )


def load(path: Path) -> tuple[dict, list[dict]]:
    rows = [
        json.loads(l)
        for l in path.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    meta = next(r for r in rows if r.get("type") == "meta")
    if meta["config"].get("port_mode", "hex") != "hex":
        raise ValueError(
            f"{path}: emergence needs hex ports, got {meta['config'].get('port_mode')}"
        )
    return meta, [r for r in rows if r.get("type") == "tick"]


MIN_DISTINCT_VALUES = (
    2  # an agent "uses text" once it wrote >= 2 different text port values
)


def emergence(path: Path, L: int) -> dict:
    """an agent qualifies after >= MIN_DISTINCT_VALUES distinct text values (noise does not
    recur; held outputs count once). timing is taken from the qualifying agent's FIRST text
    tick: t_first = earliest such tick over qualifying agents, t_all = latest (None unless
    every agent qualifies)."""
    meta, ticks = load(path)
    n = len(meta["agents"])
    first_tick, values, per_tick = {}, {}, []
    for rec in ticks:
        k = 0
        for a in rec["agents"]:
            txt = [v for v in a["outputs"] if is_text(v, L)]
            if txt:
                k += 1
                first_tick.setdefault(a["agent"], rec["t"])
                values.setdefault(a["agent"], set()).update(txt)
        per_tick.append(k)
    qual = {
        g: first_tick[g] for g, vs in values.items() if len(vs) >= MIN_DISTINCT_VALUES
    }
    return {
        "run_id": meta["run_id"],
        "ticks": len(ticks),
        "n_agents": n,
        "L": L,
        "t_first": min(qual.values()) if qual else None,
        "t_all": max(qual.values()) if len(qual) == n else None,
        "adopted": len(qual),
        "per_tick": per_tick,
    }


if __name__ == "__main__":
    L = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    r = emergence(Path(sys.argv[1]), L)
    print(json.dumps({k: v for k, v in r.items() if k != "per_tick"}))
