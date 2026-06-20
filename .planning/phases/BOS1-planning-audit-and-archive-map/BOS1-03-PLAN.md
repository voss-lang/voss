# BOS1-03 Plan: BOS Track Restart and Prefix Cleanup

**Status:** Executed 2026-06-20
**Type:** docs reconciliation
**Requirements:** BOS-PROD-01..04, BOS-PLAN-01..04

## Objective

Return Behavioral OS work to one traditional BOS-prefixed implementation track:
`BOS1-01`, `BOS2-01`, through `BOS18-*`.

## Scope

Modify:
- `.planning/ROADMAP.md`
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- BOS phase docs needed to preserve implemented context

Remove:
- split-prefix planning artifacts
- split-prefix terminology from active docs and runtime test labels

Do not modify:
- git history or branches
- implemented BOS runtime code except naming comments/docstrings

## Acceptance Criteria

1. ROADMAP has BOS1-BOS18 as the only active Behavioral OS track.
2. PROJECT, REQUIREMENTS, and STATE reference BOS phases only.
3. Implemented projection and ledger work are carried forward under BOS3.
4. Split-prefix planning artifacts are deleted.
5. Tests for implemented BOS projection/ledger still pass.

## Verification

```bash
rg -n "BOS[I R]" .planning voss/harness tests/harness
pytest tests/harness/test_bos_event_projection.py \
  tests/harness/test_bos_event_ledger.py \
  tests/harness/test_swarm_store.py -q
```
