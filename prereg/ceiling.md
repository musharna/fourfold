# Scripted ceiling: what does the interface allow, and how early?

Frozen 2026-11-13 01:29 EST (from `date`), before any agent code existed and before any scored run.

This was frozen in a separate working directory, before the agent was written, so this repo's history
cannot show the freeze. The text is as frozen except that local paths and file names were replaced with
the ones in this repo.

## Question

In fourfold, nine LLM cells on a 3×3 grid must work out where they are from 128-bit port values
alone. P0 scored them once, after tick 50 (means 0.09–0.88). Nothing says what the interface itself
allows. How early can a cell that already has a shared code reach a perfect quiz score, and does the
scorer ever award 1.0?

## What I had seen before freezing

- The P0 results (model quiz means at tick 50; echo/t0 floors near 0.089).
- The simulator and scorer source (`sim.py`, `eval.py`, unmodified; 40be9dd in this history).
- No scripted-ceiling run existed (checked: the tracked files of this project for a scripted-optimum
  agent).

## The agent and what it is allowed

- A pure function (system prompt text, tick or quiz prompt text) → reply text. It reads nothing
  else: no simulator objects, no memory between calls. All state lives in its `<protocol>` notebook
  under the harness's 400-word cut.
- It differs from the LLM cells in three declared ways: every cell runs the same code (a shared
  protocol from birth); it knows the harness rules (port i is one two-way link, dead ports read
  zero, ticks are synchronous, the world is a rectangular grid of unknown size); it knows the quiz
  format. It is not told the grid's dimensions or anyone's id but its own.
- So this is a ceiling on the interface, not on what an uninformed learner could do.

## Definitions

- **Quiz after tick T**: `eval.ask_all` + `eval.score_agent` on the first T ticks
  (T = 0 is the fresh state). Score = the scorer's `total` (mean of five parts).
- **Seeds**: world seeds 1001, 1002, 1003 (the worlds P0 used) and 1–100. 103 worlds × 9 cells =
  927 quizzes per tick.
- **Wrong claim**: `map_wrong > 0`, or a wiring slot whose claim names a cell or "dead" and scores
  below what a correct claim of that kind would (a wrong id, a wrong port, or dead-vs-live).

## Predictions and pass criteria (thresholds do not move)

- **C1, ceiling at tick 4.** Every one of the 927 quizzes after tick 4 scores exactly 1.0. FAIL if
  any is below.
- **C2, not before.** No world has all nine cells at 1.0 after tick 3; every corner cell is below
  1.0 after tick 3 (the opposite corner is four hops away and information moves one hop per tick).
  FAIL if any corner scores 1.0 after tick 3.
- **C3, never wrong.** Zero wrong claims at every tick 0–12 in every world. FAIL on one.
- **C4, valid and within budget.** Zero harness `errors` on any tick, and no protocol over 400
  words. FAIL on one.
- **C5, stable.** Every quiz after ticks 5–12 scores 1.0.
- **C6, other grid sizes (generality, not optimality).** On 2×2, 2×3, 3×4, 4×4 and 5×5 (seeds 1–20
  each) every cell scores 1.0 by tick 2·(rows + cols), with zero wrong claims on the way. FAIL if
  any cell is below at that tick.

Scores before tick 4 are what this agent achieves, reported as observed; I do not claim they are
the best possible.

## Controls

1. Scorer reachability, independent of my agent: an answer written directly from the world's true
   wiring must score 1.0 for every cell; the same answer with two ids swapped in the map must not.
2. Lost message: the harness's own `silence` perturbation on the center cell at tick 3. Prediction:
   mean after tick 4 is below 1.0, zero wrong claims, and all cells back at 1.0 by tick 6. This is
   the twin that shows C1 can fail.
3. Interface check: the wrapper hands the agent only the two prompt strings; a test asserts the
   agent function's signature and that a call with fresh strings reproduces the logged reply.
4. Denominators: the run fails unless it scored 927 quizzes per tick (180 per size for C6).
5. Truth comes from the simulator's world (`meta["agents"]`) through `eval.score_agent`, never from
   my agent. Deepest shared layer: `sim.build_world` defines the wiring for both; that is the
   definition, not a shared estimate.

## Limits

One harness commit. Text port mode only (128 bits). A scripted cell with a designed code says
nothing about how hard the code is to invent. 1×N grids are out of scope (no unit squares).
