# T_text results: do our Sol cells write ASCII, and does the route matter? (updated 2026-11-10 13:45)

**Bottom line (after full runs, stages 2–4 below):** the question's premise was wrong. Codex cells wrote English
in 1 of 3 cued runs (seed 1003, all nine cells by t29). No route effect is shown: text in 2/2 bare-API vs 1/3
codex cued runs (Fisher p = 0.4). Text looks like a founder event that happens in some runs and not others.

## Stage 1: single-call replay (complete)

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

## Stages 2–4: full runs (cued prompt, 128-bit hex, same wiring per seed)
| run | route | reasoning tokens/call (median, full run) | log words/call (median, t1–40) | cells writing English | first text | eval |
|---|---|---|---|---|---|---|
| erin sol-50 | OpenAI API | 512 | 54.5 | 9/9 | t6 | 0.597 |
| API 1001 | OpenRouter → OpenAI, bare | 458 | 49 | 5/9 | t41 | 0.296 |
| API 1002 | same | 421 | 50 | 6/9 | t12 | 0.280 |
| API 1002, effort medium (stage 4, 30 ticks) | same | 67 | 44 (t1–30) | 0/9 | none | not run |
| codex 1001 | codex exec | 223 | 37 | 0/9 | none | 0.288 |
| codex 1002 | codex exec | 242 | 37 | 0/9 | none | 0.308 |
| codex 1003 | codex exec | 320 | 38 | 9/9 | t24 | 0.298 |

Codex no-cue runs (1001–1003): 0/9 text in all three.

- **Codex 1003 (landed 11-10 11:41):** cell 0 sent "WHO? ID=38b1f9a3" at t24, a neighbor answered "ACK! ID=6774d88e"
  at t25, and all nine cells were composing English by t29 ("ECHO Q0 …", "INPUTS? …", "…:PING").
- **Withdrawn:** "codex never writes text" (it held for 5 runs and failed on the 6th), and with it the audit's
  leading suspect that codex's lower reasoning budget suppresses text. Codex reasons about half as much per call
  as the API (a real, measured difference), and wrote text anyway.
- **Stage 4 stays ambiguous:** effort medium on the API gave no text in 30 ticks, but at 67 reasoning tokens it
  sat far below codex, and bare 1001 needed 41 ticks at full effort.
- **Stage 3 (codex, verbosity medium):** not run yet and no longer needed for the text question. Moved to the end
  of the Codex queue; it would only measure log length.
- **Open:** whether text is less likely per run on codex. 2/2 vs 1/3 cannot tell. A third bare-API seed (1003)
  gives the pair for the run where codex did write text.
- Stage 2 deviation and the stage 4 calibration are logged in `prereg/T_text.md`. OpenRouter is pinned to the
  OpenAI provider; erin called api.openai.com directly.

**Next:** scripted-founder runs (`prereg/P1_founder.md`). Note for reading them: on seed 1003 the no-founder
control itself reaches 9/9 from t24, so a founder effect there can only show as earlier adoption.
