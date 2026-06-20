# BOSI1-01 Summary: BOS Event Projection Runtime

**Completed:** 2026-06-20
**Plan:** BOSI1-01-PLAN.md
**Contract implemented:** `.planning/BOS-EVENT-SCHEMA.md` +
`.planning/schemas/bos-events.schema.json`

## Delivered

- Added `voss/harness/bos_events.py`, a pure projection layer for existing
  session, run, and swarm JSONL records.
- Added schema-validation tests in
  `tests/harness/test_bos_event_projection.py`.
- Updated `.planning/PROJECT.md` and `.planning/ROADMAP.md` to separate
  BOS contract work from BOSI implementation work.

## Behavior

- `SessionRecord` projects to `session.started`.
- `RunRecord` projects to `task.completed`.
- `RunRecord.changed`, `RunRecord.inspected`, and `RunRecord.avoided` project
  to `file.modified`, `file.inspected`, and `file.avoided`.
- `SwarmStore` JSONL envelopes project to `swarm.create`, `swarm.assign`,
  `task.created`, and `task.completed`.

## Boundaries Preserved

- No session writer changes.
- No swarm writer changes.
- No server/SSE transport changes.
- No BOS ledger/storage service yet; that is BOSI2.

## Verification

```bash
pytest tests/harness/test_bos_event_projection.py \
  tests/harness/test_session_redaction.py \
  tests/harness/test_swarm_store.py -q
python3 -m py_compile voss/harness/bos_events.py tests/harness/test_bos_event_projection.py
```

Both passed.
