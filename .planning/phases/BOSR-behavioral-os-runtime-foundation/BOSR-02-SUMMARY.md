# BOSR-02 Summary: Local BOS Event Ledger

**Executed:** 2026-06-20
**Requirement:** BOSR-02

## Delivered

- Added `voss/harness/bos_ledger.py`.
- Added a local append-only ledger path at `.voss/bos/events.jsonl`.
- Added locked writes using `portalocker`.
- Added `append_event`, `append_many`, `read_events`, and `ledger_path`.
- Added duplicate `event_id` no-op handling that preserves file bytes.
- Added replay filters for `trace_id`, `event_type`, and `category`.
- Added replay tolerance for a torn trailing JSONL line.
- Added tests using projected session, run, file, and swarm events.

## Verification

```bash
pytest tests/harness/test_bos_event_projection.py \
  tests/harness/test_bos_event_ledger.py \
  tests/harness/test_swarm_store.py -q
python3 -m py_compile voss/harness/bos_events.py \
  voss/harness/bos_ledger.py \
  tests/harness/test_bos_event_ledger.py
```

Result: both commands passed.

## Notes

Runtime schema validation remains outside the ledger. Tests validate replayed
events against `.planning/schemas/bos-events.schema.json`, matching the BOSR-02
acceptance criteria while keeping the runtime ledger independent of planning
file paths.
