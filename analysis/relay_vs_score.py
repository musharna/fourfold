"""relay_vs_score: exploratory (post hoc, 2026-11-10) — does the eval score track relaying seen in port traffic.

what it does   per run, over the non-scripted cells, from ticks.jsonl + the true wiring in meta:
                 sent       other cells' IDs that ever appear in the cell's own outputs
                 far heard  non-neighbor IDs that ever appear in the cell's inputs (only relaying can deliver these)
               against the cell's eval-t50 total; prints run means and the run-level Spearman rho.
when to use    reading founder / cue results; usage: relay_vs_score.py <run id>... ("sol-50" = erin's example run).
must pass      nothing gated: IDs are random 32-bit values (words_vs_acts.py's absent-ID null is 0 in every run).
"""
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def sp(x,y):
    def rk(v):
        s=sorted(range(len(v)),key=lambda i:v[i]); r=[0]*len(v); i=0
        while i<len(s):
            j=i
            while j+1<len(s) and v[s[j+1]]==v[s[i]]: j+=1
            for k in range(i,j+1): r[s[k]]=(i+j)/2
            i=j+1
        return r
    a,b=rk(x),rk(y); ma,mb=st.mean(a),st.mean(b); den=(sum((u-ma)**2 for u in a)*sum((u-mb)**2 for u in b))**.5
    return sum((u-ma)*(w-mb) for u,w in zip(a,b))/den if den else float("nan")
tab=[]
for rid in sys.argv[1:]:
    d=ROOT / "examples" / "sol-50" if rid == "sol-50" else ROOT / "runs" / rid
    rows=[json.loads(l) for l in open(d/"ticks.jsonl") if l.strip()]
    meta=next(r for r in rows if r.get("type")=="meta"); T=[r for r in rows if r.get("type")=="tick"]
    ags=meta["agents"]; ids=[a["id"] for a in ags]; seed={a["id"]:a["seed"].lower() for a in ags}
    nb={a["id"]:{l["agent"] for l in a["links"] if l} for a in ags}
    scripted={int(k) for k in (meta["config"].get("cells") or {})}
    far_heard={i:set() for i in ids}; relayed={i:set() for i in ids}; first_far=None; relay_ticks=0
    for r in T:
        anyrelay=False
        for k,rec in enumerate(r["agents"]):
            i=ids[k]
            for v in rec.get("inputs") or []:
                v=v.lower()
                for b in ids:
                    if b!=i and b not in nb[i] and seed[b] in v:
                        far_heard[i].add(b)
                        if first_far is None: first_far=r["t"]
            if k in scripted: continue
            for v in rec.get("outputs") or []:
                v=v.lower()
                for b in ids:
                    if b!=i and seed[b] in v: relayed[i].add(b); anyrelay=True
        relay_ticks+=anyrelay
    ev={a["agent"]:a["total"] for a in json.load(open(d/"eval-t50.json"))["results"]}
    off=min(ev)-min(ids) if len(ev)==9 else None
    cells=[i for k,i in enumerate(ids) if k not in scripted]
    key=(lambda i:i) if set(cells)<=set(ev) else (lambda i:i+1)
    sc=[ev[key(i)] for i in cells]; fh=[len(far_heard[i]) for i in cells]; ro=[len(relayed[i]) for i in cells]
    tab.append((rid,st.mean(ro),st.mean(fh),st.mean(sc)))
    print(f"{rid:24s} others' IDs sent/cell {st.mean(ro):.2f} | far IDs heard/cell {st.mean(fh):.2f} (first t{first_far}) | score {st.mean(sc):.2f} | within-run rho(far heard, score) {sp(fh,sc):+.2f}")
o=[t for t in tab if t[0]!="sol-50"]
print(f"run-level, ours n={len(o)}: rho(sent, score) {sp([t[1] for t in o],[t[3] for t in o]):.2f}; rho(far heard, score) {sp([t[2] for t in o],[t[3] for t in o]):.2f}")
