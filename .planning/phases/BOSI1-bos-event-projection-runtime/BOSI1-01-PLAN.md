# BOSI1-01 Plan: BOS Event Projection Runtime

**Status:** Executed 2026-06-20
**Track:** BOSI1 - BOS Event Projection Runtime
**Contract implemented:** `.planning/BOS-EVENT-SCHEMA.md` +
`.planning/schemas/bos-events.schema.json`

## Goal

Add the first code-backed BOS implementation slice: a pure Python projection
layer that reads existing Voss runtime records and returns canonical BOS event
dictionaries.

## Scope

Implement projections for:
- `SessionRecord` -> `session.started`
- `RunRecord` -> `task.completed`
- `RunRecord.changed`, `RunRecord.inspected`, `RunRecord.avoided` -> `file.*`
- Swarm JSONL envelopes from `SwarmStore` -> `swarm.*` or `task.*`

Do not change:
- session snapshot writing
- swarm JSONL writing
- server/SSE event emission
- any storage or sync service

## Success Criteria

1. Representative projected events validate against `.planning/schemas/bos-events.schema.json`.
2. Projection-derived fields (`ingest_time`, `trace_id`, `caused_by`) are
   assigned by the projector and are not written back to source records.
3. Payloads only carry schema-approved metadata: no file contents, provider
   credentials, tokens, or raw transcript content.
4. Existing session/swarm tests continue to pass.

## Verification

Run:

```bash
pytest tests/harness/test_bos_event_projection.py \
  tests/harness/test_session_redaction.py \
  tests/harness/test_swarm_store.py -q
```
