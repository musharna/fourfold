"""test_p1_hooks: checks for the per-cell, scripted-cell and perturbation hooks in sim.py / eval.py.

what it does   1 planted truth: the founder template renders erin's exact sol-50 founder value (agent 7, t6, q0).
               2 integration: an echo run with a scripted founder in cell 4, cell 2 silenced t10-15, cell 0 wiped
                 at t20 — checks the founder's ports, the silence (zero ports, not asked, marked), the wipe, that
                 text reaches a neighbor (echo cells relay it), and that eval quizzes only the 8 non-scripted cells.
               3 fail-loud: bad template, out-of-grid cell, unknown perturbation each exit nonzero with a message.
when to use    after any change to these hooks; the golden echo regression (scripts/golden_hash.py) covers the default path.
must pass      all asserts; prints PASS lines and exits 1 on the first failure.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "analysis"))
import sim  # noqa: E402
from emergence import is_text  # noqa: E402

PY = sys.executable
FOUNDER = ["{id}<ECHO Q{jd} NOW!>"] * 4


def run_sim(toml: str, run_id: str, ticks: int) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
        f.write(toml)
    return subprocess.run(
        [PY, "sim.py", "--config", f.name, "--run-id", run_id, "--ticks", str(ticks)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def ok(cond, msg):
    if not cond:
        sys.exit(f"FAIL: {msg}")
    print(f"PASS: {msg}")


import shutil  # noqa: E402

for old in (ROOT / "runs").glob(
    "p1test-*"
):  # fixed run ids: clear the previous test's runs
    shutil.rmtree(old)


# 1. planted truth from erin's run
sim.set_width({})
got = sim.ScriptedAgent.render(FOUNDER[0], "db06f745", 6, 0)
ok(
    got == "db06f7454543484f205130204e4f5721",
    f"founder template reproduces erin's founder q0 ({got})",
)
ok(is_text(got, 10), "founder value passes the L=10 text detector")
ok(
    sim.ScriptedAgent.render("{id}{t}{j}", "deadbeef", 6, 2)
    == "deadbeef0000000600000002" + "0" * 8,
    "id/tick/port substitution and zero padding",
)

# 2. integration
base = """agent = "echo"
world_seed = 7
store_prompts = true
[echo]
malformed_rate = 0.0
[cells.4]
agent = "scripted"
[cells.4.scripted]
program = [{from = 1, to = 5, out = ["{id}{t}{j}", "{id}{t}{j}", "{id}{t}{j}", "{id}{t}{j}"]},
           {from = 6, out = ["{id}<ECHO Q{jd} NOW!>", "{id}<ECHO Q{jd} NOW!>", "{id}<ECHO Q{jd} NOW!>", "-"]}]
[[perturb]]
cell = 2
action = "silence"
from = 10
to = 15
[[perturb]]
cell = 0
action = "wipe"
from = 20
"""
rid = "p1test-integration"
p = run_sim(base, rid, 30)
ok(p.returncode == 0, f"integration run exits 0 ({p.stderr[-300:]})")
rows = [
    json.loads(l)
    for l in (ROOT / "runs" / rid / "ticks.jsonl").read_text().splitlines()
]
meta, ticks = rows[0], {r["t"]: r for r in rows[1:]}
seed4 = meta["agents"][4]["seed"]
ok(
    ticks[3]["agents"][4]["outputs"][1] == f"{seed4}{3:08x}{1:08x}" + "0" * 8,
    "scripted rule 1 (t3, q1)",
)
ok(
    ticks[6]["agents"][4]["outputs"][2]
    == sim.ScriptedAgent.render(FOUNDER[2], seed4, 6, 2),
    "scripted rule 2 (t6, q2)",
)
ok(
    ticks[6]["agents"][4]["outputs"][3] == ticks[5]["agents"][4]["outputs"][3],
    "'-' holds the port",
)
ok(
    all(
        ticks[t]["agents"][2]["outputs"] == [sim.ZERO] * 4
        and ticks[t]["agents"][2]["perturbed"] == ["silence"]
        and ticks[t]["agents"][2]["raw"] == ""
        for t in range(10, 16)
    ),
    "cell 2 silenced t10-15: zero ports, not asked, marked",
)
ok(
    ticks[16]["agents"][2]["raw"] != "" and "perturbed" not in ticks[16]["agents"][2],
    "cell 2 back at t16",
)
ok("perturbed" not in ticks[9]["agents"][2], "no mark before the silence")
ok(
    ticks[20]["agents"][0]["perturbed"] == ["wipe"]
    and "protocol:\n(empty)" in ticks[20]["agents"][0]["prompt"]
    and "recent log:\n(empty)" in ticks[20]["agents"][0]["prompt"],
    "cell 0 wiped at t20: empty protocol and log in its prompt",
)
ok(
    ticks[19]["agents"][0]["protocol"] != "",
    "cell 0 had a protocol before the wipe (the wipe check can fail)",
)
# per founder port: the slot of the neighbor that reads q_j carries text from t7 iff q_j is a text rule ("-" holds hex)
for j, l in enumerate(meta["agents"][4]["links"]):
    if not l:
        continue
    got = any(
        is_text(ticks[t]["agents"][l["agent"]]["inputs"][l["port"]], 10)
        for t in range(7, 31)
    )
    ok(
        got == (j < 3),
        f"founder q{j} -> cell {l['agent']} p{l['port']}: text {'arrives' if j < 3 else 'never arrives (held)'}",
    )
e = subprocess.run([PY, "eval.py", rid], cwd=ROOT, capture_output=True, text=True)
ok(e.returncode == 0, f"eval exits 0 ({e.stderr[-200:]})")
res = json.loads((ROOT / "runs" / rid / "eval-t30.json").read_text())["results"]
ok(
    sorted(r["agent"] for r in res) == [1, 2, 3, 4, 6, 7, 8, 9],
    "eval quizzes the 8 non-scripted cells only (agent 5 = cell 4 skipped)",
)

# 3. fail loud
for name, toml in [
    (
        "bad template",
        'agent = "echo"\n[cells.4]\nagent = "scripted"\n[cells.4.scripted]\nprogram = [{from = 1, out = ["zz", "-", "-", "-"]}]\n',
    ),
    (
        "too long",
        'agent = "echo"\n[cells.4]\nagent = "scripted"\n[cells.4.scripted]\nprogram = [{from = 1, out = ["{id}<THIS TEXT IS FAR TOO LONG>", "-", "-", "-"]}]\n',
    ),
    ("cell outside grid", 'agent = "echo"\n[cells.9]\nagent = "scripted"\n'),
    (
        "unknown perturbation",
        'agent = "echo"\n[[perturb]]\ncell = 1\naction = "explode"\nfrom = 3\n',
    ),
]:
    p = run_sim(toml, f"p1test-bad-{name.replace(' ', '-')}", 3)
    ok(
        p.returncode != 0 and "config:" in p.stderr,
        f"fails loud on {name} ({p.stderr.strip().splitlines()[-1][:90] if p.stderr.strip() else 'no message'})",
    )
print("ALL PASS")
