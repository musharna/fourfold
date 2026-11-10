# T_text results: why our Sol cells never write ASCII (API half, 2026-11-10)

Prereg: `prereg/T_text.md`. Data: `analysis/t_text/calls.jsonl`, `summary.tsv`. 240/240 calls valid,
all served by OpenAI via OpenRouter, $3.82.

Texting = any output passes `is_text(L=10)`, out of 20 calls per cell:

| arm | S1 founder (erin t6) | S2 contagion (erin t7) | S3 ours (t6) |
|---|---|---|---|
| A-bare (erin's exact request) | 1 | 20 | 0 |
| A-bare-low (+ verbosity low) | 0 | 20 | 0 |
| A-scaf-low (codex replica) | 0 | 20 | 0 |
| A-scaf-med | 0 | 20 | 0 |

- **Inventing English is rare even at erin's founder moment:** 1 of 80 S1 calls across all arms.
  The one hit was A-bare, writing "ECHO db06f745 Qj" with the log line "deliberately changes the frame format".
  So her run drew a roughly 1-in-20 event (or rarer), not a behavior her setup reliably produces.
- **Copying is universal:** 80/80 S2 calls put text on an output, under every arm, including the codex
  replica with low verbosity. If a founder appears, text spreads.
- **Verbosity and scaffolding:** not supported at S1 (prereg Fisher, p = 1). Power caveat: at rates
  of 0–5%, N = 20 cannot separate them, so this is "no large effect", not "no effect".
- **Exploratory, not preregistered:** at S2, replies that write their own new English (beyond relaying
  the incoming packet) were bare 13/40 vs scaffold 7/40 (Fisher two-sided p ≈ 0.19). This hints that
  scaffolding dampens composition. It is not significant.
- **Our states:** 0/80 at S3. Our histories are not ripe for invention on any route.

**Current reading: H-chance.** Text needs a rare founder event, and then copying is near certain.
Our 5 runs with none are consistent with that. Still OPEN: the codex half (C-low and C-med, which test
H-serve and H-copy on our actual route), set to run Thu 2026-11-12 20:28 EST.
