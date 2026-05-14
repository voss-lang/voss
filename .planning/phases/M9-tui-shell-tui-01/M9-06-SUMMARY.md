---
phase: M9
plan: 06
status: complete
date: 2026-05-14
---

# M9-06 Summary — Fork-from-Turn + Session Schema Backward Compat (TUI-08)

Wave 6. `SessionRecord` grows two additive Optional fields — `parent_id`
and `parent_turn_index` — for fork lineage. `_hydrate` already filters
to `_SESSION_FIELDS`, so pre-M9 session JSON files load byte-clean with
both fields defaulting to `None`. Forking is a pure-data primitive in
`voss/harness/tui/fork.py`; the modal lives in `widgets/fork_modal.py`
and the app handler `VossTUIApp.action_fork_turn` wires the two
together. cli.py wiring + default-renderer flip is deferred to M9-07.

## Files Created

| Path | Purpose |
|------|---------|
| `voss/harness/tui/fork.py` | `fork_session(record, turn_index, cwd) -> SessionRecord`. Pure data — no UI imports. Seeds a new record with `turns[: turn_index + 1]`, `parent_id`, `parent_turn_index`, fresh runs, then persists via `session.save`. Raises ValueError on out-of-range index. |
| `voss/harness/tui/widgets/fork_modal.py` | `ForkConfirmModal(turn_n)` with locked UI-SPEC copy (heading + body) and `[Enter] Fork · [Esc] Cancel` bindings. Posts `ForkConfirmed(turn_n)` / `ForkCancelled` messages and dismisses with bool. |
| `tests/harness/tui/test_session_fork.py` | 8 tests — fork_session correctness, originals-untouched, out-of-range raise, modal heading/body, modal Enter/Esc paths, `action_fork_turn` end-to-end with status flash, no-op when record absent. |
| `tests/harness/tui/test_session_backward_compat.py` | 4 tests — pre-M9 fixture loads with `parent_id is None`, new fields roundtrip, fields appear in `_SESSION_FIELDS`, unknown keys (incl. credential-shaped) still dropped by `_hydrate`. |

## Files Modified

| Path | Change |
|------|--------|
| `voss/harness/session.py` | `SessionRecord` gains `parent_id: Optional[str] = None` and `parent_turn_index: Optional[int] = None` (additive). Module docstring extended with a paragraph noting the M9-06 fields and confirming neither carries credentials. `_SESSION_FIELDS` auto-updates because it iterates `dataclasses.fields(SessionRecord)`. |
| `voss/harness/tui/app.py` | Added `record: SessionRecord | None` + `focused_turn_index: int | None` instance attributes. Added `action_fork_turn()` — resolves the focused turn index, pushes `ForkConfirmModal`, and on Enter calls `fork_session(...)` then flashes the StatusLine with the UI-SPEC `Resumed {new_id} · {n} turns` toast. Pure local import of `fork_session` keeps `fork.py` UI-free. |
| `voss/harness/tui/widgets/__init__.py` | Re-export `ForkConfirmModal`. |
| `tests/harness/test_session_redaction.py` | Extended the schema-allowlist test's `expected` set with the two new keys. |

## Backward Compat Proof

`_hydrate` filters incoming dicts to `_SESSION_FIELDS` and provides
defaults for missing `turns` / `runs`. Adding new optional fields with
`None` defaults is therefore safe in BOTH directions:

- **Old reader + new file:** new keys dropped silently (`_hydrate` filter).
- **New reader + old file:** `parent_id` / `parent_turn_index` fall back to
  their `None` defaults.

Tests cover both: `test_pre_m9_session_loads_without_crash` writes the
M8-shape fixture and reads it through the M9 reader; the
`test_pre_m9_extra_unknown_keys_dropped` test confirms credential-shaped
keys are still rejected by the dataclass allowlist.

## Threat Model Outcomes

- **T-M9-06-01** (Tampering — crafted JSON with extra keys): mitigated by
  existing `_hydrate` filter. Redaction test extended to assert the
  expected key set explicitly.
- **T-M9-06-02** (DoS — out-of-range turn_index): mitigated by ValueError
  in `fork_session`; `action_fork_turn` also bails early via
  `_resolve_fork_index` returning `None`.
- **T-M9-06-03** (Information disclosure — cwd inherited): accepted; same
  property as resume.

## Verification

```bash
pytest tests/harness/tui/test_session_fork.py \
       tests/harness/tui/test_session_backward_compat.py \
       tests/harness/test_session.py \
       tests/harness/test_session_redaction.py -q
# → 32 passed
```

Full harness suite: 503 passed, 2 skipped (was 450 before M9-06).

## Success Criteria

1. ✅ `SessionRecord` has `parent_id` and `parent_turn_index` as additive
      Optional fields with `None` defaults.
2. ✅ Pre-M9 session JSON files load without crash and yield records with
      `parent_id is None`.
3. ✅ `fork_session(record, turn_index, cwd)` returns a new SessionRecord
      with parent fields set; original record unchanged on disk.
4. ✅ `ForkConfirmModal` renders UI-SPEC-locked copy; Enter/Esc bindings
      work.
5. ✅ `VossTUIApp.action_fork_turn` drives the modal → fork_session →
      status flash flow.

## Deferred to M9-07

- cli.py wiring: set `app.record` on session load; bind `f` key globally.
- Default-renderer flip + Windows-console strategy + accent allow-list +
  `--no-unicode` audits + phase-final human-verify checkpoint.
