---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 02
subsystem: memory
tags: [memory, telemetry, retrieval, sidecar, vacuum, gitignore, VRNK-01]

# Dependency graph
requires:
  - phase: V23-01
    provides: RED telemetry tests + sidecar contract (.voss/memory/.retrieval.jsonl, compacted retrieval_count/last_retrieved)
  - phase: M8 memory store
    provides: _lock skip-on-contention, _load_tombstones corrupt-tolerant reader, vacuum three-pass, recall surface
provides:
  - MemoryStore._record_telemetry / _load_telemetry_compacted / _vacuum_telemetry / _retrieval_path
  - Agent-path telemetry record call at the memory_recall tool site (CLI no-touch)
  - _VOSS_MEMORY_GITIGNORE extended (.retrieval.jsonl + .reindex-manifest.json; .pins.json excluded)
  - vacuum() fourth pass compacting the telemetry sidecar
affects: [V23-04 rescore (reads count+last_retrieved), V23-05 retrieval-aware eviction (reads last_retrieved), V23-06 global-store telemetry]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Telemetry mirrors the .tombstones.jsonl lifecycle: append-log + vacuum compaction, under _lock('retrieval') skip-on-contention"
    - "Compacted reader is idempotent — folds BOTH raw {locator,ts} events and compacted {locator,retrieval_count,last_retrieved} lines"
    - "Compacted dict carries dual field names: retrieval_count (SPEC) + count alias (V23-04/05 readers)"

key-files:
  created: []
  modified:
    - voss/harness/memory_store.py
    - voss/harness/tools.py

key-decisions:
  - "Compacted entry emits BOTH `retrieval_count` (SPEC field, V23-01 test) and `count` (V23-04 `int(entry['count'])` + V23-05 readers) → no test/plan divergence to fix later"
  - "_vacuum_telemetry() wired in BOTH vacuum() branches (early no-tombstone return AND main path) so telemetry compacts regardless of tombstone presence"
  - "Telemetry records the response hit-list AFTER the `if not hits` guard (plan placement); recall() body never touched (assertion + diff confirm)"
  - "All telemetry fs work try/except-wrapped + skip-on-contention so it can never break a recall caller (T-V23-02-01/02)"

patterns-established:
  - "Sidecar append-then-compact with a single corrupt-tolerant fold reused by record/load/vacuum"

requirements-completed: [VRNK-01]

# Metrics
completed: 2026-06-14
---

# Phase V23 Plan 02: Retrieval telemetry (VRNK-01) Summary

**Implemented the `.voss/memory/.retrieval.jsonl` telemetry append-log written only by agent-path recall, with vacuum compaction, gitignored, and memory files left byte/mtime-immutable — the data substrate for VRNK-03 rescore and VRNK-04 eviction.**

## Accomplishments
- `MemoryStore._record_telemetry(hits)` — empty-hits no-op; `_lock("retrieval")` skip-on-contention; appends one `{locator, ts}` line per hit; fs errors swallowed. Writes ONLY the sidecar.
- `MemoryStore._load_telemetry_compacted()` — corrupt-line-tolerant fold → `{locator: {retrieval_count, count, last_retrieved}}`; reads raw event lines AND post-vacuum compacted lines (idempotent); `{}` on missing/all-corrupt.
- `MemoryStore._vacuum_telemetry()` + `_retrieval_path` property; wired as vacuum() pass (iv) in both the early-return and main branches.
- `_VOSS_MEMORY_GITIGNORE` extended with `.retrieval.jsonl` + `.reindex-manifest.json`; `.pins.json` deliberately excluded (D-02 committed).
- One surgical `store._record_telemetry(hits)` at the `memory_recall` tool site (agent path); `cli.py` recall left no-touch.

## Files Modified
- `voss/harness/memory_store.py` — gitignore constant; `_retrieval_path` + 3 telemetry methods (after the tombstones block); vacuum fourth pass ×2 branches.
- `voss/harness/tools.py` — telemetry record call + comment after the `memory_recall` no-hits guard.

## Decisions Made
- **Dual field names** in the compacted entry. V23-01's RED test + SPEC §Acceptance say `retrieval_count`; V23-04-PLAN reads `int(entry["count"])`. Emitting both (same value) satisfies the test, the SPEC, and the downstream rescore/eviction readers without leaving any of them broken.

## Deviations from Plan
- Plan Task 1 wording used `count`; implemented persisted/SPEC field as `retrieval_count` with `count` as an alias (see above).
- `_vacuum_telemetry()` added to the early-return (no-tombstone) branch too, not just the main path, so telemetry always compacts.

## Issues Encountered
- The plan's `-k telemetry` acceptance filter also matches `test_show_displays_telemetry` (a VRNK-07 CLI verb test, legitimately RED until V23-07) — a keyword collision, not a defect. The three actual VRNK-01 tests are GREEN; verified by exact node ids.

## Verification
- 3 VRNK-01 tests GREEN (exact node ids): `test_telemetry_recorded_on_agent_recall`, `test_telemetry_not_recorded_on_cli_recall`, `test_recall_does_not_mutate_memory_file_mtime`.
- Greps: `memory_store.py` `.retrieval.jsonl` ×5 (≥2); `.pins.json` NOT on the gitignore line; `tools.py` `_record_telemetry` ×1; `cli.py` `_record_telemetry` ×0.
- `recall()` body unchanged (git diff shows no edit at the recall region).
- Broad memory regression sweep (test_memory_store / _eviction / _vacuum / _tools + tests/memory existing): **36 passed, 0 failed**.
- Module posture now: 12 failed (remaining V23-03..07 features) / 7 passed / 1 xfailed — telemetry flipped 3 RED→GREEN.

## Next Phase Readiness
Telemetry substrate live. V23-03 (floors) and V23-04 (rescore, reads `count`+`last_retrieved`) and V23-05 (eviction, reads `last_retrieved`) can consume `_load_telemetry_compacted()`.

---
*Phase: V23-retrieval-aware-memory-ranking-hygiene*
*Completed: 2026-06-14*
