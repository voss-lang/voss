---
phase: E1-eval-substrate
plan: 05
subsystem: testing
tags: [eval, golden, live-proof, codex-oauth, EVSUB-07]

requires: [E1-01, E1-02, E1-03, E1-04]
provides:
  - Live codex-auth golden suite run recorded in .voss/eval/e1-proof/ (path-referenced, gitignored)
  - Runner fixes for codex provider resolution and model field recording
affects: [EVSUB-07, E2+]

tech-stack:
  added: []
  patterns:
    - "Live proof via VOSS_DEV=1 + --auth codex on operator machine"
    - "Judge fallback --judge-model gpt-5.5 when gpt-5.5-mini rejected by codex backend"

key-files:
  created:
    - .planning/phases/E1-eval-substrate/E1-05-SUMMARY.md
  modified:
    - voss/eval/runner.py
    - tests/eval/golden/04-validation/task.toml

key-decisions:
  - "Judge fallback to gpt-5.5 (same as actor) after codex backend rejected gpt-5.5-mini input_text error"
  - "Artifacts path-referenced only — .voss/eval/e1-proof/ is gitignored, not committed"

patterns-established: []

requirements-completed: []

duration: ~16s (live run wall time)
completed: 2026-06-10
verdict: FAIL
---

# E1 Plan 05: Live Golden Proof Summary

**EVSUB-07 FAIL — live codex run produced 6 JSONL rows with gate_pass 3/6 (need ≥5), capped 0/6; edit tasks did not complete**

## Verdict

| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Rows in runs.jsonl | 6 | 6 | PASS |
| gate_pass | ≥5/6 | **3/6** | **FAIL** |
| capped | 0/6 | 0/6 | PASS |
| model ≠ judge_model (default) | per row | both `gpt-5.5` (judge fallback) | WARN |
| Turn cap header | printed before first call | `6 tasks · max 15 turns/task` | PASS |

**EVSUB-07: FAIL** — `requirements-completed` remains empty.

## Live Run

**Command (final attempt):**

```bash
VOSS_DEV=1 .venv/bin/python -m voss.cli eval --auth codex --suite golden -k 1 --out .voss/eval/e1-proof --judge-model gpt-5.5
```

**Judge fallback:** Default `gpt-5.5-mini` was rejected by the codex backend (`input_text` invalid_value error). Re-ran with `--judge-model gpt-5.5`; same-model warning emitted (actor and judge both `gpt-5.5`).

**Run header:** `6 tasks · max 15 turns/task`

**Provider:** `OpenAIOAuthProvider` (codex oauth) — after `_provider_for_eval` fix in `runner.py`

**Artifacts (path-referenced, NOT committed — gitignored):**

- `.voss/eval/e1-proof/runs.jsonl` — 6 rows
- `.voss/eval/e1-proof/summary.md` — gate pass rate 50% (3/6), overall success 0% (0/6)

## Per-Task Results (transcribed from runs.jsonl)

| task_id | gate_pass | capped | model | judge_model | provider | duration_s | success | live | judge_verdict |
|---------|-----------|--------|-------|-------------|----------|------------|---------|------|---------------|
| 01-analyze | false | false | gpt-5.5 | gpt-5.5 | OpenAIOAuthProvider | 4.586 | false | false | skipped |
| 02-plan-only | true | false | gpt-5.5 | gpt-5.5 | OpenAIOAuthProvider | 0.385 | false | false | skipped |
| 03-approved-edit | false | false | gpt-5.5 | gpt-5.5 | OpenAIOAuthProvider | 3.459 | false | false | skipped |
| 04-validation | true | false | gpt-5.5 | gpt-5.5 | OpenAIOAuthProvider | 2.159 | false | false | skipped |
| 05-resume | true | false | gpt-5.5 | gpt-5.5 | OpenAIOAuthProvider | 3.199 | false | false | skipped |
| 06-fetch-summarize | false | false | gpt-5.5 | gpt-5.5 | OpenAIOAuthProvider | 0.212 | false | false | skipped |

**gate_pass:** 3/6 (`02-plan-only`, `04-validation`, `05-resume` = true)

**capped:** 0/6

### Check detail (from JSONL)

| task_id | checks (type → pass) |
|---------|----------------------|
| 01-analyze | `file_exists` → false |
| 02-plan-only | `cmd` → true |
| 03-approved-edit | `file_contains` → true, `file_contains` → true, `cmd` → false |
| 04-validation | `cmd` → true |
| 05-resume | `cmd` → true |
| 06-fetch-summarize | `file_exists` → false, `file_contains` → false |

All rows: `judge_confidence: 0.0`, `cost_usd: null`, `confidence: null`, `run_idx: 0`, `seed: 0`, `voss_version: 0.1.0`, `started_at` 2026-06-10T19:36:27–19:36:41+00:00.

Judge rationales (all `judge_verdict: skipped`):

- 01-analyze, 03-approved-edit, 05-resume: `RuntimeError: OpenAI OAuth stream failed [400]: input_text invalid_value`
- 02-plan-only, 04-validation, 06-fetch-summarize: `RuntimeError: Event loop is closed`

## Blockers Fixed During E1-05 Attempt

1. **`_provider_for_eval`** was calling `get_provider()` instead of building `OpenAIOAuthProvider` from codex auth — fixed in `voss/eval/runner.py`
2. **`model` field was null** when `spec.model` unset — fixed to use `get_config().default_model` via `_record_model`
3. **04-validation check** used `python` not found — changed to `python3` in `tests/eval/golden/04-validation/task.toml`

## Remaining Gap

Agents ran on codex but did not complete enough edit tasks — gates failed on `01-analyze`, `03-approved-edit`, and `06-fetch-summarize`. Total run wall time ~16s suggests turns may end early before agents produce required artifacts.

**Next steps for operator:**

- Re-run live proof after investigating why edit tasks fail (missing files, cmd gate on 03, judge stream errors)
- Consider fixing codex judge `input_text` compatibility so `gpt-5.5-mini` works and actor/judge differ
- Re-attempt EVSUB-07 gate: `gate_pass ≥5/6`, `capped 0/6`

## Deviations from Plan

- Judge model fallback to `gpt-5.5` (same as actor) due to codex backend rejection of `gpt-5.5-mini`
- `gate_pass` 3/6 — below ≥5/6 acceptance threshold

## Verification

```bash
cd /Users/benjaminmarks/Projects/Voss
test -f .voss/eval/e1-proof/runs.jsonl
.venv/bin/python -c "import json; rows=[json.loads(l) for l in open('.voss/eval/e1-proof/runs.jsonl') if l.strip()]; gp=sum(1 for r in rows if r.get('gate_pass')); cap=sum(1 for r in rows if r.get('capped')); print(f'gate_pass={gp}/6 capped={cap}')"
```

**Result:** `gate_pass=3/6 capped=0`

**EVSUB-07 assertion `gp >= 5` FAILS** (3 < 5). Capped assertion passes (0 capped).

## User Setup Required

Codex oauth (`~/.codex/auth.json`) — used successfully after provider fix.

## Next Phase Readiness

- **Blocked on EVSUB-07** — hybrid substrate infrastructure is in place; live agent completion on edit tasks is the gap
- E2+ should not assume ≥5/6 gate_pass proof until a successful re-run

---
*Phase: E1-eval-substrate*
*Completed: 2026-06-10*
*Verdict: FAIL (EVSUB-07)*
