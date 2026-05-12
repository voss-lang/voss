---
phase: M2
plan: 05
status: complete
date: 2026-05-11
files_modified:
  - voss/harness/agent.py (_compose_cognition_prompt, _compose_prior_context_block, COGNITION_BUDGET_TOKENS, _default_token_count, run_turn prepend + prior_context kwarg)
  - voss/harness/render.py (show_cognition + show_cognition_overflow + show_warning on Protocol + 3 renderers; cognition_loaded + cognition_overflow + warning NDJSON events)
  - voss/harness/cli.py (_run_repl loads CognitionBundle once via cognition.load(cwd, token_count=…); passes cognition=bundle + prior_context to run_turn; prior_context one-shot consumption; resume_cmd seeds prior_context from record.runs[-1])
  - tests/harness/test_repl_cognition.py (3 unskipped + new helpers)
  - tests/harness/test_agent_integration.py (test_turn_injects_cognition + test_resume_injects_prior_run_context unskipped)
tests_added: 5 (3 renderer + 2 integration)
tests_total: 215 passed + 4 skipped
agent_py_edited: true
---

# M2-05 Summary · Cognition Auto-Injection + Resume Rehydration

## 1. System-prompt composition order

```
sys_prompt = "\n\n".join(filter(None, [
    cognition_text,        # cognition.load(cwd) → architecture + constraints
    prior_context_text,    # only on resume (first turn) — most-recent RunRecord
    PLAN_SYSTEM,           # M1 baseline planner instructions
]))
```

`run_turn` builds `messages=[{"role":"system","content":sys_prompt}, {"role":"user","content":user_prompt}]`. Both prepend blocks degrade to empty strings when their inputs are missing → backward-compatible with M1-style turns.

## 2. 6k truncation rule (constraints first)

```python
COGNITION_BUDGET_TOKENS = 6000

body = "# Project cognition\n\n## Architecture\n\n{arch}\n\n## Constraints\n\n{bullets}"
if token_count_fn(body, model=model) > 6000:
    renderer.show_cognition_overflow(architecture_tokens=measured, budget=6000)
    body = "# Project cognition\n\n## Architecture\n\n{arch}\n\n(constraints truncated due to budget)"
```

Architecture **always** stays intact; constraints drop entirely on overflow. `_default_token_count` wraps `litellm.token_counter`; on import/runtime failure it falls back to a 4-chars-per-token approximation AND emits `show_warning("cognition token-count unavailable; budget unchecked")` (T-M2-20 mitigation — no silent skip).

## 3. Renderer surface additions

| Method | Tty | Plain | Json |
|--------|-----|-------|------|
| `show_cognition(architecture_tokens, constraints_count, plans_loaded=0, decisions_loaded=0)` | dim status `cognition: architecture (X.Xk) + N constraints[ + P plans + D decisions]`; suppressed when `quiet=True` | stderr `cognition: arch=Ntok constraints=N` | NDJSON `{type:"cognition_loaded", architecture_tokens, constraints_count, plans_loaded, decisions_loaded}` |
| `show_cognition_overflow(architecture_tokens, budget=6000)` | yellow `⚠ architecture.md is N tokens (over 6000 budget) — /analyze can rewrite a tighter digest` | stderr `cognition overflow: N > 6000` | NDJSON `{type:"cognition_overflow", architecture_tokens, budget}` |
| `show_warning(msg)` | yellow `⚠ {msg}` | stderr `warning: {msg}` | NDJSON `{type:"warning", message}` |

`TtyRenderer` gained `quiet: bool = False` field for a future `--quiet` flag. Protocol gained all three method signatures.

## 4. `prior_context` dict shape (consumed by `resume`)

Source: `record.runs[-1]` (latest finalized RunRecord, persisted as dict via `dataclasses.asdict` in `_run_repl`). Fields read by `_compose_prior_context_block`:

```python
{
    "goal": str,                       # RunSemantics.goal
    "plan": {"rationale": str, ...},   # full Plan.model_dump() snapshot
    "decisions": [{"title": str, "body": str, "confidence": float}, ...],
    "follow_ups": [str, ...],
    "risks": [str, ...],
}
```

Rendered block:

```
Prior context (most-recent turn):
- goal: <goal>
- plan rationale: <plan.rationale>
- decisions:
  - <title 1>
  - <title 2>
- follow_ups:
  - <item>
- risks:
  - <item>
```

Missing keys / empty lists collapse to `(none)`. `prior_context=None` returns `""`.

**One-shot consumption.** `_run_repl` accepts `prior_context` kwarg and sets it to `None` immediately after the FIRST `run_turn` call — subsequent turns in the same REPL session never re-inject the block. `resume_cmd` is the only caller that seeds it (`prior = record.runs[-1] if record.runs else None`).

## 5. How to disable auto-inject

Pass `cognition=None` to `run_turn`. Two production sites already use this:

- **`/analyze` bootstrap** (`voss/harness/skills/analyze.py`): passes `cognition=None` explicitly so the bootstrap turn isn't fed its own (possibly-stale or missing) architecture.md.
- **Tests** that don't want injection (e.g. existing M1 FakeProvider tests) — `cognition` defaults to `None`, so they're unchanged.

`cli._run_repl` always passes the loaded bundle for real chat turns. If `.voss/architecture.md` is missing, `cognition.load` returns `CognitionBundle(initialized=False)` and `_compose_cognition_prompt` short-circuits to `""` — no prepend, no `show_cognition` call.

## 6. Test additions

| File | Tests | Notes |
|------|-------|-------|
| `tests/harness/test_repl_cognition.py` | 3 unskipped | `test_cognition_status_line_tty` (rich Console → StringIO capture), `test_cognition_loaded_ndjson_event` (capsys NDJSON parse), `test_cognition_overflow_truncates_constraints` (stub token counter + JsonRenderer event assertion + "## Constraints" absent + "constraints truncated" suffix present) |
| `tests/harness/test_agent_integration.py` | 2 unskipped | `test_turn_injects_cognition` (asserts `MODULE MAP HERE` + `forbid: eval` both precede `You are Voss` in system content); `test_resume_injects_prior_run_context` (asserts goal/decision/follow_up/risk strings in system content) |

Suite: **215 passed + 4 skipped** (was 210 + 8).

## 7. Threat dispositions

| Threat   | Disposition |
|----------|-------------|
| T-M2-17 | Accept — architecture.md is committed content; user responsibility for secrets in it. Same posture as M1 user-prompt passthrough. |
| T-M2-18 | Mitigate — 6k budget enforced; constraints truncate first; `cognition_overflow` event + user hint; architecture preserved so turn proceeds. |
| T-M2-19 | Accept — prior_context produced by same agent in same project; flagged for future "agent-vs-agent" review. |
| T-M2-20 | Mitigate — `_compose_cognition_prompt` wraps `token_count_fn` in `try/except`; on failure emits `show_warning` and prepends architecture unchecked (never silent). |

## 8. Handoff to M2-06

- Drift hint surface (`test_drift_hint_printed_non_blocking`) still skipped (`reason="Wave 4 — pending plan M2-06"`).
- Renderer `show_warning` slot now exists — M2-06 drift hint can use it.
- `cognition.load` is the single REPL-boot entry point; M2-06 doctor adds rows reading the same bundle.
