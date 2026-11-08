"""P0 gates, run before any real P0 output is opened. prints counts; exits 1 on any failure.

G1 scorer plant      perfect answers built from the true wiring -> eval.score_agent total == 1.0
                     for every agent; scrambled twin (wrong ids) < 1.0; empty answer == 0.0.
G2 detector null     random 128-bit ports: pick the smallest L in (8, 10, 12, 14) whose false
                     text-event rate is < 0.05 per 3x3x50 run (frozen rule; uses the null only).
G3 detector plant    a synthetic run with text planted from tick 7 on, in all agents by tick 15:
                     detector returns exactly t_first=7, t_all=15; its all-zero twin returns None.
G4 independent check sol-50 example vs erin's README timeline (first text t6, all nine by t14),
                     tolerance +-1 tick each. the README did not choose L (G2 did).
"""

from __future__ import annotations

import json
import random
import signal
import sys
import tempfile
from pathlib import Path

signal.signal(
    signal.SIGALRM,
    lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)),
)
signal.alarm(300)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "analysis"))
import eval as ev  # noqa: E402
from emergence import emergence, is_text  # noqa: E402

fails = []
SOL = ROOT / "examples" / "sol-50" / "ticks.jsonl"
meta = json.loads(SOL.read_text(encoding="utf-8").splitlines()[0])


# ---- G1 scorer plant
def perfect(meta, k, scramble=False):
    agents = meta["agents"]
    seeds = [a["seed"] for a in agents]
    if scramble:
        seeds = seeds[1:] + seeds[:1]
    a = agents[k]
    R, C = meta["rows"], meta["cols"]
    grid = {tuple(x["pos"]): seeds[i] for i, x in enumerate(agents)}
    drawn = "\n".join("  ".join(grid[(r, c)] for c in range(C)) for r in range(R))
    role = ev.role_of(sum(1 for l in a["links"] if l))
    word = {
        "centre": "the center",
        "edge": "an edge (middle of a side)",
        "corner": "a corner",
    }[role]
    out = [
        f"<count>{len(agents)}</count>",
        f"<arrangement>a {R}x{C} grid:\n{drawn}\n</arrangement>",
        f"<position>{word}</position>",
    ]
    # p_i is fed by the neighbour's q_port; q_i feeds the neighbour's p_port (shared side)
    for kind, other in (("p", "q"), ("q", "p")):
        for i in range(4):
            l = a["links"][i]
            out.append(
                f"<{kind}{i}>nothing</{kind}{i}>"
                if l is None
                else f"<{kind}{i}>{seeds[l['agent']]} {other}{l['port']}</{kind}{i}>"
            )
    return "\n".join(out)


tot = [
    ev.score_agent(meta, k, perfect(meta, k))["total"]
    for k in range(len(meta["agents"]))
]
scr = [
    ev.score_agent(meta, k, perfect(meta, k, scramble=True))["total"]
    for k in range(len(meta["agents"]))
]
emp = [ev.score_agent(meta, k, "")["total"] for k in range(len(meta["agents"]))]
g1 = (
    all(t == 1.0 for t in tot)
    and all(s < 1.0 for s in scr)
    and all(e == 0.0 for e in emp)
)
print(
    f"G1 scorer plant: perfect {sum(t == 1.0 for t in tot)}/{len(tot)} == 1.0; "
    f"scrambled <1.0 {sum(s < 1.0 for s in scr)}/{len(scr)} (mean {sum(scr) / len(scr):.2f}); "
    f"empty ==0 {sum(e == 0.0 for e in emp)}/{len(emp)} -> {'PASS' if g1 else 'FAIL'}"
)
if not g1:
    fails.append("G1")

# ---- G2 null: frozen rule picks L from random ports only
rng = random.Random(20261108)
N = 400_000
ports = [f"{rng.getrandbits(128):032x}" for _ in range(N)]
# agent-level null: each agent writes 4 ports x 50 ticks = 200 values; it falsely qualifies on
# >= MIN_DISTINCT_VALUES flagged values. a run has a false event if any of its 9 agents qualifies.
from emergence import MIN_DISTINCT_VALUES   # noqa: E402
per_agent, n_agents = 200, 9
chosen = None
for L in (8, 10, 12, 14):
    flags = [is_text(p, L) for p in ports]
    f = sum(flags) / N
    agents = [sum(flags[i:i + per_agent]) >= MIN_DISTINCT_VALUES for i in range(0, N, per_agent)]
    runs = [any(agents[i:i + n_agents]) for i in range(0, len(agents) - n_agents + 1, n_agents)]
    lam = f * per_agent
    import math
    p_agent = 1 - math.exp(-lam) * sum(lam ** j / math.factorial(j) for j in range(MIN_DISTINCT_VALUES))
    analytic = 1 - (1 - p_agent) ** n_agents
    sim_rate = sum(runs) / len(runs)
    print(f"G2 null L={L}: port flag rate {f:.2e}; false-event runs simulated {sum(runs)}/{len(runs)} "
          f"= {sim_rate:.3f}, analytic {analytic:.4f} per 3x3x50 run")
    if chosen is None and sim_rate < 0.05 and analytic < 0.05:
        chosen = L
print(f"G2 chosen L = {chosen} -> {'PASS' if chosen else 'FAIL'}")
if not chosen:
    fails.append("G2")
    sys.exit("gates FAILED: " + ", ".join(fails))


# ---- G3 planted synthetic run through the same loader
def text_hex(s: str) -> str:
    return s.encode().ljust(16, b"\x00")[:16].hex()


def write_run(path: Path, plant: bool):
    rows = [
        {
            "type": "meta",
            "run_id": "plant" if plant else "null",
            "config": {"port_mode": "hex"},
            "agents": [{"seed": f"{i:08x}"} for i in range(9)],
        }
    ]
    for t in range(1, 31):
        agents = []
        for i in range(9):
            outs = [
                f"{rng.getrandbits(128):032x}" if t % 3 else "0" * 32 for _ in range(4)
            ]
            if plant and t >= 7 + i:  # agent i starts at tick 7+i; agent 8 at 15
                # erin's format: 4-byte id + 12 bytes of text, text varies by tick
                outs[1] = f"{rng.getrandbits(32):08x}" + f"HELLO {i} T{t:03d}".encode().hex()
            if not plant:
                outs = ["0" * 32] * 4
            agents.append({"agent": i, "outputs": outs})
        rows.append({"type": "tick", "t": t, "agents": agents})
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


with tempfile.TemporaryDirectory() as d:
    p, z = Path(d) / "plant.jsonl", Path(d) / "null.jsonl"
    write_run(p, True)
    write_run(z, False)
    rp, rz = emergence(p, chosen), emergence(z, chosen)
g3 = (rp["t_first"], rp["t_all"]) == (7, 15) and (rz["t_first"], rz["t_all"]) == (
    None,
    None,
)
print(
    f"G3 plant: t_first={rp['t_first']} t_all={rp['t_all']} (want 7, 15); "
    f"null twin t_first={rz['t_first']} t_all={rz['t_all']} (want None) -> {'PASS' if g3 else 'FAIL'}"
)
if not g3:
    fails.append("G3")

# ---- G2b realistic null: a full echo-agent run (structured traffic, no language)
import subprocess   # noqa: E402
rid = f"gate-echo-null-{rng.getrandbits(24):06x}"
subprocess.run([sys.executable, str(ROOT / "sim.py"), "--agent", "echo", "--ticks", "50",
                "--world-seed", "7", "--run-id", rid], check=True, capture_output=True, timeout=120)
re_ = emergence(ROOT / "runs" / rid / "ticks.jsonl", chosen)
g2b = re_["adopted"] == 0 and re_["ticks"] == 50
print(f"G2b echo null: {re_['ticks']} ticks, adopted {re_['adopted']}/9 (want 0) -> {'PASS' if g2b else 'FAIL'}")
if not g2b:
    fails.append("G2b")

# ---- G4 independent reference: erin's README timeline for sol-50
r = emergence(SOL, chosen)
ok = (
    r["t_first"] is not None
    and r["t_all"] is not None
    and abs(r["t_first"] - 6) <= 1
    and abs(r["t_all"] - 14) <= 1
)
print(
    f"G4 sol-50 vs README: t_first={r['t_first']} (README 6), t_all={r['t_all']} (README 14), "
    f"adopted {r['adopted']}/{r['n_agents']} -> {'PASS' if ok else 'FAIL'}"
)
if not ok:
    fails.append("G4")

print("ALL GATES PASS" if not fails else "gates FAILED: " + ", ".join(fails))
sys.exit(1 if fails else 0)
