"""p0_readout: one row per P0 run with every prereg readout.

what it does   for each runs/p0-*/ dir: ticks reached, error-free agent-ticks (per-agent `errors` list),
               safeguard refusals, other errors, VOID flag (prereg: < 90% error-free or < 50 ticks),
               eval-t50 mean over all 9 agents and over answered agents, emergence (L=10).
               F0 floor rows come from eval-t0.json where present.
when to use    P0 verdicts; rerun after any new run lands.
output         TSV on stdout (also written to analysis/p0_readout.tsv).
must pass      a run known to contain errors must show < 100% error-free (positive control:
               p0-sonnet-nocue-1003 had 172 refusals) — checked below, the script exits 2 if not.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
from emergence import emergence  # noqa: E402

COLS = [
    "run",
    "ticks",
    "agent_ticks",
    "error_free",
    "frac_ok",
    "refused",
    "other_err",
    "void",
    "eval_mean",
    "eval_answered_mean",
    "n_answered",
    "f0_mean",
    "adopted",
    "t_first",
    "t_all",
]


def eval_means(p: Path):
    if not p.exists():
        return None, None, 0
    res = json.loads(p.read_text(encoding="utf-8"))["results"]
    allm = sum(r["total"] for r in res) / len(res)
    ans = [r["total"] for r in res if not r.get("error")]
    return round(allm, 3), (round(sum(ans) / len(ans), 3) if ans else None), len(ans)


def row(d: Path) -> dict:
    n = bad = ref = 0
    ticks = 0
    for line in (d / "ticks.jsonl").read_text(encoding="utf-8").splitlines():
        x = json.loads(line)
        if x.get("type") != "tick":
            continue
        ticks = max(ticks, x["t"])
        for a in x["agents"]:
            n += 1
            es = a.get("errors") or []
            bad += bool(es)
            ref += any("safeguards" in str(e) for e in es)
    em = emergence(d / "ticks.jsonl", 10)
    m, am, na = eval_means(d / "eval-t50.json")
    f0, _, _ = eval_means(d / "eval-t0.json")
    frac = (n - bad) / n if n else 0.0
    return {
        "run": d.name,
        "ticks": ticks,
        "agent_ticks": n,
        "error_free": n - bad,
        "frac_ok": round(frac, 3),
        "refused": ref,
        "other_err": bad - ref,
        "void": frac < 0.90 or ticks < 50,
        "eval_mean": m,
        "eval_answered_mean": am,
        "n_answered": na,
        "f0_mean": f0,
        "adopted": em["adopted"],
        "t_first": em["t_first"],
        "t_all": em["t_all"],
    }


def main():
    rows = [
        row(d)
        for d in sorted((ROOT / "runs").glob("p0-*"))
        if (d / "ticks.jsonl").exists()
    ]
    ctl = [r for r in rows if r["run"] == "p0-sonnet-nocue-1003"]
    if ctl and ctl[0]["refused"] == 0:
        sys.exit("positive control failed: p0-sonnet-nocue-1003 shows 0 refusals")
    out = ["\t".join(COLS)] + ["\t".join(str(r[c]) for c in COLS) for r in rows]
    (ROOT / "analysis" / "p0_readout.tsv").write_text(
        "\n".join(out) + "\n", encoding="utf-8"
    )
    print("\n".join(out))


if __name__ == "__main__":
    main()
