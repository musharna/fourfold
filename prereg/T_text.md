# T_text: why do our Sol cells never write ASCII text? (frozen 2026-11-09, before any call)

**Observation.** erin's sol-50: agent 7 at t6 sends `ID + "ECHO Qj NOW!"`, copied by 9/9 by t14.
Our 5 Sol runs (codex route): same `[ID|tick|idx|payload]` hex framing, ASCII only as 4-byte tags, 0/9 text.
Rendered system prompt word-identical (line wrap only); same model and effort; 0 shell commands in any run.

**Measured differences of our route** (`analysis/codex_capture/default.json`, captured via a local mock
provider, same flags as the runs): `text.verbosity = "low"`; our system prompt sent as a *developer*
message; ~9.5k tokens extra (exec/wait/request_user_input tools 20k chars, collaboration tools 5.5k,
skills list 6k, multi-agent role 2.7k, environment context); Responses API on the ChatGPT backend.
Flags can set verbosity=medium and cut only ~20% of the rest (`stripped.json`).

## Hypotheses
- **H-verb** low verbosity suppresses the prose idea.
- **H-scaf** codex's coding-agent scaffolding suppresses it.
- **H-serve** ChatGPT-backend serving differs from the API (snapshot/defaults).
- **H-chance** nothing suppresses it: invention is a rare, history-dependent founder event.
- **H-copy** our route also fails to *copy* text when a neighbor sends it.

## Design: replay single agent-ticks, N = 20 calls per arm x state
States (stored prompts replayed byte-for-byte; erin's states use her stored system template + seed):
- **S1 founder**: sol-50 agent index 6, t6 (the tick it invented ECHO).
- **S2 contagion**: sol-50 agent index 3, t7 (input p2 carries "ECHO Q0 NOW!").
- **S3 ours**: p0-solcx-cued-1002 agent index 6, t6.

Arms (all gpt-6.1-sol, reasoning effort high):
| arm | route | request |
|---|---|---|
| C-low | codex (Plus) | exactly as in the runs |
| C-med | codex (Plus) | + `model_verbosity=medium` |
| A-bare | OpenRouter | erin's request: system + user, no verbosity (default medium) |
| A-bare-low | OpenRouter | A-bare + verbosity low |
| A-scaf-low | OpenRouter | codex replica: developer msgs + codex blocks + tools from default.json, verbosity low (approximation: chat completions, so tool namespaces and the freeform `exec` grammar are flattened to plain functions, grammar text kept in the description) |
| A-scaf-med | OpenRouter | A-scaf-low with verbosity medium |

**Readout (per call):** text = any of q0–q3 passes `emergence.is_text(L=10)` after `sim.parse_response`.
Secondary: output tokens; S2 exact copy of the incoming ECHO value.
**Scorer control (must pass before any call):** erin's stored replies at S1 and S2 score text=True;
our stored reply at S3 scores False. The replay tool exits if not.

## Decision rules (Fisher exact two-sided, p < 0.05, N = 20 vs 20)
- H-verb supported: C-med > C-low at S1, and A-bare > A-bare-low at S1.
- H-scaf supported: A-bare-low > A-scaf-low at S1 (or A-bare > A-scaf-med).
- H-serve supported: A-scaf-low > C-low at S1.
- H-copy supported: C-low < A-bare at S2.
- H-chance supported: C-low at S1 >= 5/20 and none of H-verb/H-scaf/H-serve supported; corroborated if
  A-bare at S3 <= 2/20 (our histories are not "ripe" on any route).
Causes can combine; every comparison is reported with counts. A result that needs a threshold moved is a fail.
If no API credit: only C arms run; H-verb is then codex-side only, H-scaf and H-serve stay OPEN.

**Stage 2 (decided after, not frozen here):** a full 50-tick run with the identified fix.
**Cost:** codex 120 calls (~0.3 Plus window); API 240 calls, ~$7 at $2/$10 per M (live 11-09).
**Dropped:** effort arm (erin and ours both "high"; the output-token gap is read off the verbosity arms).

## Stage 2 (frozen 2026-11-10, before the first call): trajectory-level route test
Single-call replay found no route difference, but erin's README reports text in both of her 128-bit Sol runs
(sol-50; byte_ban run, high-bit ASCII from t21) against 0 of our 5 codex runs. Full runs on erin's route
(`configs/sol_api.toml`: bare chat completions, effort high, no verbosity, no scaffold, OpenRouter pinned to OpenAI),
world seed 1001 first (paired with p0-solcx-cued-1001), then 1002 if funded. Cost cap $5.50 per funding step;
a capped run resumes to t50 when credit is added.
Readouts: cells with text output (is_text L=10), first text tick, cells composing their own text
(`founder_readout.readout`, no founder), eval vs the paired codex run.
Reading (descriptive, n <= 2): text in an API run when the paired codex run had none favors a trajectory-level
route effect. No text in API runs by t30 favors the "rare founder" reading.

## Stage 3 (frozen 2026-11-10 03:00, before the first call): does codex's low verbosity explain the gap?
Seed 1001 pair: API route text 5/9 (founder t41), codex route 0/9. Codex cells wrote ~25% shorter logs from t1
(31 vs 43 words/tick t1-5; erin 45) and tried fewer distinct port values (461 vs 597, t1-40).
Run `configs/sol_codex_verbmed.toml` (codex + model_verbosity=medium), world seed 1001.
Readouts: log words/tick (t1-5, t1-40), distinct outputs t1-40, text cells and first text tick, eval.
Reading (descriptive, n = 1): logs and distinct outputs move to the API values AND text appears → verbosity is the dial.
Logs move but no text → verbosity explains the style gap but not the text (scaffolding or chance).
Logs don't move → verbosity isn't what shortens them.

**Stage 3 addendum (2026-11-10 03:25, before the first call; from the session audit):** two readouts added.
(1) Median reasoning tokens per call (t1-11 and t1-50). Codex calls reason about half as much as API calls at the
same nominal effort "high" (full runs, cued: 223-242 vs 421-458; erin 512; same request body replayed: codex
394-446 vs API+scaffold 788-801), and single-call verbosity=medium did not raise it (394 vs 446). So a third
reading is possible: logs lengthen, reasoning stays low, no text → the serving path's reasoning budget is still
a live suspect and this run cannot test it.
(2) Error-free fraction is reported with and without all-agent usage-limit ticks (a freeze tick changes no state).
**Stage 2 deviation, logged late:** API-1001 ticks 21-30 ran with 1-5 agents failing on HTTP 402; they were cut and
the run resumed from t20 (backup kept). The discarded ticks held no text (checked 11-10). Paired counts so far:
2/2 API vs 0/2 codex is Fisher p = 0.33; the t30 rule above was met on seed 1001 (first text t41).

## Stage 4 (frozen 2026-11-10 03:24, before the first call): does less reasoning suppress text on the API route?
Run `configs/sol_api_rmed.toml` (= `sol_api.toml` with reasoning effort "medium"; nothing else changed), world seed
1002, 30 ticks, run id `p0-solapi-rmed-1002`. Pairs: `p0-solapi-cued-1002` (effort high: first text t12, 6/9 cells
by t17) and `p0-solcx-cued-1002` (codex: 0/9).
Calibration: after tick 3 the median reasoning tokens per call must be <= 325 (codex cued-1002 t1-3: 271; API
high t1-3: 340). If above, stop, keep the file as a discarded pilot, and rerun as `p0-solapi-rlow-1002` with effort
"low"; no further levels, whatever "low" gives is reported.
Readouts: reasoning tokens (t1-3, t1-30), log words/tick, text cells and first text tick (is_text L=10), composing
cells (`founder_readout`, all 9 cells).
Reading (descriptive, n = 1): no text by t30 with reasoning at codex level → consistent with the reasoning budget
being the dial (not proof: one seed, and bare 1001 took 41 ticks). Text by t30 → less reasoning alone does not
suppress text; suspicion moves to the scaffold or the serving path. Cost: within the $5.50 cap.
