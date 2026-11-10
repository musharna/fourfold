"""founder_readout: P1_founder readouts (prereg/P1_founder.md) — does a planted founder make Sol cells adopt English.

what it does   per run, over every cell except the founder (cell 6):
                 R1 relay      cells with any output passing is_text(L=10)
                 R2 adoption   cells that compose English: a text output that is not a verbatim copy of any
                               input value the cell has seen up to that tick
                 R3 persist    composed English from non-founder cells in t30-50
                 R4 task       eval-t50 mean over the same cells, founder run vs paired p0-solcx-cued run
when to use    P1_founder runs (runs/p0-solcx-founder-<seed>).
output         one line per run on stdout; analysis/founder_readout.tsv.
must pass      `control`: erin's sol-50 (cell 6 excluded) R2 >= 7/8; an echo-agent dry run of
               configs/sol_codex_founder.toml (echo cells only relay) R1 > 0 and R2 = 0. exits 2 otherwise.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
from emergence import is_text  # noqa: E402

FOUNDER = 6


def load(run_dir: Path):
    rows = [
        json.loads(l)
        for l in (run_dir / "ticks.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    return rows[0], [r for r in rows[1:] if r.get("type") == "tick"]


def readout(run_dir: Path) -> dict:
    meta, ticks = load(run_dir)
    cells = [i for i in range(len(meta["agents"])) if i != FOUNDER]
    relay, comp, late = set(), set(), set()
    seen = {i: set() for i in cells}
    first_comp = None
    for rec in ticks:
        for i in cells:
            a = rec["agents"][i]
            seen[i].update(v.lower() for v in a["inputs"])
            for v in a["outputs"]:
                if is_text(v.lower(), 10):
                    relay.add(i)
                    if v.lower() not in seen[i]:
                        comp.add(i)
                        first_comp = first_comp or rec["t"]
                        if rec["t"] >= 30:
                            late.add(i)
    return {
        "run": run_dir.name,
        "ticks": len(ticks),
        "R1_relay": len(relay),
        "R2_adopt": len(comp),
        "R3_late_cells": len(late),
        "first_composed_t": first_comp,
        "n_cells": len(cells),
    }


def eval_mean(run_dir: Path) -> float | None:
    p = run_dir / "eval-t50.json"
    if not p.exists():
        return None
    res = [r for r in json.loads(p.read_text())["results"] if r["agent"] - 1 != FOUNDER]
    return round(sum(r["total"] for r in res) / len(res), 3) if res else None


def control():
    fail = []
    e = readout(ROOT / "examples" / "sol-50")
    if e["R2_adopt"] < 7:
        fail.append(f"sol-50 R2 {e['R2_adopt']}/8 < 7")
    rid = "founder-control-echo"
    shutil.rmtree(ROOT / "runs" / rid, ignore_errors=True)
    p = subprocess.run(
        [
            sys.executable,
            "sim.py",
            "--config",
            "configs/sol_codex_founder.toml",
            "--agent",
            "echo",
            "--world-seed",
            "1001",
            "--run-id",
            rid,
            "--ticks",
            "30",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if p.returncode:
        fail.append(f"echo dry run failed: {p.stderr[-300:]}")
    else:
        c = readout(ROOT / "runs" / rid)
        if not (c["R1_relay"] > 0 and c["R2_adopt"] == 0):
            fail.append(
                f"echo dry run R1 {c['R1_relay']} R2 {c['R2_adopt']} (want R1>0, R2=0)"
            )
        shutil.rmtree(ROOT / "runs" / rid)
    if fail:
        print("CONTROL FAILED:\n  " + "\n  ".join(fail))
        sys.exit(2)
    print(
        f"control PASS: sol-50 R2 {e['R2_adopt']}/8 (first composed t{e['first_composed_t']}); echo dry run relays without composing"
    )


def main():
    control()
    rows = []
    for d in sorted((ROOT / "runs").glob("p0-solcx-founder-*")):
        if not (d / "ticks.jsonl").exists():
            continue
        r = readout(d)
        seed = d.name.rsplit("-", 1)[1]
        r["eval_founder"] = eval_mean(d)
        r["eval_paired_nofounder"] = eval_mean(ROOT / "runs" / f"p0-solcx-cued-{seed}")
        rows.append(r)
        print(r)
    if rows:
        cols = list(rows[0])
        (ROOT / "analysis" / "founder_readout.tsv").write_text(
            "\n".join(
                ["\t".join(cols)] + ["\t".join(str(r[c]) for c in cols) for r in rows]
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
