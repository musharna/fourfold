"""golden_hash: content hash of a run's ticks.jsonl with wall-clock fields removed (time, created, run_id, latency).
use: regression check that a sim.py change leaves default behavior byte-identical (echo agent, fixed world seed)."""
import hashlib, json, sys
for p in sys.argv[1:]:
    rows = [json.loads(l) for l in open(p)]
    for r in rows:
        for k in ("time", "created", "run_id"):
            r.pop(k, None)
        for a in r.get("agents", []):
            if isinstance(a, dict):
                a.pop("latency", None)
    print(p, len(rows), hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:16])
