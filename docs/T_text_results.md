# T_text results: why our Sol cells never write ASCII (complete, 2026-11-10)

Prereg: `prereg/T_text.md`. Data: `analysis/t_text/calls.jsonl`, `summary.tsv`. 360/360 calls valid
(240 OpenRouter, all OpenAI-served, $3.82; 120 codex on Plus after one free reset).

Texting = any output passes `is_text(L=10)`, out of 20 calls per cell:

| arm | S1 founder (erin t6) | S2 contagion (erin t7) | S3 ours (t6) |
|---|---|---|---|
| C-low (codex, as run) | 0 | 20 | 0 |
| C-med (codex, verbosity medium) | 0 | 20 | 0 |
| A-bare (erin's exact request) | 1 | 20 | 0 |
| A-bare-low | 0 | 20 | 0 |
| A-scaf-low (codex replica) | 0 | 20 | 0 |
| A-scaf-med | 0 | 20 | 0 |

**Preregistered verdicts:** all "not supported": H-verb (codex and API), H-scaf, H-serve, H-copy.
H-chance is also "not supported", because its frozen rule assumed codex would invent at S1 at least 5/20 times.
The real rate is far lower than that assumption, so the rule can't pass. I'm not moving the threshold.

**What the data say:**
- **Inventing English is very rare everywhere:** 1 of 120 calls at erin's founder moment (one bare-API
  call: "ECHO db06f745 Qj", log: "deliberately changes the frame format"), and 0/120 at ours. Erin's run
  drew roughly a 1-in-100 event at its ripest moment. No setup was shown to change that rate. At these
  rates N = 20 cannot detect small differences.
- **Picking up English that arrives is universal:** 120/120 at S2, on every route and setup, including real
  codex at low verbosity. Nothing in our setup blocks spread.
- **Exploratory, not preregistered (multiple looks):** at S2, writing *new* English rather than relaying the
  incoming packet: bare API 13/40 vs scaffolded (codex replica + real codex) 12/80, Fisher p ≈ 0.03
  (codex alone 5/40, p ≈ 0.06). Codex's coding-agent scaffolding may halve how often a cell composes its own
  English, while not affecting relay. This is a candidate for its own preregistered test.

**Answer to "what causes it" (revised 11-10 after re-reading erin's README):** no difference was detectable
*at a single call*. Invention is ~1% per call even at erin's best moment, and relay is universal. But erin's README
also reports text in her `byte_ban` Sol run (high-bit ASCII from t21, spreading like plain ASCII). So her setup made
text in both 128-bit Sol runs she describes, versus 0 of our 5. That fits "lucky draw" poorly, and it leaves a
**trajectory-level** route effect open: a small per-call difference (e.g. the exploratory scaffolding effect on
composition) that compounds over 50 ticks. A single-call replay cannot see that. The test that decides it is full
runs on erin's route (bare API), compared with our codex runs.

**Next:** plant a scripted founder in full Sol runs (`prereg/P1_founder.md`) to test whether a founder
alone makes our cells adopt and keep English.
