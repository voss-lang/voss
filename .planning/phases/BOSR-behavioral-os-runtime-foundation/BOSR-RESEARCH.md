# BOSR Research: Behavioral OS Runtime Foundation

**Created:** 2026-06-20
**Mode:** Inline research from existing repo artifacts. No internet required.

## Existing Runtime Inputs

### Session Records

`voss/harness/session.py` defines:
- `SessionRecord`: id, name, cwd, model, timestamps, turns, runs, parent
  lineage.
- `RunRecord`: id, timestamps, goal, changed/inspected/avoided paths,
  decisions, validation, failures, cost, iterations, exit reason.

The session module has an explicit redaction invariant. BOSR must not add raw
provider credentials, secrets, or transcript content into BOS payloads.

### Swarm Events

`voss/harness/swarm_store.py` and `voss/harness/swarm/events.py` provide:
- `SwarmStore` with create/task/assign/done mutations.
- `SwarmEventLog` append-only JSONL under `.voss/swarm/<id>/events/events.jsonl`.
- Portalocker-based bounded exclusive append.
- Replay from event log.

This is the persistence style BOSR should mirror for `.voss/bos/events.jsonl`.

### BOS Event Projection

`voss/harness/bos_events.py` already projects:
- `SessionRecord` -> `session.started`
- `RunRecord` -> `task.completed`
- run file lists -> `file.modified`, `file.inspected`, `file.avoided`
- swarm JSONL envelopes -> `swarm.create`, `swarm.assign`, `task.created`,
  `task.completed`

Existing tests validate representative projection outputs against
`.planning/schemas/bos-events.schema.json`.

## Contracts Available

| Contract | Status | Use In BOSR |
|---|---|---|
| `.planning/schemas/bos-events.schema.json` | Exists | Event validation |
| `contracts/decision-ledger.schema.json` | Exists | Decision writer |
| `contracts/outcomes.schema.json` | Exists | Outcome writer and no-leakage tests |
| Recommendation-view contract | Planned in BOS9 | Use as source, but implement only if present |

## Implementation Patterns To Reuse

- Append-only JSONL writer: `SwarmEventLog`.
- Redaction allowlist: `SessionRecord` and `RunRecord` tests.
- Schema validation tests: `tests/planning/test_bos_outcome_schema.py` and
  `tests/harness/test_bos_event_projection.py`.
- Existing server/SSE swarm plane: V25 runtime; do not introduce another bus.
- No pydantic runtime dependency for hand-authored contracts unless already
  present and justified; use dictionaries plus tests where sufficient.

## Risks

| Risk | Mitigation |
|---|---|
| Recreating docs bloat | BOSR has exactly 6 plans; no nested BOSI subtrack |
| False-green schema tests | Use real schema files and representative projected records |
| Outcome leakage | Decision writer and outcome writer remain separate; tests assert no outcome fields in decisions |
| Sensitive data leakage | Payloads carry IDs, paths, metadata, and summaries only; no file contents or raw transcript |
| Bus proliferation | All runtime events derive from session/swarm/server sources; no new coordination transport |
| Overbuilding web/backend | BOSR exposes local read model only; backend/web write workflows deferred |

## Recommended Plan Order

1. Reconcile planning state so future execution targets BOSR.
2. Build local event ledger over BOSI1 projector.
3. Add decision and outcome capture.
4. Add shadow recommendation records.
5. Add read model for desktop/web consumption.
6. Validate end-to-end and retire stale placeholders.
