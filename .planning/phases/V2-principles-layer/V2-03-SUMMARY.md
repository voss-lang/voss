---
phase: V2-principles-layer
plan: 03
subsystem: cli
tags: [principles, cli, show, guard, schema-freeze, opacity]

requires:
  - phase: V2-01
    provides: "resolve_with_sources / VossPrinciplesConfigError"
  - phase: V2-02
    provides: "injection (the runtime consumer the opacity guard scans)"
provides:
  - "voss principles show (+ --json) — merged active set with per-principle source (VPRIN-07)"
  - "AST guard: no code path branches on a principle key/text (VPRIN-03 opacity)"
  - "Schema-freeze guard: RunRecord/SessionRecord/BudgetScope field sets frozen"
affects: [V9 audit recording of principles, future principle consumers]

tech-stack:
  added: []
  patterns:
    - "AST branch-scan guard enforcing opaque-data treatment of config text"
    - "dataclass field-set freeze test protecting the redaction invariant"

key-files:
  created:
    - tests/harness/test_principles_cli.py
    - tests/harness/test_principles_guard.py
  modified:
    - voss/harness/cli.py

key-decisions:
  - "show human format: `{key}  [{source}]  {text}` aligned on key width"
  - "Guard scans principles.py + agent.py; flags principle key/text only in Compare operands / match-case values (data positions allowed)"
  - "Schema-freeze baseline captured AS-IS post-V1-04 (RunRecord = 24 fields incl capability_invocations); V2 adds zero"

patterns-established:
  - "principles_group registered in AGENT_COMMANDS like capabilities_group/memory_group"

requirements-completed: [VPRIN-03, VPRIN-07]

duration: 15min
completed: 2026-06-06
---

# Phase V2-03: Principles Layer — Show CLI + Guards Summary

**`voss principles show` makes the merged active principle set inspectable with per-principle source, and two guards lock the invariants: principles are opaque (no code branches on them) and the redaction-critical record schemas are frozen.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2 / 2
- **Files modified:** 1 source + 2 tests created

## Accomplishments

### Task 1 — `voss principles show`
- `principles_group` + `show` subcommand mirroring `capabilities_group` (`--cwd` + `--json` + local `import json as json_lib`). Human: `{key}  [{source}]  {text}`; JSON: list of `{key, text, source}`. Malformed file → `VossPrinciplesConfigError` caught → stderr `<error: …>` + `Exit(1)`. Registered in `AGENT_COMMANDS`.

### Task 2 — guards
- **GUARD 1 (opacity, VPRIN-03):** AST-scans `principles.py` + `agent.py` for any principle key/default-text used as a `Compare` operand or `match`-case value → fails if found (keys/texts sourced from `DEFAULT_PRINCIPLES`, no hardcoding). Data positions (the constant, f-string interpolation) are allowed.
- **GUARD 2 (schema freeze):** asserts the exact field-name sets of `RunRecord` (24), `SessionRecord` (11), `BudgetScope` (8); any field add/remove fails, protecting the O1/V4 redaction invariant.

## Verification

- `test_principles_cli.py` (7) + `test_principles_guard.py` (5) green.
- `voss principles show` exits 0 with grouped source labels; `--json` parses to 6 default-sourced entries.
- `test_session_redaction.py` still green (redaction invariant intact).
- V2-03 edited only cli.py + the two test files — no changes to session.py/budget.py (schema-freeze holds; the guard captures the current frozen baseline).

## Notes

- No deviations: all changes within the plan's `files_modified`.
- Schema-freeze baseline includes V1-04's `capability_invocations` (a prior-phase field). V2 adds none; V9 will add principle-audit fields and must update the frozen sets then.
