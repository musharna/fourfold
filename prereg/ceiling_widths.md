# Scripted ceiling, part 2: narrow ports

Frozen 2026-11-13 01:47 EST (from `date`), before the multi-tick agent code existed and before any

This was frozen in a separate working directory, before the agent was written, so this repo's history
cannot show the freeze. The text is as frozen except that local paths and file names were replaced with
the ones in this repo.
run at a width other than 128 bits.

## Question

The harness lets a port be 4 to 128 bits wide. The upstream README reports one 4-bit run in which
the models "never found each other in 130 ticks". Is a perfect quiz reachable at each width, and by
which tick?

## What I had seen before freezing

- Part 1 (128 bits): perfect after tick 4 in 103 of 103 worlds.
- The README anecdotes for 4-bit and 8-bit ports. No scripted run at any narrow width existed
  (checked: the output directory of part 1 and the tracked files of this project).

## The agent change

The same code as part 1, with each message spread over as many ticks as it needs. With H hex
characters per port per tick: the id-and-port header takes a = ceil(10 / H) ticks, the neighbor
list b = ceil(24 / H) ticks, and each square F = 32 / H ticks. An all-zero tick between squares
means "nothing to send". Nothing is compressed; this is the plain version.

## Definitions

- **Widths**: 4, 8, 16, 32, 64, 128 bits. **Worlds**: 3×3, seeds 1001–1003 and 1–100 (103).
- **First perfect tick** of a world: the smallest T such that all nine cells score 1.0 at every
  quiz from T to the last tick run (predicted tick + 6).
- **Wrong claim**: as in part 1.

## Predictions and pass criteria

- **D1, when.** First perfect tick = a + b + 2F in every world: 98, 49, 25, 13, 7, 4 for 4, 8, 16,
  32, 64, 128 bits. PASS if every world is at or before the predicted tick; any world later is a
  FAIL. Worlds earlier than predicted are reported, not failed.
- **D2, the README case.** At 4 bits every world is perfect by tick 130. FAIL if any is not.
- **D3, never wrong.** Zero wrong claims at every tick, every width, every world.
- **D4, part 1 unchanged.** At 128 bits the new code gives the same score for every one of the
  45,682 quizzes of part 1 (`scores.csv` byte-identical).
- **D5, valid.** Zero harness errors; no protocol over 400 words.

## A floor that holds for any cell (derived, not tested)

A corner must learn eight random 32-bit ids through two ports of W bits, and an id d hops away
cannot begin to arrive before tick d. With n_d cells at distance ≥ d (8, 6, 3, 1 for d = 1..4):
T ≥ d − 1 + 16·n_d / W for each d. That gives 32, 16, 8, 4, 4, 4 ticks for the six widths. The
gap between this floor and D1 is reported as open.

## Controls

1. Truth still comes from the simulator through `eval.score_agent` (part 1 control 1 rerun).
2. Lost chunk: the center silenced for one tick in the middle of its first square at 8 bits.
   Prediction: at least one world is not all-perfect at tick 49. This shows D1 can fail. Wrong
   claims may appear here; a multi-tick message has no protection against a missing chunk, and that
   is a declared limit, not a criterion.
3. Planted corner case: a world whose ids are edited so that one square's four ids all begin with a
   zero character, which the "all-zero tick = nothing to send" rule cannot carry directly. The
   escape path must deliver it: all nine cells perfect by the end of the run, zero wrong claims;
   and with the escape disabled the same world must fail.
4. Denominators: 103 worlds × 9 cells at every quizzed tick, for each width.

## Limits

Plain encoding only, so the ticks reported are an upper bound on what is needed, not the minimum.
One harness commit, 3×3 only, hex port mode only.
