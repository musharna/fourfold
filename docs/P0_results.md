# P0 results (updated 2026-11-10, Sol 3 seeds complete) — replication of erz0r/fourfold

Prereg: `prereg/P0.md` (frozen @89dfc67; deviations 1–10). Tables: `analysis/p0_readout.tsv`, `analysis/r3_words_acts.tsv`.
Figures: `figures/p0_eval.png`, `figures/p0_refusals.png`, `figures/p0_neighbors.png`.

## Verdicts (frozen rules)
| question | status | basis |
|---|---|---|
| Replication (Sol cued, codex route) | **NOT REPRODUCED** (3/3 valid) | text adopted 9/9 in 1 of 3 seeds (rule needs 2): seed 1003 first text t24, all nine by t29; seeds 1001/1002 0/9. Eval 0.288/0.308/0.298 vs bar 0.289 (floor 0.089 + 0.20) |
| Cue (Sol, codex route) | **MIXED** by the adoption rule (cued 1/3, no-cue 0/3) | eval no-cue 0.570/0.594/0.881 (mean 0.68) vs cued mean 0.30: higher on every seed |
| Qwen3.5-9B capability | **CANNOT** (3/3 valid) | eval 0.086–0.089 = floor 0.089; text 0/9 |
| Sonnet 5.5 | cued n=2 valid: no emergence, at floor (0.10/0.12 vs 0.089); no-cue 0/6 valid ⇒ no cue verdict | refusals |
| Opus 5.5 (+ neutral line, dev. 8) | cued 3/3 valid: eval 0.214/0.195/0.132 vs own floor 0.108/0.129/0.122; text 0/9 | |

## What stands out
1. **Sol scores higher without the evaluation cue on all three seeds**: 0.57/0.59/0.88 vs 0.29/0.31/0.30.
   Cued cells learn their own wiring (0.75–0.92) but never the grid (map score 0.00 in all 5 cued runs, both
   routes). No-cue cells score 0.31–0.89 on the map and name 28–48 non-neighbor IDs in their final notes
   (cued: 0–8), so they relay what they hear. Erin's cued run (0.597, map 0.30) looks like our no-cue runs.
2. **English appeared in 3 of 5 cued Sol runs and 0 of 3 no-cue runs.** Codex seed 1003: "WHO? ID=38b1f9a3" at
   t24, "ACK! ID=…" at t25, all nine cells by t29 (erin: t6 → t14). Bare API (T_text stage 2): 5/9 from t41 and
   6/9 from t12. Codex seeds 1001/1002: structured hex only. Route difference 2/2 vs 1/3 is Fisher p = 0.4, so
   "codex never writes text" is withdrawn (`docs/T_text_results.md`). Text did not raise eval (0.298 with it).
   Every Sol cell heard every neighbor's ID (24/24 links) in all runs.
3. **Claude hears fewer neighbors**: neighbor IDs heard Opus 9–14/24, Sonnet 3–8/24, Qwen 0–8/24.
4. **Opus without the cue talks in English** ("ack both. p3=0", "good day too :)"; 5/9 agents from t9; eval 0.239)
   but that run is VOID: ~20% of turns refused (descriptive only, dev. 10).
5. **Safeguard refusals are the Claude bottleneck.** 1,224 refused agent-turns (~4,900 flagged requests) before the
   fix. No unsafe content found in 7,560 agent records; trigger = security-sounding vocabulary the agents invent
   ("payload" ~4.3k, "injection" ~950). One neutral context line (dev. 8) cut cued Opus to 1–3%; no-cue stays ~20%.
   Removing the eval cue raises refusals in every Claude arm (fig. `p0_refusals.png`).

## Validity (prereg: VOID under 90% error-free agent-ticks)
All six codex Sol runs are valid: 93.3–97.3% error-free. Their only errors are usage-limit ticks where every
call failed and no state changed (1–3 per run); without those ticks, 99.3–100%.

## Not yet done
Zero-information floors for the two 1003 runs (queued; the prereg floor is seed 1001); a third bare-API seed (1003,
needs ~$8 OpenRouter credit); framed-Sol check; redact the account email in
`runs/p0-opus-framed-nocue-1001/ticks.jsonl` before anything is published.
