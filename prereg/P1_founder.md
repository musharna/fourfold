# P1_founder: is a founder enough for our Sol cells to adopt English? (frozen 2026-11-10, before any call)

**Why.** T_text (`docs/T_text_results.md`): invention is ~1% per call even at erin's founder moment; relay of
incoming English is 120/120 on every route. If a founder is all that's missing, planting one should
make our cells adopt English. If not, erin's spread needed something a broadcast can't supply
(a founder that converses).

**Design.** Arm `solcx-founder` (`configs/sol_codex_founder.toml`): the P0 Sol cued arm (codex, effort high,
erin's prompt) with cell 6 (bottom-left corner, erin's founder cell) replaced by a scripted cell:
- t1–5: hex frames `[ID|tick|port|0]` (the framing all Sol cells use);
- t6–12: `ID + "ECHO Qj NOW!"` on every port, erin's founder's exact message (render verified byte-for-byte);
- t13–50: hex frames again, so any English after t12 is written by the 8 Sol cells.
World seeds 1001, 1002, 1003, paired with P0 `solcx-cued` runs of the same seed (identical wiring and IDs, no founder).
Seed 1001 runs first. 1002 and 1003 follow if 1001 is VALID (≥ 90% error-free agent-ticks). The adoption
readout is not used to decide whether to continue.

**Readouts** (`analysis/founder_readout.py`, over the 8 Sol cells):
- R1 relay: cells with any output passing `is_text(L=10)`.
- **R2 adoption (primary):** cells that compose their own English: an output passing `is_text(L=10)` that is
  not a verbatim copy of any input value the cell has seen up to that tick.
- R3 persistence: any composed English from Sol cells in t30–50 (founder silent since t12).
- R4 task: eval mean over the 8 Sol cells vs the same 8 cells in the paired no-founder run (descriptive).

**Predictions.**
- Founder is enough: R2 ≥ 4/8 in ≥ 2 of 3 seeds, and R3 in ≥ 2 of 3 seeds.
- Not enough (the founder must converse): R2 ≤ 1/8 in every seed.
- Anything in between is reported as is, with no verdict.

**Readout controls (must pass before the first run is read):** erin's sol-50 counted the same way (founder
excluded) gives R2 ≥ 7/8 (agents composed "WHO SEES?", "SAW Q3", ...); the echo-agent integration run
(echo cells only relay) gives R1 > 0 and R2 = 0.

**Cost:** ~410 Sol calls per run (~170 Codex credits); queued after Sol 1003 finishes.

## Addendum: sham-founder control (frozen 2026-11-10 18:00, before any sham call; founder seed 1001 already read)
**Seen first:** founder-1001 gave R2 6/8, R3 5 cells, eval 0.558 vs 0.287 paired. Post hoc (`analysis/relay_vs_score.py`):
across our 9 Sol runs the score tracks relaying in port traffic (non-neighbor IDs heard per cell: cued 0.1–1.0 →
0.28–0.31; founder 3.4 → 0.56; no-cue 3.1–5.3 → 0.57–0.88; run-level rho 0.71), not English (9/9 composing in
cued-1003 scored 0.30; no-cue runs have no English).
**Question.** Is the founder effect due to the English message, or to swapping a Sol cell for a scripted one whose
regular frames carry its ID and port number?
**Design.** Arm `solcx-sham` (`configs/sol_codex_sham.toml`): the founder arm with cell 6 sending hex frames on
every tick (dry run: identical to the founder cell outside t6–12, no text). World seed 1001 only (Codex budget),
run id `p0-solcx-sham-1001`; compared with founder-1001 and cued-1001 over the same 8 cells. Replaces T_text stage 3
in the queue (`scripts/codex_queue4.sh`).
**Readouts.** Eval mean over the 8 Sol cells; non-neighbor IDs heard per cell; R1/R2 as above.
**Reading (n = 1, descriptive).** Sham eval ≤ 0.35 and far IDs heard ≤ 1.5 per cell → the scripted cell alone does
not produce the effect. Sham eval ≥ 0.45 → the effect is at least partly the scripted cell, not the English.
In between: no verdict. VOID rule as in P0.
