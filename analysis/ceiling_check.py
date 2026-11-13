"""scripted ceiling (ceiling.py): controls and the preregistered checks. prints counts; exits 1 on
any failure. every verdict line is printed by the comparison from measured counts.

  python analysis/ceiling_check.py            controls + 3x3 at 128 bits + other grid sizes (about 3 min)
  python analysis/ceiling_check.py --widths   also port widths 4 to 128 bits (about 10 min more)
  python analysis/ceiling_check.py --dev      13 worlds instead of 103, and 3 instead of 20 per grid size

criteria: prereg/ceiling.md (C1-C6) and prereg/ceiling_widths.md (D1-D3, D5). results: docs/ceiling_results.md.
the full run rewrites analysis/ceiling_by_tick.tsv and ceiling_sizes.tsv (and ceiling_widths.tsv with
--widths). runs are written to a temporary directory and deleted.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import inspect
import re
import signal
import statistics
import sys
import tempfile
import time
from pathlib import Path

signal.signal(
    signal.SIGALRM,
    lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)),
)
signal.alarm(3600)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ceiling  # noqa: E402
import eval as ev  # noqa: E402
import sim  # noqa: E402

EVAL_TPL = (ROOT / "prompts" / "eval.txt").read_text(encoding="utf-8")
TMAX = 12
SIZES = [(2, 2), (2, 3), (3, 4), (4, 4), (5, 5)]
WIDTHS = [4, 8, 16, 32, 64, 128]
PARTS = [
    "count_score",
    "arrangement_score",
    "position_score",
    "map_score",
    "wiring_score",
]
FAILS: list = []


def verdict(key: str, ok: bool, text: str):
    print(f"{'PASS' if ok else 'FAIL'}  {key}: {text}", flush=True)
    if not ok:
        FAILS.append(key)


# ---------------------------------------------------------------- running and quizzing


def run_world(
    rows,
    cols,
    seed,
    ticks,
    run_id,
    perturb=None,
    port_bits=128,
    store=False,
    plant=None,
):
    """-> (meta, tick records), through sim.new_run and sim.step as `python sim.py` does."""
    cfg = sim.deep_merge(
        sim.DEFAULTS,
        {"agent": "ceiling", "world_seed": seed, "rows": rows, "cols": cols, "ticks": ticks,
         "perturb": perturb or [], "port_bits": port_bits, "store_prompts": store},
    )  # fmt: skip
    sim.set_width(cfg)
    sim.check_perturb(cfg)
    _, meta = sim.new_run(cfg, run_id)
    if plant:  # a control may edit the world (the ids) before anything runs
        plant(meta)
    states = sim.restore_states(meta, [])
    agents = sim.make_agents(cfg)

    async def go():
        return [await sim.step(t, meta, states, agents) for t in range(1, ticks + 1)]

    return meta, asyncio.run(go())


def wrong_slots(score: dict) -> int:
    """wiring slots where the cell named a neighbour or called the port dead, and was not fully right."""
    return sum(1 for s in score["slots"] if s["claim"] != "none" and s["score"] < 1.0)


def quiz(meta: dict, ticks: list, T: int) -> list:
    """eval.py's quiz after tick T -> one scored dict per cell."""
    _, results = asyncio.run(ev.ask_all(meta, ticks[:T], EVAL_TPL))
    out = []
    for tn, rep in results:
        s = ev.score_agent(meta, tn.state.id, rep.raw)
        s["error"], s["wrong"] = rep.error, s["map_wrong"] + wrong_slots(s)
        out.append(s)
    if len(out) != meta["rows"] * meta["cols"]:
        sys.exit(
            f"denominator short: {len(out)} of {meta['rows'] * meta['cols']} cells quizzed"
        )
    return out


def first_perfect(perfect_by_tick: dict, n: int):
    """smallest T from which all n cells stay perfect to the end of the run, or None."""
    first = None
    for T in sorted(perfect_by_tick, reverse=True):
        if perfect_by_tick[T] != n:
            break
        first = T
    return first


def write_tsv(name: str, rows: list):
    with open(ROOT / "analysis" / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- controls that do not need the agent to be right


def truth_answer(meta: dict, k: int, swap: bool = False, lie: bool = False) -> str:
    """a quiz answer written straight from the world's true wiring, not from any agent."""
    a, rows, cols = meta["agents"][k], meta["rows"], meta["cols"]
    grid = [
        [meta["agents"][r * cols + c]["seed"] for c in range(cols)] for r in range(rows)
    ]
    if swap:  # two cells side by side: never a rotation or mirror image (opposite corners are, in 2x2)
        grid[0][0], grid[0][1] = grid[0][1], grid[0][0]
    live = sum(l is not None for l in a["links"])
    out = [
        f"<count>{rows * cols}</count>",
        f"<arrangement>a {rows}x{cols} grid\n"
        + "\n".join(" ".join(row) for row in grid)
        + "</arrangement>",
        f"<position>{ {2: 'corner', 3: 'edge', 4: 'center'}[live] }</position>",
    ]
    for kind, other in (("p", "q"), ("q", "p")):
        for i, l in enumerate(a["links"]):
            says = (
                "nothing"
                if l is None
                else f"{meta['agents'][l['agent']]['seed']} {other}{l['port']}"
            )
            if lie and kind == "p" and i == 0:
                says = (
                    "nothing"
                    if l is not None
                    else f"{meta['agents'][(k + 1) % (rows * cols)]['seed']} {other}0"
                )
            out.append(f"<{kind}{i}>{says}</{kind}{i}>")
    return "\n".join(out)


def controls():
    worlds = [
        (3, 3, 1001),
        (3, 3, 1002),
        (3, 3, 1003),
        (2, 2, 1),
        (2, 3, 1),
        (3, 4, 1),
        (4, 4, 1),
        (5, 5, 1),
    ]
    n = perfect = swapped = caught = 0
    for rows, cols, seed in worlds:
        meta, _ = run_world(rows, cols, seed, 1, f"ctl-{rows}x{cols}-{seed}")
        for k in range(rows * cols):
            n += 1
            perfect += ev.score_agent(meta, k, truth_answer(meta, k))["total"] == 1.0
            swapped += (
                ev.score_agent(meta, k, truth_answer(meta, k, swap=True))["total"]
                == 1.0
            )
            lied = ev.score_agent(meta, k, truth_answer(meta, k, lie=True))
            caught += wrong_slots(lied) == 1 and lied["total"] < 1.0
    verdict(
        "control scorer reaches 1.0 on a true answer",
        perfect == n,
        f"{perfect}/{n} cells at 1.0",
    )
    verdict(
        "control scorer drops a map with two ids swapped",
        swapped == 0,
        f"{swapped}/{n} still at 1.0",
    )
    verdict(
        "control wrong-claim counter fires on one false link",
        caught == n,
        f"{caught}/{n} caught",
    )

    params = list(inspect.signature(ceiling.respond).parameters)
    verdict(
        "control agent takes only the two prompt strings",
        params == ["system", "prompt"],
        f"parameters {params}",
    )
    meta, ticks = run_world(3, 3, 1001, 8, "ctl-replay", store=True)
    same = total = 0
    for rec in ticks:
        for a, w in zip(rec["agents"], meta["agents"]):
            total += 1
            same += (
                ceiling.respond(sim.system_prompt(meta, w["seed"]), a["prompt"])
                == a["raw"]
            )
    verdict(
        "control a fresh call on the logged strings gives the logged reply",
        same == total == 72,
        f"{same}/{total} replies",
    )


# ---------------------------------------------------------------- prereg/ceiling.md


def sweep(label, rows, cols, seeds, ticks, perturb=None):
    """-> one row per cell per quiz tick, and (harness errors, longest protocol in words)."""
    out, errs, words = [], 0, 0
    for seed in seeds:
        meta, recs = run_world(
            rows, cols, seed, ticks, f"{label}-{rows}x{cols}-{seed}", perturb
        )
        errs += sum(len(a["errors"]) for r in recs for a in r["agents"])
        words = max(
            [words]
            + [
                len(re.findall(r"\S+", a["protocol"]))
                for r in recs
                for a in r["agents"]
            ]
        )
        for T in range(ticks + 1):
            for s in quiz(meta, recs, T):
                row = {
                    "set": label,
                    "rows": rows,
                    "cols": cols,
                    "seed": seed,
                    "T": T,
                    "role": s["true_role"],
                }
                row.update({k: s[k] for k in ["total"] + PARTS + ["wrong"]})
                row["error"] = bool(s["error"])
                out.append(row)
    return out, errs, words


def part1(seeds33: list, seeds_sz: list, save: bool):
    main, errs, words = sweep("main", 3, 3, seeds33, TMAX)
    lost, _, _ = sweep(
        "lost", 3, 3, seeds33, TMAX, [{"cell": 4, "action": "silence", "from": 3}]
    )
    n33 = 9 * len(seeds33)
    at = lambda rows, T: [r for r in rows if r["T"] == T]
    if len(main) != n33 * (TMAX + 1) or len(lost) != n33 * (TMAX + 1):
        sys.exit(f"denominator short: {len(main)} quizzes, expected {n33 * (TMAX + 1)}")

    p4 = sum(r["total"] == 1.0 for r in at(main, 4))
    verdict(
        "C1 ceiling at tick 4", p4 == n33, f"{p4}/{n33} quizzes at 1.0 after tick 4"
    )
    corners = [r for r in at(main, 3) if r["role"] == "corner"]
    cp = sum(r["total"] == 1.0 for r in corners)
    wp = sum(
        all(r["total"] == 1.0 for r in at(main, 3) if r["seed"] == s) for s in seeds33
    )
    verdict(
        "C2 not before tick 4",
        cp == 0 and wp == 0 and len(corners) == 4 * len(seeds33),
        f"{cp}/{len(corners)} corner quizzes at 1.0 after tick 3; {wp}/{len(seeds33)} worlds all at 1.0",
    )
    wrong = sum(r["wrong"] for r in main)
    verdict(
        "C3 never wrong",
        wrong == 0,
        f"{wrong} wrong claims in {len(main)} quizzes (ticks 0-{TMAX})",
    )
    qerr = sum(r["error"] for r in main)
    verdict(
        "C4 valid and within budget",
        errs == 0 and qerr == 0 and words <= 400,
        f"{errs} harness errors over {n33 * TMAX} cell-ticks; {qerr} quiz errors; longest protocol {words} words",
    )
    late = [r for r in main if r["T"] >= 5]
    lp = sum(r["total"] == 1.0 for r in late)
    verdict(
        "C5 stable",
        lp == len(late),
        f"{lp}/{len(late)} quizzes at 1.0 after ticks 5-{TMAX}",
    )

    size_rows, parts, ok6 = [], [], True
    for r, c in [(3, 3)] + SIZES:
        last = 2 * (r + c)
        rows, e6, _ = (
            (main, 0, 0) if (r, c) == (3, 3) else sweep("size", r, c, seeds_sz, last)
        )
        seeds = sorted({x["seed"] for x in rows})
        firsts = [
            first_perfect(
                {
                    T: sum(
                        x["total"] == 1.0
                        for x in rows
                        if x["seed"] == s and x["T"] == T
                    )
                    for T in {x["T"] for x in rows}
                },
                r * c,
            )
            for s in seeds
        ]
        size_rows.append(
            {"grid": f"{r}x{c}", "rows": r, "cols": c, "worlds": len(seeds), "first_perfect_min": min(firsts),
             "first_perfect_median": statistics.median(firsts), "first_perfect_max": max(firsts), "hop_limit": r + c - 2}
        )  # fmt: skip
        if (r, c) != (3, 3):
            end = at(rows, last)
            p, w = sum(x["total"] == 1.0 for x in end), sum(x["wrong"] for x in rows)
            if len(end) != r * c * len(seeds_sz):
                sys.exit(
                    f"denominator short on {r}x{c}: {len(end)} quizzes at tick {last}"
                )
            ok6 &= p == len(end) and w == 0 and e6 == 0
            parts.append(
                f"{r}x{c} {p}/{len(end)} at tick {last} (all perfect from tick {max(firsts)}), {w} wrong"
            )
    verdict("C6 other grid sizes", ok6, "; ".join(parts))

    mean4 = sum(r["total"] for r in at(lost, 4)) / n33
    still = sum(
        all(r["total"] == 1.0 for r in at(lost, 4) if r["seed"] == s) for s in seeds33
    )
    back = sum(r["total"] == 1.0 for r in at(lost, 6))
    verdict(
        "control lost message (centre silenced at tick 3)",
        mean4 < 1.0
        and still == 0
        and sum(r["wrong"] for r in lost) == 0
        and back == n33,
        f"mean {mean4:.3f} after tick 4, {still}/{len(seeds33)} worlds still all at 1.0; "
        f"{sum(r['wrong'] for r in lost)} wrong claims; {back}/{n33} at 1.0 after tick 6",
    )

    if save:
        by_tick = []
        for label, rows in (("main", main), ("lost", lost)):
            for T in range(TMAX + 1):
                for role in ("all", "corner", "edge", "centre"):
                    sel = [r for r in at(rows, T) if role in ("all", r["role"])]
                    row = {
                        "set": label,
                        "T": T,
                        "role": role,
                        "n": len(sel),
                        "mean": round(sum(r["total"] for r in sel) / len(sel), 4),
                    }
                    row.update(
                        {
                            p.replace("_score", ""): round(
                                sum(r[p] for r in sel) / len(sel), 4
                            )
                            for p in PARTS
                        }
                    )
                    row.update(
                        {
                            "perfect": sum(r["total"] == 1.0 for r in sel),
                            "wrong": sum(r["wrong"] for r in sel),
                        }
                    )
                    by_tick.append(row)
        write_tsv("ceiling_by_tick.tsv", by_tick)
        write_tsv("ceiling_sizes.tsv", size_rows)


# ---------------------------------------------------------------- prereg/ceiling_widths.md

NEAR = {1: 8, 2: 6, 3: 3, 4: 1}  # cells at least d hops from a corner of a 3x3 grid


def predicted(width: int) -> int:
    h = width // 4
    head, star = ceiling.phases(h)
    return head + star + 2 * (32 // h)


def floor(width: int) -> int:
    """no cell can be perfect earlier: 32-bit ids d or more hops away arrive through two ports from tick d."""
    return max(-(-((d - 1) * width + 16 * n) // width) for d, n in NEAR.items())


def width_world(label, width, seed, ticks, perturb=None, plant=None):
    """-> ({T: cells perfect}, {T: mean}, wrong claims, harness + quiz errors, longest protocol, escape sightings)."""
    meta, recs = run_world(
        3, 3, seed, ticks, f"{label}-w{width}-{seed}", perturb, width, plant=plant
    )
    errs = sum(len(a["errors"]) for r in recs for a in r["agents"])
    words = max(
        len(re.findall(r"\S+", a["protocol"])) for r in recs for a in r["agents"]
    )
    seen = sum("inverted:1" in a["protocol"] for r in recs for a in r["agents"])
    perfect, mean, wrong = {}, {}, 0
    for T in range(ticks + 1):
        q = quiz(meta, recs, T)
        perfect[T], mean[T] = (
            sum(s["total"] == 1.0 for s in q),
            sum(s["total"] for s in q) / 9,
        )
        wrong += sum(s["wrong"] for s in q)
        errs += sum(bool(s["error"]) for s in q)
    return perfect, mean, wrong, errs, words, seen


def widths(seeds: list, save: bool):
    table, parts, ok1, wrong, errs, words, quizzes = [], [], True, 0, 0, 0, 0
    for w in WIDTHS:
        firsts = []
        for seed in seeds:
            perfect, _, wr, er, wd, _ = width_world("main", w, seed, predicted(w) + 6)
            firsts.append(first_perfect(perfect, 9))
            wrong, errs, words, quizzes = (
                wrong + wr,
                errs + er,
                max(words, wd),
                quizzes + 9 * len(perfect),
            )
        late = sum(x is None or x > predicted(w) for x in firsts)
        ok1 &= late == 0 and len(firsts) == len(seeds)
        got = sorted(x for x in firsts if x is not None)
        parts.append(
            f"{w} bits: predicted {predicted(w)}, observed {got[0] if got else None}-{got[-1] if got else None}, {late}/{len(firsts)} worlds late"
        )
        table.append(
            {"port_bits": w, "worlds": len(firsts), "first_perfect_min": got[0] if got else "", "first_perfect_max": got[-1] if got else "",
             "late_worlds": late, "predicted": predicted(w), "floor": floor(w)}
        )  # fmt: skip
        if w == 4:
            by130 = sum(x is not None and x <= 130 for x in firsts)
    verdict("D1 first perfect tick", ok1, "; ".join(parts))
    verdict(
        "D2 4 bits within 130 ticks",
        by130 == len(seeds),
        f"{by130}/{len(seeds)} worlds perfect by tick 130",
    )
    verdict("D3 never wrong", wrong == 0, f"{wrong} wrong claims in {quizzes} quizzes")
    verdict(
        "D5 valid",
        errs == 0 and words <= 400,
        f"{errs} errors; longest protocol {words} words",
    )

    mid = (
        sum(ceiling.phases(2)) + 1 + 8
    )  # the centre, silent for one tick in the middle of its first square
    broken = lost_wrong = 0
    final = []
    for seed in seeds:
        perfect, mean, wr, _, _, _ = width_world(
            "lost",
            8,
            seed,
            predicted(8) + 6,
            [{"cell": 4, "action": "silence", "from": mid}],
        )
        broken += perfect[predicted(8)] != 9
        lost_wrong += wr
        final.append(mean[predicted(8) + 6])
    verdict(
        "control lost chunk (8 bits)",
        broken >= 1,
        f"silenced at tick {mid}: {broken}/{len(seeds)} worlds not all-perfect at tick {predicted(8)}; mean {sum(final) / len(final):.3f} at the end; "
        f"{lost_wrong} wrong claims over the run (a declared limit, not a criterion)",
    )

    def zero_heads(
        meta,
    ):  # one square whose four ids all begin with a zero tick at 16 bits
        for k in (0, 1, 3, 4):
            meta["agents"][k]["seed"] = "0000" + meta["agents"][k]["seed"][4:]

    end = predicted(16) + 60
    e_perfect, _, e_wrong, _, _, seen = width_world(
        "escape", 16, 1001, end, plant=zero_heads
    )
    ceiling.USE_ESCAPE = False
    n_perfect, _, n_wrong, _, _, _ = width_world(
        "noescape", 16, 1001, end, plant=zero_heads
    )
    ceiling.USE_ESCAPE = True
    verdict(
        "control planted zero-start square (16 bits)",
        e_perfect[end] == 9
        and e_wrong == 0
        and seen > 0
        and not (n_perfect[end] == 9 and n_wrong == 0),
        f"with escape: {e_perfect[end]}/9 perfect at tick {end} (all perfect from tick {first_perfect(e_perfect, 9)}), {e_wrong} wrong, "
        f"escape seen in {seen} notebook states; without: {n_perfect[end]}/9 perfect, {n_wrong} wrong",
    )
    if save:
        write_tsv("ceiling_widths.tsv", table)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--dev",
        action="store_true",
        help="13 worlds instead of 103; tables are not rewritten",
    )
    ap.add_argument(
        "--widths", action="store_true", help="also run port widths 4 to 128 bits"
    )
    args = ap.parse_args()
    seeds33 = [1001, 1002, 1003] + list(range(1, 11 if args.dev else 101))
    seeds_sz = list(range(1, 4 if args.dev else 21))
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as d:
        sim.RUNS = Path(d)
        controls()
        part1(seeds33, seeds_sz, save=not args.dev)
        if args.widths:
            widths(seeds33, save=not args.dev)
    print(
        f"{'ALL PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}  ({len(seeds33)} worlds, {time.perf_counter() - t0:.0f} s)"
    )
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
