# P0 results (updated 2026-11-13, Sol 3 seeds, founder and sham complete) — replication of erz0r/fourfold

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

Zero-information floors (quiz at tick 0): cued 0.089 on seeds 1001, 1002 and 1003; no-cue 0.046 (1002), 0.081 (1003).

Scripted-cell reference levels on the same scorer (a scripted agent built separately, not in this repo yet;
re-run here on seeds 1001 and 1002, dotted lines in `figures/p0_eval.png`): an answer that knows nothing scores 0.144,
one ID + port exchange with each neighbor 0.636, and the scripted cell 1.000 from tick 4. Of our 20 valid 50-tick runs,
one is above 0.636 (Sol no-cue 1003, 0.881) and six end below 0.144 (Qwen ×3, Sonnet ×2, Opus cued 1003).

## Follow-up (P1_founder, 3 seeds; `analysis/founder_readout.tsv`)
One scripted cell sent erin's "ECHO Qj NOW!" at t6–12. All three runs valid (95.1/98.2/96.2% error-free).

| seed | composed own English (of 8) | still at t30–50 | first composed | eval, founder | eval, same cells without founder | far IDs heard per cell |
|---|---|---|---|---|---|---|
| 1001 | 6 | 5 | t14 | 0.558 | 0.287 | 3.4 |
| 1002 | 6 | 4 | t11 | 0.230 (0.263 over the 7 answered) | 0.324 | 2.0 |
| 1003 | 8 | 8 | t9 | 0.540 | 0.302 | 3.6 |

**Verdict (frozen rule): a founder is enough for adoption** (R2 ≥ 4/8 and R3 in 3 of 3 seeds). The score rose on two
seeds and not on the third: seed 1002 adopted English (6/8) and scored below its no-founder pair (count 0.54,
arrangement, position and map all 0.00). One quiz answer in 1002 was lost to a Codex transport error and counts as 0.
So English spreading does not by itself raise the score. Relaying is a partial account at best: 1002 heard 2.0 far IDs
per cell, above the no-founder runs (0.1–1.0) and above erin's run (1.8, score 0.60), yet scored 0.23; over these six
runs rho(far heard, score) is 0.37. Caveat on 1003: its no-founder pair found English unaided at t24.

**Sham-founder control (seed 1001, n = 1; frozen reading: the scripted cell alone does not produce the effect).** The
same scripted cell sending only hex frames, no English: eval 0.235 over the 8 Sol cells (founder 0.558, no scripted
cell 0.287), far IDs heard per cell 0.62 (founder 3.38, no scripted cell 1.00), map 0.00. Valid, 96.4% error-free.
So on seed 1001 the rise came with the English message, not with swapping in a scripted cell. One sham cell wrote
English unaided at t42 ("ECHO EXACT INPUT"); one neighbor relayed it and it went no further by t50.

## Not yet done
A third bare-API seed (1003); framed-Sol check; quiz repeated over time. Raw run logs are not in the repo.
