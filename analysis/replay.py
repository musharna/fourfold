"""replay: re-send one stored agent-tick prompt to a model route N times; score whether it writes ASCII text.

what it does   T_text battery (prereg/T_text.md). states S1/S2/S3 x arms C-low, C-med (codex on Plus) and
               A-bare, A-bare-low, A-scaf-low, A-scaf-med (OpenRouter, provider pinned to OpenAI).
               `run` appends one JSON line per call to analysis/t_text/calls.jsonl (resumable);
               `summary` prints counts per cell and the frozen comparisons (Fisher exact, two-sided).
when to use    T_text; any "would this agent, in this exact state, do X under route Y" question.
output         calls.jsonl rows {arm,state,i,text,outputs,raw,usage,error}; analysis/t_text/summary.tsv.
must pass      `control`: erin's stored replies at S1/S2 score text, ours at S3 does not, previous outputs at
               every state are non-text (so a reply with missing tags cannot score text), S2's inputs carry
               text, Fisher on [[3,0],[0,3]] = 0.1. exits 2 otherwise. a cell with < N valid calls is OPEN.
               exit 3 = codex usage limit (rerun later; done calls are kept).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "analysis"))
import sim  # noqa: E402
from emergence import is_text  # noqa: E402

OUT = ROOT / "analysis" / "t_text"
CALLS = OUT / "calls.jsonl"
CAPTURE = ROOT / "analysis" / "codex_capture" / "default.json"
MAX_ATTEMPTS = 3  # errored calls retried at most this many times per (arm, state, i)

STATES = {  # name: (run dir, agent index, tick)
    "S1": ("examples/sol-50", 6, 6),  # founder: writes ID + "ECHO Qj NOW!"
    "S2": ("examples/sol-50", 3, 7),  # contagion: p2 carries "ECHO Q0 NOW!"
    "S3": ("runs/p0-solcx-cued-1002", 6, 6),  # ours, same cell and tick
}
ARMS = {
    "C-low": ("codex", []),
    "C-med": ("codex", ["-c", "model_verbosity=medium"]),
    "A-bare": ("api", {"scaf": False, "verbosity": None}),
    "A-bare-low": ("api", {"scaf": False, "verbosity": "low"}),
    "A-scaf-low": ("api", {"scaf": True, "verbosity": "low"}),
    "A-scaf-med": ("api", {"scaf": True, "verbosity": "medium"}),
}


class UsageLimit(Exception):
    pass


def load_state(name: str) -> dict:
    run, idx, t = STATES[name]
    # read-only (sim.load_run truncates a half-written tail on disk)
    lines = [
        json.loads(l)
        for l in (ROOT / run / "ticks.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    meta = next(r for r in lines if r.get("type") == "meta")
    ticks = [r for r in lines if r.get("type") == "tick"]
    sim.set_width(meta["config"])
    by_t = {r["t"]: r for r in ticks}
    rec = by_t[t]["agents"][idx]
    prev = by_t[t - 1]["agents"][idx] if t > 1 else None
    return {
        "meta": meta,
        "system": sim.system_prompt(meta, meta["agents"][idx]["seed"]),
        "prompt": rec["prompt"],
        "stored_raw": rec["raw"],
        "inputs": rec["inputs"],
        "prev_outputs": prev["outputs"] if prev else [sim.ZERO] * 4,
        "prev_protocol": prev["protocol"] if prev else "",
        "word_limit": int(meta["config"]["protocol_word_limit"]),
    }


def score(st: dict, raw: str) -> tuple[bool, list, list]:
    outs, _log, _proto, errors, _notices = sim.parse_response(
        raw, st["prev_outputs"], st["prev_protocol"], st["word_limit"]
    )
    return any(is_text(o, 10) for o in outs), outs, errors


def fisher(a: int, n1: int, b: int, n2: int) -> float:
    """two-sided Fisher exact p for a/n1 vs b/n2."""
    k, N = a + b, n1 + n2
    pr = lambda x: math.comb(n1, x) * math.comb(n2, k - x) / math.comb(N, k)
    p0 = pr(a)
    return min(
        1.0,
        sum(
            pr(x)
            for x in range(max(0, k - n2), min(k, n1) + 1)
            if pr(x) <= p0 * (1 + 1e-9)
        ),
    )


def control() -> None:
    fail = []
    for name, want in (("S1", True), ("S2", True), ("S3", False)):
        st = load_state(name)
        got, _, _ = score(st, st["stored_raw"])
        if got != want:
            fail.append(f"{name}: stored reply text={got}, expected {want}")
        if any(is_text(o, 10) for o in st["prev_outputs"]):
            fail.append(f"{name}: previous outputs already contain text")
    if not any(is_text(v, 10) for v in load_state("S2")["inputs"]):
        fail.append("S2: inputs carry no text")
    if abs(fisher(3, 3, 0, 3) - 0.1) > 1e-9:
        fail.append(f"fisher([[3,0],[0,3]]) = {fisher(3, 3, 0, 3)}, expected 0.1")
    if fail:
        sys.exit(2 if print("CONTROL FAILED:\n  " + "\n  ".join(fail)) is None else 2)
    print(
        "control PASS: S1/S2 stored replies score text, S3 does not; prev outputs non-text; S2 inputs text; fisher ok"
    )


# ---------- routes ----------


def scaffold() -> tuple[list, list]:
    """codex's extra developer/user blocks and its tools, flattened to chat-completions functions.
    approximation: namespaces and the freeform `exec` grammar become plain functions; the grammar
    text is kept in the description so the token load is preserved."""
    r = json.loads(CAPTURE.read_text(encoding="utf-8"))
    items = r["input"]
    assert (
        items[0]["type"] == "additional_tools"
        and items[-1]["content"][0]["text"] == "TICK-SENTINEL prompt"
    )
    text = lambda it: "".join(c.get("text", "") for c in it["content"])
    dev = [text(it) for it in items[2:] if it.get("role") == "developer"]
    usr = [text(it) for it in items[2:-1] if it.get("role") == "user"]
    tools = []
    for ns in items[0]["tools"]:
        for j, s in enumerate(ns["tools"]):
            desc = (
                ns.get("description", "") + "\n\n"
                if j == 0 and ns.get("description")
                else ""
            ) + s.get("description", "")
            if s.get("type") == "custom":
                desc += "\n\ninput format:\n" + json.dumps(s.get("format"))
                params = {
                    "type": "object",
                    "properties": {"input": {"type": "string"}},
                    "required": ["input"],
                }
            else:
                params = s.get("parameters") or {"type": "object", "properties": {}}
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": f"{ns['name']}_{s['name']}",
                        "description": desc,
                        "parameters": params,
                    },
                }
            )
    return dev, usr, tools


def openrouter_key() -> str:
    k = os.environ.get("OPENROUTER_API_KEY", "")
    if not k:
        m = re.search(
            r"sk-or-[A-Za-z0-9_-]+",
            (Path.home() / ".config/openrouter/credentials").read_text(),
        )
        k = m.group(0) if m else ""
    if not k:
        sys.exit(
            "no OpenRouter key (env OPENROUTER_API_KEY or ~/.config/openrouter/credentials)"
        )
    return k


async def call_api(client, opts: dict, st: dict) -> dict:
    if opts["scaf"]:
        dev, usr, tools = scaffold()
        msgs = [{"role": "developer", "content": st["system"]}] + [
            {"role": "developer", "content": d} for d in dev
        ]
        msgs += [{"role": "user", "content": u} for u in usr] + [
            {"role": "user", "content": st["prompt"]}
        ]
    else:
        msgs, tools = (
            [
                {"role": "system", "content": st["system"]},
                {"role": "user", "content": st["prompt"]},
            ],
            None,
        )
    body = {
        "model": "openai/gpt-6.1-sol",
        "messages": msgs,
        "max_completion_tokens": 16000,
        "reasoning": {"effort": "high"},
        "provider": {"order": ["openai"], "allow_fallbacks": False},
    }
    if tools:
        body |= {"tools": tools, "tool_choice": "auto", "parallel_tool_calls": False}
    if opts["verbosity"]:
        body["verbosity"] = opts["verbosity"]
    last = ""
    for attempt in range(4):
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions", json=body
        )
        if r.status_code == 402:
            raise UsageLimit(f"openrouter 402 (no credit): {r.text[:200]}")
        if r.status_code == 200:
            d = r.json()
            if "choices" in d:
                m = d["choices"][0]["message"]
                err = (
                    None
                    if m.get("content")
                    else f"no content; tool_calls={json.dumps(m.get('tool_calls'))[:300]}"
                )
                return {
                    "raw": m.get("content") or "",
                    "usage": d.get("usage"),
                    "error": err,
                    "provider": d.get("provider"),
                }
        last = f"{r.status_code} {r.text[:300]}"
        await asyncio.sleep(2**attempt * 3)
    return {"raw": "", "usage": None, "error": f"api failed: {last}"}


async def call_codex(agent, st: dict) -> dict:
    turn = sim.Turn(
        t=0, state=None, inputs=[], changed=[], system=st["system"], prompt=st["prompt"]
    )
    rep = await agent.act(turn)
    if rep.error and "usage limit" in rep.error:
        raise UsageLimit(rep.error[:300])
    return {"raw": rep.raw, "usage": rep.usage, "error": rep.error}


# ---------- battery ----------


def rows() -> list[dict]:
    return (
        [json.loads(l) for l in CALLS.read_text().splitlines() if l.strip()]
        if CALLS.exists()
        else []
    )


async def run(arms: list, states: list, n: int) -> int:
    import httpx

    control()
    OUT.mkdir(parents=True, exist_ok=True)
    have = rows()
    done = {(r["arm"], r["state"], r["i"]) for r in have if not r["error"]}
    tries: dict = {}
    for r in have:
        tries[(r["arm"], r["state"], r["i"])] = (
            tries.get((r["arm"], r["state"], r["i"]), 0) + 1
        )
    todo = [
        (a, s, i)
        for a in arms
        for s in states
        for i in range(n)
        if (a, s, i) not in done and tries.get((a, s, i), 0) < MAX_ATTEMPTS
    ]
    print(f"{len(todo)} calls to make ({len(done)} done)")
    if not todo:
        return 0
    st = {s: load_state(s) for s in states}
    codex = sim.CodexCLIAgent(
        {
            "jail": "scripts/codex_jail.sh",
            "model": "gpt-6.1-sol",
            "effort": "high",
            "timeout": 900,
            "retries": 3,
            "max_concurrency": 9,
            "extra_args": [],
        }
    )
    client = (
        httpx.AsyncClient(
            timeout=600, headers={"Authorization": f"Bearer {openrouter_key()}"}
        )
        if any(ARMS[a][0] == "api" for a, _, _ in todo)
        else None
    )
    api_sem, stop, lock = asyncio.Semaphore(9), asyncio.Event(), asyncio.Lock()

    async def one(a, s, i):
        if stop.is_set():
            return
        kind, opts = ARMS[a]
        try:
            if kind == "codex":
                codex.cfg = {**codex.cfg, "extra_args": opts}
                res = await call_codex(codex, st[s])
            else:
                async with api_sem:
                    res = await call_api(client, opts, st[s])
        except UsageLimit as e:
            if not stop.is_set():
                print(f"STOP {a}: {e}")
            stop.set()
            return
        text, outs, perr = score(st[s], res["raw"]) if res["raw"] else (False, [], [])
        row = {
            "arm": a,
            "state": s,
            "i": i,
            "text": text,
            "outputs": outs,
            "parse_errors": perr,
            **res,
        }
        async with lock:
            with CALLS.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
        print(
            f"{a:11s} {s} #{i:2d} text={text} {'ERR ' + str(res['error'])[:80] if res['error'] else ''}",
            flush=True,
        )

    # codex_cfg is shared, so codex arms run one arm at a time; api arms run concurrently
    for a in arms:
        if ARMS[a][0] == "codex":
            await asyncio.gather(*(one(*x) for x in todo if x[0] == a))
    await asyncio.gather(*(one(*x) for x in todo if ARMS[x[0]][0] == "api"))
    if client:
        await client.aclose()
    return 3 if stop.is_set() else 0


COMPARISONS = [  # (hypothesis, higher arm, lower arm, state)
    ("H-verb codex", "C-med", "C-low", "S1"),
    ("H-verb api", "A-bare", "A-bare-low", "S1"),
    ("H-scaf (low)", "A-bare-low", "A-scaf-low", "S1"),
    ("H-scaf (med)", "A-bare", "A-scaf-med", "S1"),
    ("H-serve", "A-scaf-low", "C-low", "S1"),
    ("H-copy", "A-bare", "C-low", "S2"),
]


def summary(n: int) -> None:
    cell: dict = {}
    for r in rows():
        if not r["error"]:
            c = cell.setdefault((r["arm"], r["state"]), {"k": 0, "n": 0, "tok": []})
            c["k"] += r["text"]
            c["n"] += 1
            u = r.get("usage") or {}
            c["tok"].append(u.get("output_tokens") or u.get("completion_tokens") or 0)
    lines = ["arm\tstate\ttext\tvalid\tmedian_out_tokens"]
    for a in ARMS:
        for s in STATES:
            c = cell.get((a, s))
            if c:
                t = sorted(c["tok"])
                lines.append(f"{a}\t{s}\t{c['k']}\t{c['n']}\t{t[len(t) // 2]}")
    print("\n".join(lines))
    (OUT / "summary.tsv").write_text("\n".join(lines) + "\n")
    full = lambda a, s: (a, s) in cell and cell[(a, s)]["n"] >= n
    supported = {}
    print()
    for h, hi, lo, s in COMPARISONS:
        if not (full(hi, s) and full(lo, s)):
            print(f"{h:14s} OPEN (cells {hi}/{lo} @{s} not at n={n})")
            continue
        A, B = cell[(hi, s)], cell[(lo, s)]
        p = fisher(A["k"], A["n"], B["k"], B["n"])
        ok = A["k"] / A["n"] > B["k"] / B["n"] and p < 0.05
        supported[h] = ok
        print(
            f"{h:14s} {hi} {A['k']}/{A['n']} vs {lo} {B['k']}/{B['n']} @{s}  p={p:.3g}  {'SUPPORTED' if ok else 'not supported'}"
        )
    if full("C-low", "S1"):
        causal = any(v for k, v in supported.items() if not k.startswith("H-copy"))
        k = cell[("C-low", "S1")]["k"]
        verdict = "SUPPORTED" if k >= 5 and not causal else "not supported"
        corr = (
            f"; A-bare @S3 {cell[('A-bare', 'S3')]['k']}/{cell[('A-bare', 'S3')]['n']}"
            if full("A-bare", "S3")
            else "; A-bare @S3 OPEN"
        )
        print(
            f"{'H-chance':14s} C-low @S1 {k}/{cell[('C-low', 'S1')]['n']} (>=5 needed), no route cause supported={not causal}  {verdict}{corr}"
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["control", "run", "summary"])
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--states", default=",".join(STATES))
    ap.add_argument("--n", type=int, default=20)
    a = ap.parse_args()
    if a.cmd == "control":
        control()
    elif a.cmd == "run":
        arms, states = a.arms.split(","), a.states.split(",")
        bad = [x for x in arms if x not in ARMS] + [
            x for x in states if x not in STATES
        ]
        if bad:
            sys.exit(f"unknown arm/state: {bad}")
        sys.exit(asyncio.run(run(arms, states, a.n)))
    else:
        summary(a.n)


if __name__ == "__main__":
    main()
