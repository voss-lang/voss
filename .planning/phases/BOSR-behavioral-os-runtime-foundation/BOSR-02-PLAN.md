# BOSR-02 Plan: Local BOS Event Ledger

**Status:** Executed 2026-06-20
**Wave:** 1
**Type:** code
**Requirements:** BOSR-02

## Objective

Persist projected BOS events in a local append-only ledger so Voss can replay
the Behavioral OS event stream from real harness/swarm activity.

## Scope

Implement:
- `voss/harness/bos_ledger.py`
- `.voss/bos/events.jsonl` append-only writer
- locked writes using portalocker
- `append_event`, `append_many`, `read_events`
- duplicate `event_id` no-op handling
- filters by `trace_id`, `event_type`, and `category`
- tests using real BOSI1 projected events

Do not implement:
- backend sync
- compaction
- schema migrations
- web routes

## Read First

- `voss/harness/bos_events.py`
- `voss/harness/swarm/events.py`
- `tests/harness/test_bos_event_projection.py`
- `.planning/schemas/bos-events.schema.json`

## Acceptance Criteria

1. Projected events append to `.voss/bos/events.jsonl`.
2. Re-appending the same `event_id` does not change file bytes.
3. Replay preserves order and tolerates a torn trailing line.
4. Events validate against the BOS event schema in tests.
5. Source session and swarm logs are not modified.

## Verification

```bash
pytest tests/harness/test_bos_event_projection.py \
  tests/harness/test_bos_event_ledger.py \
  tests/harness/test_swarm_store.py -q
python3 -m py_compile voss/harness/bos_events.py \
  voss/harness/bos_ledger.py \
  tests/harness/test_bos_event_ledger.py
```
