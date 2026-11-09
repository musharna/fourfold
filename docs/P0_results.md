# P0 results (2026-11-09) — replication of erz0r/fourfold

Prereg: `prereg/P0.md` (frozen @89dfc67; deviations 1–10). Tables: `analysis/p0_readout.tsv`, `analysis/r3_words_acts.tsv`.
Figures: `figures/p0_eval.png`, `figures/p0_refusals.png`, `figures/p0_neighbors.png`.

## Verdicts (frozen rules)
| question | status | basis |
|---|---|---|
| Replication (Sol cued) | **OPEN** — 1 of 3 seeds run | seed 1001: eval 0.288 vs floor 0.089 (+0.199; bar +0.20 missed by 0.001), ASCII text 0/9 |
| Cue (Sol) | **OPEN** — n=1 per arm | no-cue 0.570 (+0.48, center agent 1.0) vs cued 0.288; text 0/9 in both |
| Qwen3.5-9B capability | **CANNOT** (3/3 valid) | eval 0.086–0.089 = floor 0.089; text 0/9 |
| Sonnet 5.5 | cued n=2 valid: no emergence, at floor (0.10/0.12 vs 0.089); no-cue 0/6 valid ⇒ no cue verdict | refusals |
| Opus 5.5 (+ neutral line, dev. 8) | cued 3/3 valid: eval 0.214/0.195/0.132 vs own floor 0.108/0.129/0.122; text 0/9 | |

## What stands out
1. **Sol does best without the evaluation cue** (one seed per arm): 0.57 vs 0.29, close to erin's 0.597. Opposite
   of "emergence is prompt-cued". Needs seeds 1002/1003 before it is more than a lead.
2. **No ASCII text in our Sol runs.** Both used structured hex messages (IDs, counters); every cell heard every
   neighbor's ID (24/24 links), as in erin's run. Erin's text protocol (t6/t14) did not reproduce on seed 1001.
   Our Sol runs go through `codex exec` (~10.8k tokens of scaffolding per call), not the raw API (dev. 2).
3. **Claude hears fewer neighbors**: neighbor IDs heard Opus 9–14/24, Sonnet 3–8/24, Qwen 0–8/24.
4. **Opus without the cue talks in English** ("ack both. p3=0", "good day too :)"; 5/9 agents from t9; eval 0.239)
   but that run is VOID: ~20% of turns refused (descriptive only, dev. 10).
5. **Safeguard refusals are the Claude bottleneck.** 1,224 refused agent-turns (~4,900 flagged requests) before the
   fix. No unsafe content found in 7,560 agent records; trigger = security-sounding vocabulary the agents invent
   ("payload" ~4.3k, "injection" ~950). One neutral context line (dev. 8) cut cued Opus to 1–3%; no-cue stays ~20%.
   Removing the eval cue raises refusals in every Claude arm (fig. `p0_refusals.png`).

## Not yet done
Sol seeds 1002/1003 (both arms; ~4–6 Plus windows); framed-Sol check (does the neutral line move Sol?);
scan run logs for the injected account email before anything is published.
