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
