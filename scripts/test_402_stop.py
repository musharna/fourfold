"""test_402_stop: an out-of-credit reply (HTTP 402) from the provider stops the run at that tick.

what it does   runs sim.py (agent = llm) against a local mock provider on a port the OS picks.
               1 positive control: every call answered → 3 ticks on disk, exit 0.
               2 partial 402 (every third call fails, as on 2026-11-10 when 1-5 of 9 agents failed per tick):
                 exit nonzero after tick 1, "402 Payment Required" in the message, exactly 1 tick on disk.
when to use    after any change to sim.py's stop rules or the llm agent's error text.
must pass      both; case 2 was seen to fail on the pre-fix stop rule (the run went on to tick 3).
"""

import http.server
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
GOOD = "".join(f"<q{i}>{'0' * 31}{i}</q{i}>" for i in range(4)) + "<log>ok</log>"


def serve(fail_every: int):
    n, lock = [0], threading.Lock()

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers.get("content-length", 0)))
            with lock:
                n[0] += 1
                fail = fail_every and n[0] % fail_every == 0
            body = (
                {"error": {"message": "insufficient credits", "code": 402}}
                if fail
                else {"choices": [{"message": {"content": GOOD}}], "usage": {}}
            )
            self.send_response(402 if fail else 200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def run(run_id: str, fail_every: int):
    shutil.rmtree(ROOT / "runs" / run_id, ignore_errors=True)
    srv = serve(fail_every)
    with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
        f.write(f'agent = "llm"\nticks = 3\n[llm]\nbase_url = "http://127.0.0.1:{srv.server_port}/v1"\nmodel = "x"\nretries = 0\n')
    p = subprocess.run([PY, "sim.py", "--config", f.name, "--run-id", run_id], cwd=ROOT, capture_output=True, text=True, timeout=120)
    srv.shutdown()
    path = ROOT / "runs" / run_id / "ticks.jsonl"
    ticks = [r for r in map(json.loads, path.read_text().splitlines()) if r.get("type") == "tick"] if path.exists() else []
    shutil.rmtree(ROOT / "runs" / run_id, ignore_errors=True)
    return p, ticks


def ok(cond, msg):
    if not cond:
        sys.exit(f"FAIL: {msg}")
    print(f"PASS: {msg}")


p, ticks = run("t402-ok", 0)
ok(p.returncode == 0 and len(ticks) == 3, f"control: all calls answered → 3 ticks, exit 0 (rc {p.returncode}, {len(ticks)} ticks) {p.stderr[-300:]}")
ok(all(not a["errors"] for r in ticks for a in r["agents"]), "control: no agent errors")

p, ticks = run("t402-partial", 3)
failed = sum(bool(a["errors"]) for r in ticks[:1] for a in r["agents"])
ok(len(ticks) >= 1 and 0 < failed < 9, f"partial 402: tick 1 has some but not all agents failing ({failed}/9)")
ok(p.returncode != 0 and len(ticks) == 1, f"partial 402: run stops after tick 1 (rc {p.returncode}, {len(ticks)} ticks on disk)")
ok("402 Payment Required" in (p.stderr + p.stdout), "partial 402: stop message names the 402")
