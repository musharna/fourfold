"""words_vs_acts: R3 (exploratory) — does what each agent wrote in its protocol match its own port traffic.

what it does   per agent of a run, from ticks.jsonl + the true wiring in meta:
                 id_out      own random ID appears in its own outputs (any tick)          [act]
                 nb_heard    true neighbors whose ID ever appeared in its inputs          [act]
                 nb_named    true neighbors whose ID its final protocol names             [word]
                 named_not_heard  neighbors named but never heard (claim without evidence)
                 far_named   non-neighbor IDs named in the final protocol (relayed or false)
                 text_out    emergence.is_text on any of its outputs, L=10                 [act]
                 text_word   final protocol says its messages carry ASCII/text            [word]
               plus a null: 9 random 32-bit IDs absent from the run, searched in all outputs (id_out_null).
when to use    P0 R3 readout; any fourfold hex-port run.
output         TSV per agent (analysis/r3_words_acts.tsv) + per-run summary on stdout.
must pass      positive control examples/sol-50 (erin): text_out 9/9, id_out 9/9, nb_heard = all links;
               text_word is REPORT-ONLY: the control showed it at 5/9 on erin's run (agents quote messages
               instead of saying "ascii"); widening it to quotes would fire on decoded hex-speak, so it was
               not tuned after seeing results.
               null id_out (random absent IDs) must be 0 for every run — the script exits 2 if either fails.
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
from emergence import is_text  # noqa: E402

TEXT_WORD = re.compile(
    r"\bascii\b|\btext\b|plain ?text|\bchars?\b|characters|letters", re.I
)


def load(p: Path):
    rows = [
        json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()
    ]
    meta = next(r for r in rows if r.get("type") == "meta")
    ticks = [r for r in rows if r.get("type") == "tick"]
    return meta, ticks


def per_agent(meta, ticks):
    ags = meta["agents"]
    seed = {a["id"]: a["seed"].lower() for a in ags}
    nbrs = {a["id"]: {l["agent"] for l in a["links"] if l} for a in ags}
    outs = {i: [] for i in seed}
    ins = {i: [] for i in seed}
    proto = {i: "" for i in seed}
    for t in ticks:
        for k, rec in enumerate(t["agents"]):
            i = ags[k]["id"]
            outs[i] += [v.lower() for v in rec.get("outputs") or []]
            ins[i] += [v.lower() for v in rec.get("inputs") or []]
            if rec.get("protocol"):
                proto[i] = rec["protocol"]
    ids = sorted(seed)
    rows = []
    for n, i in enumerate(ids):
        fake = f"{random.Random(f'{meta["run_id"]}:{i}').getrandbits(32):08x}"
        assert fake not in seed.values()
        pl = proto[i].lower()
        heard = {b for b in nbrs[i] if any(seed[b] in v for v in ins[i])}
        named = {b for b in nbrs[i] if seed[b] in pl}
        far = {b for b in ids if b != i and b not in nbrs[i] and seed[b] in pl}
        rows.append(
            {
                "agent": i,
                "n_nbrs": len(nbrs[i]),
                "id_out": any(seed[i] in v for v in outs[i]),
                "id_out_null": any(fake in v for o in outs.values() for v in o),
                "nb_heard": len(heard),
                "nb_named": len(named),
                "named_not_heard": len(named - heard),
                "far_named": len(far),
                "text_out": any(is_text(v, 10) for v in outs[i]),
                "text_word": bool(TEXT_WORD.search(proto[i])),
            }
        )
    return rows


COLS = [
    "run",
    "agent",
    "n_nbrs",
    "id_out",
    "id_out_null",
    "nb_heard",
    "nb_named",
    "named_not_heard",
    "far_named",
    "text_out",
    "text_word",
]


def summarize(run, rows):
    s = lambda k: sum(int(r[k]) for r in rows)
    return (
        f"{run}: id_out {s('id_out')}/9 (null {s('id_out_null')}) | nb heard {s('nb_heard')}/{s('n_nbrs')} "
        f"named {s('nb_named')} (unheard {s('named_not_heard')}) far {s('far_named')} | "
        f"text out {s('text_out')}/9 word {s('text_word')}/9"
    )


def main():
    paths = [ROOT / "examples/sol-50/ticks.jsonl"] + sorted(
        (ROOT / "runs").glob("p0-*/ticks.jsonl")
    )
    out = ["\t".join(COLS)]
    fail = []
    for p in paths:
        run = p.parent.name
        meta, ticks = load(p)
        if not ticks:
            continue
        rows = per_agent(meta, ticks)
        for r in rows:
            out.append("\t".join(str(v) for v in [run] + [r[c] for c in COLS[1:]]))
        print(summarize(run, rows))
        if any(r["id_out_null"] for r in rows):
            fail.append(f"{run}: random-ID null id_out nonzero")
        if run == "sol-50":
            s = lambda k: sum(int(r[k]) for r in rows)
            if not (s("text_out") == 9 and s("id_out") == 9 and s("nb_heard") == s("n_nbrs")):
                fail.append(f"positive control sol-50 failed: {summarize(run, rows)}")
    (ROOT / "analysis" / "r3_words_acts.tsv").write_text(
        "\n".join(out) + "\n", encoding="utf-8"
    )
    if fail:
        sys.exit("CONTROL FAILED: " + "; ".join(fail))


if __name__ == "__main__":
    main()
