# BOS3-03 Plan: Event Projection and Local Event Ledger Runtime

**Status:** Executed 2026-06-20
**Type:** code
**Requirements:** BOS-DATA-06, BOS-DATA-07

## Objective

Turn the BOS event schema into a local runtime event substrate by projecting
existing Voss records into BOS events and persisting those events in an
append-only local ledger.

## Scope

Implement:
- pure projection helpers for `SessionRecord`, `RunRecord`, and swarm JSONL
  events
- local append-only `.voss/bos/events.jsonl` ledger
- duplicate `event_id` no-op handling
- replay filters for `trace_id`, `event_type`, and `category`
- torn trailing line tolerance
- schema-backed tests

Do not implement:
- decision rows
- outcome rows
- external ingestion
- backend sync
- web routes

## Acceptance Criteria

1. Projection does not mutate session, run, or swarm source logs.
2. Projected events validate against `.planning/schemas/bos-events.schema.json`.
3. Re-appending an existing `event_id` leaves ledger bytes unchanged.
4. Replay preserves append order and tolerates a torn final line.
5. Ledger tests cover session, run, file, and swarm projected events.

## Verification

```bash
pytest tests/harness/test_bos_event_projection.py \
  tests/harness/test_bos_event_ledger.py \
  tests/harness/test_swarm_store.py -q
python3 -m py_compile voss/harness/bos_events.py \
  voss/harness/bos_ledger.py \
  tests/harness/test_bos_event_ledger.py
```
