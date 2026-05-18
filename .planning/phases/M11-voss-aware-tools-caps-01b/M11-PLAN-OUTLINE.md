---
phase: M11
slug: voss-aware-tools-caps-01b
type: plan-outline
created: 2026-05-18
---

# Phase M11 - Voss-aware Tools - Plan Outline

M11 ships five serial plans. Serialization is intentional: plans 2, 4, and 5
touch shared CLI/slash/TUI surfaces, so parallel execution would create avoidable
merge friction.

| Plan ID | Objective | Wave | Depends On | Requirements |
|---|---|---:|---|---|
| M11-01 | Recorded-data inspection core. Add pure helpers for decision sequences and iteration budget timelines, with synthetic session tests and no-emit guards. | 1 | - | VTOOL-02, VTOOL-03, VTOOL-05 |
| M11-02 | Probable inspector and budget tracer surfaces. Register read-only tools, `voss inspect probable`, `voss inspect budget`, `/probable`, and `/btrace`. | 2 | M11-01 | VTOOL-02, VTOOL-03, VTOOL-05 |
| M11-03 | Lint-as-skill schema integration. Consume T7 SKL-06 output unchanged, validate schema, and prove first-class skill reachability. | 3 | M11-01 | VTOOL-01, VTOOL-05 |
| M11-04 | `.voss` to Python diff viewer. Add on-demand source-vs-generated diff core plus `voss vdiff`, `/vdiff`, and `voss_py_diff` tool. | 4 | M11-01, M11-02 | VTOOL-04, VTOOL-05 |
| M11-05 | TUI modal reuse and final acceptance. Add read-only modals for probable, budget trace, and Voss/Python diff plus phase-level acceptance guards. | 5 | M11-02, M11-03, M11-04 | VTOOL-01, VTOOL-02, VTOOL-03, VTOOL-04, VTOOL-05 |

## Dependency Notes

- M11-01 creates the pure read/format layer. Every later surface calls it
  instead of duplicating session parsing.
- M11-02 deliberately chooses `/btrace` because `/budget` is already the
  T6 session-USD slash.
- M11-03 does not edit the T7 lint producer unless a test exposes a real bug.
- M11-04 is after M11-02 because both touch `tools.py`, `cli.py`, and slash
  tests.
- M11-05 is last because TUI modals should wrap already-tested CLI/core output,
  not invent alternate semantics.

## OUTLINE COMPLETE

Total plans: 5 across 5 waves.

