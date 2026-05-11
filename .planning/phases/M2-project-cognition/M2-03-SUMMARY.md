---
phase: M2
plan: 03
status: complete
date: 2026-05-11
files_modified:
  - voss/harness/agent.py (RunSemantics + run_turn integration + decisions mirror)
  - voss/harness/tools.py (record_run privileged ToolEntry)
  - voss/harness/recorder.py (absorb + write_decisions_md)
  - voss/harness/cli.py (_run_repl appends asdict(result.run) + session_id=record.id)
  - tests/harness/test_agent_integration.py (FakeProviderWithSemantics/Failing + 3 new tests)
  - tests/harness/test_cognition.py (test_decision_frontmatter unskipped)
  - tests/harness/test_tools.py (mutating count 4)
  - tests/harness/test_tools_config_cmds.py (10-tool listing)
tests_added: 4 (3 record_run integration + 1 decision_frontmatter)
tests_total: 196 passed + 11 skipped
---

# M2-03 Summary: Agent Integration · record_run · Decisions Mirror

Wave 2 closes COG-08 semantic half and COG-06 (decisions mirror).

## 1. `run_turn` integration map

```
async def run_turn(..., session_id=None, cognition=None):
    rec = RunRecorder.start()                        ← before show_thinking
    renderer.show_thinking("planning")
    resp = await provider.complete(... response_format=Plan ...)
    if confidence < threshold:
        return TurnResult(..., run=None)             ← clarify path skips recorder
    for step in plan.steps:
        if entry is None:
            rec.observe(step.name, step.args, "<unknown tool>", ok=False)
        elif not allowed:
            rec.observe(step.name, step.args, text, ok=False)
        elif exception:
            rec.observe(step.name, step.args, text, ok=False)
        else:
            rec.observe(step.name, step.args, text, ok=True)
    # NEW (M2-03):
    transcript = _compose_run_transcript(task, plan, results, rec)
    semantics = await _record_run_call(provider, model, transcript)
    if semantics is not None:
        rec.absorb(semantics, plan)
    else:
        rec.goal = "(record_run failed)"
        rec.plan = plan.model_dump()
    run = rec.finalize(cwd, cost_usd=resp.cost_usd)
    if run.decisions:
        try: write_decisions_md(cwd, run, session_id or "(no-session)")
        except OSError as exc: click.echo(f"warning: ...", err=True)
    return TurnResult(..., run=run)
```

`rec.observe` count by grep = 4 (one per dispatch branch). `rec.finalize` count = 1.

## 2. `RunSemantics` pydantic v2 schema

```python
class RunSemantics(BaseModel):
    model_config = {"extra": "ignore"}     # LENIENT (LLM-output, T-M2-11)

    goal: str = ""
    avoided: list[dict]  = []
    assumptions: list[str] = []
    decisions: list[dict] = []
    risks: list[str] = []
    follow_ups: list[str] = []
```

`extra="ignore"` deliberately differs from `cognition_schemas.STRICT` —
hallucinated fields are dropped silently, never crash the turn close.

### `RECORD_RUN_SYSTEM` prompt (verbatim, in agent.py)

```
You are closing out an agent turn. Summarize it as a
RunSemantics object capturing the user-visible goal, decisions you made and
why, assumptions made, risks introduced, and follow-up work. Keep each
decision title under 8 words; body under 3 sentences. If a field has no
content, return an empty list — do not invent.
```

## 3. record_run failure-mode contract (Pitfall 1)

| Closing-call outcome             | `run.goal`              | `run.plan`              | Turn behavior |
|----------------------------------|-------------------------|-------------------------|---------------|
| Returns `RunSemantics`           | `semantics.goal`        | `plan.model_dump()`     | normal completion |
| Provider raises (e.g. network)   | `"(record_run failed)"` | `plan.model_dump()` (fallback) | turn still completes; mechanical fields intact |
| `resp.parsed is None`            | `"(record_run failed)"` | `plan.model_dump()`     | same |
| Confidence-clarify branch        | n/a — `TurnResult.run is None`         | — | clarify path skips recorder entirely |

`_record_run_call` wraps `await provider.complete(...)` in `try: except
Exception:` and returns None on any failure. Turn-level never-raise
invariant: T-M2-10 mitigated.

## 4. `.voss/decisions/*.md` frontmatter contract (D-08, COG-06)

```
---
id: <YYYY-MM-DD-slug>
status: active
related_session: <session_id>
confidence: <0..1 float, .2f>
created_at: <UTC ISO seconds>
---

# <title>

<body>
```

| Key              | Type    | Source |
|------------------|---------|--------|
| `id`             | str     | matches `path.stem` (reserve_filename) |
| `status`         | enum    | always `"active"` at write time |
| `related_session`| str     | session_id from run_turn kwarg (`"(no-session)"` sentinel if unset) |
| `confidence`     | float   | `float(d.get("confidence", 0.0))` clamped at format `.2f` |
| `created_at`     | str ISO | `datetime.now(timezone.utc).isoformat(timespec="seconds")` |

`write_decisions_md(cwd, run, session_id)` returns `list[Path]` of mirrored
files. Empty `run.decisions` → returns `[]` without creating the dir.
Collisions handled by `cognition.reserve_filename` (`-2`, `-3` suffixes).

`slug(title)` strips non-alphanumeric to `-`; cannot produce `..` or `/` →
T-M2-12 mitigated.

## 5. `record_run` ToolDescriptor (symmetry, not dispatched)

Registered in `make_toolset()` with `is_mutating=True` (consistent with
M1-01 ToolEntry classification). Body returns `"ok"` — the actual semantics
flow through the privileged `provider.complete(response_format=RunSemantics)`
call in `_record_run_call`, never through tool dispatch.

Total tool count: **10** (was 9 in M1). Mutating count: **4** (fs_write,
fs_edit, shell_run, record_run). `tests/harness/test_tools.py::test_mutating_count`
and `test_tools_config_cmds.py::test_lists_all_ten_tools` updated.

## 6. cli.py persistence

`_run_repl` now passes `session_id=record.id` into `run_turn(...)` and
appends `asdict(result.run)` to `record.runs` after each turn:

```python
result = asyncio.run(run_turn(..., session_id=record.id, ...))
if result.run is not None:
    record.runs.append(asdict(result.run))
total_cost += result.cost_usd
```

Next `/save` (or M2-06 auto-save) persists the runs array into
`<cwd>/.voss/sessions/<id>.json`.

## 7. Test additions

| File                                    | Tests added | Notes |
|-----------------------------------------|-------------|-------|
| `test_agent_integration.py`             | 3           | `FakeProviderWithSemantics`, `FakeProviderFailingSemantics` + 3 tests (`test_record_run_populates_semantic_fields`, `test_record_run_failure_persists_mechanical`, `test_decisions_written_to_disk`). Plus a skipped `test_turn_injects_cognition` placeholder for M2-05. |
| `test_cognition.py`                     | 1           | `test_decision_frontmatter` unskipped — locks the 5-key frontmatter contract. |
| `test_tools.py`                         | 0 (updated) | `test_mutating_count` expects 4/6 split. |
| `test_tools_config_cmds.py`             | 0 (updated) | renamed to `test_lists_all_ten_tools`, asserts `record_run` present. |

Full harness suite: **196 passed + 11 skipped** (was 192 + 11 after M2-02).

## 8. Threat dispositions

| Threat   | Disposition |
|----------|-------------|
| T-M2-09  | **Accepted carve-out**: user-pasted secrets quoted into `decisions[].body` survive verbatim. Documented in session.py docstring (M1-03 + M2-02). |
| T-M2-10  | Mitigated: `_record_run_call` try/except wraps provider call; failure → sentinel goal, turn completes. |
| T-M2-11  | Mitigated: `RunSemantics.model_config = {"extra": "ignore"}` silently drops hallucinated fields. |
| T-M2-12  | Mitigated: `cognition.slug()` strips non-alphanumeric → cannot produce `..` or `/`. |

## 9. Handoff to M2-04+

- **M2-04 /analyze**: writes `.voss/architecture.md` + `.voss/*.yml`; once
  written, `cognition.load(cwd)` works fully, which M2-05 then injects.
- **M2-05 REPL auto-injection**: hooks the `cognition=` kwarg that
  M2-03 added to `run_turn` (currently accepted-but-unused).
- **M2-06 drift hint + auto-save**: consumes the `record.runs` list M2-03
  populates per turn; renderer warning channel formalized in M2-05 (W9
  ticket) — current decisions-mirror error uses `click.echo(..., err=True)`
  as a placeholder.

## 10. M1-05 follow-up flag

M1-01 already added `is_mutating: bool` to `ToolEntry`. No follow-up needed
— `record_run` is registered with `is_mutating=True` cleanly. This plan's
contingency note is moot.

Subagents used (opus, sequential): one combined agent for Tasks 1a+1b
(agent.py + tools.py + recorder.py + cli.py — all tightly coupled), then
one for Task 2 tests. Sequential because Task 2 imports `RunSemantics` +
`write_decisions_md` from Task 1's output.
