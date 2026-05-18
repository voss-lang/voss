# Phase M11: Voss-aware Tools (CAPS-01b) - Validation Map

**Created:** 2026-05-18

---

## Requirement Map

| Requirement | Meaning | Covered By |
|---|---|---|
| VTOOL-01 | T7 `.voss` lint-as-skill is first-class reachable and its frozen JSON schema is consumed unchanged | M11-03 |
| VTOOL-02 | Probable-value inspector over recorded decisions | M11-01, M11-02, M11-05 |
| VTOOL-03 | Budget tracer over recorded iterations | M11-01, M11-02, M11-05 |
| VTOOL-04 | `.voss` to Python diff viewer, dogfood-capable | M11-04, M11-05 |
| VTOOL-05 | All M11 surfaces are read-only and add zero new emit points | M11-01..M11-05 |

---

## Verification Gates

### Gate 1: Recorded Data Fidelity

Required checks:

- Synthetic session fixture with two decisions renders as an ordered sequence.
- Decision confidence values clamp/render deterministically.
- Budget trace cumulative tokens are computed from existing iteration fields.
- Missing decisions/iterations produce useful no-data output, not exceptions.

### Gate 2: Surface Registration

Required checks:

- `voss tools` lists `voss_probable_inspect`, `voss_budget_trace`, and
  `voss_py_diff`, all read-only.
- Slash registry includes `/probable`, `/btrace`, `/vdiff`.
- Slash registry still includes the existing `/budget` USD command and M11
  does not change its behavior.
- `voss inspect probable`, `voss inspect budget`, and `voss vdiff` have CLI
  tests.

### Gate 3: Lint Schema Contract

Required checks:

- `default_skill_registry().get("voss-lint-as-skill")` still exists.
- Running the skill against a seeded bad `.voss` emits `version: 1`.
- Findings contain exactly `file,line,col,rule,severity,msg,hint`.
- M11 consumer rejects extra/missing fields in tests.
- `voss/harness/skills/voss_lint_as_skill.py` schema field names are unchanged.

### Gate 4: Diff Fidelity

Required checks:

- `voss vdiff voss/harness/agent/planner.voss` works when a cached harness
  artifact exists.
- Arbitrary `.voss` file falls back to parse/analyze/codegen in memory.
- Output includes the Voss source side and generated Python side.
- No source-map claim appears in CLI, help, or tests.

### Gate 5: No Emit Points

Required checks:

- `pytest tests/harness/tui/test_no_new_runtime_hooks.py`
- `git diff -- voss/harness/recorder.py voss_runtime/probable.py voss_runtime/budget.py voss_runtime/agent.py` is empty during M11 execution.
- New code has no calls that append new fields to `RunRecord.decisions` or
  `IterationRecord`.

---

## Phase Acceptance Command Set

Focused acceptance after all five plans:

```bash
python3 -m pytest -q tests/harness/test_voss_inspect.py tests/harness/test_voss_lint_schema.py tests/harness/test_voss_diff.py tests/harness/test_repl_slash.py tests/harness/test_tools.py tests/harness/tui/test_m11_modals.py tests/harness/test_m11_acceptance.py
python3 -m pytest -q tests/harness/tui/test_no_new_runtime_hooks.py
python3 -m voss.cli check voss/harness/agent/
python3 -m voss.cli vdiff voss/harness/agent/planner.voss
git diff --check
```

Known broader-suite risk from recent project history: full non-live runs have
outside-M11 blockers around isolated `platformdirs`, recorder runtime-surface
baseline drift, npm shim expectations, live Anthropic auth, and missing Ollama
models. M11 acceptance is therefore focused and no-emit guarded.

