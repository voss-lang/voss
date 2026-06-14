---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 01
subsystem: tests
tags: [memory, retrieval-ranking, red-scaffold, tests-first, pytest-fixtures]

# Dependency graph
requires:
  - phase: M8 (project memory store)
    provides: MemoryStore surface (recall, write_turn/note/convention, _maybe_evict, root/cwd), Hit, make_id
  - phase: harness test fixtures
    provides: tmp_voss_repo + chroma_disabled_env in tests/harness/conftest.py
provides:
  - RED scaffold pinning all 8 V23 requirements (tests/memory/test_retrieval_ranking.py, 20 tests)
  - Fixture bridge tests/memory/conftest.py (pytest_plugins -> tests.harness.conftest)
  - Executable post-V23 contract for: telemetry sidecar (.retrieval.jsonl), pins sidecar (.pins.json), relevance floors, telemetry rescore, retrieval/pin-aware eviction, reindex CLI verbs
affects: [V23-02 telemetry, V23-03 floors, V23-04 rescore, V23-05 eviction+reindex, V23-06 pins, V23-07 CLI verbs, V23-08 regression]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RED scaffold references not-yet-existing APIs INSIDE test bodies (module-level imports stay real → collects clean, fails at call)"
    - "Sidecar contract guessed/locked here: telemetry = .voss/memory/.retrieval.jsonl, pins = .voss/memory/.pins.json"
    - "Config knobs ride existing _load_memory_config (.voss/config.yml memory: chroma_floor/bm25_floor_ratio/rescore)"
    - "Regression locks (byte-identical, floor-disabled, mtime-fallback, empty-rescore-noop) PASS now and after — guard the no-change-unless-opted-in constraint"

key-files:
  created:
    - tests/memory/conftest.py
    - tests/memory/test_retrieval_ranking.py
  modified: []

key-decisions:
  - "pytest_plugins=['tests.harness.conftest'] in a nested conftest WORKS in this pytest (verified collect-only exit 0) despite no rootdir conftest + absent tests/harness/__init__.py (namespace pkg resolves)"
  - "Autouse _no_chroma monkeypatch makes recall BM25-only deterministic (mirrors test_memory_eviction analog) so byte-identical/rescore ordering is reproducible"
  - "Floor RED uses a ubiquitous-token query ('system' in all docs) that fills today but must floor to 0 — true-junk queries already return 0 (would false-green)"
  - "Pin/eviction RED uses conventions (0.10 quota) not notes (0.0 quota → never evict); 2x200B files @ cap 2560 → quota 256 → exactly 1 eviction"
  - "VRNK-06 unit scope asserts the _load_pins contract; full context-window injection is manual-only per V23-VALIDATION (not unit-faked)"

patterns-established:
  - "Behaviour-RED (assert post-V23 ordering/exit-code) vs symbol-RED (call absent _record_telemetry/_load_pins/reindex verb) — both collect, both fail for the feature reason"
  - "Single xfail(strict=False) for the V21-gated global-store dual-fusion pin path; un-xfailed by V23-06"

requirements-completed: [VRNK-01, VRNK-02, VRNK-03, VRNK-04, VRNK-05, VRNK-06, VRNK-07, VRNK-08]

# Metrics
completed: 2026-06-14
---

# Phase V23 Plan 01: RED test scaffold (VRNK-01..08) Summary

**Created the Wave 0 tests-first gate: `tests/memory/test_retrieval_ranking.py` (20 tests pinning all eight V23 requirements) + `tests/memory/conftest.py` (fixture bridge), so every later V23 plan turns named RED tests GREEN against a concrete, falsifiable contract.**

## Accomplishments
- **Fixture bridge** — `tests/memory/conftest.py` exposes `tmp_voss_repo` + `chroma_disabled_env` to `tests/memory/` via `pytest_plugins = ["tests.harness.conftest"]` (no redefinition; single source of truth stays in tests/harness/conftest.py). Verified the nested-conftest `pytest_plugins` resolves here (collect-only exit 0).
- **RED scaffold** — 20 `def test_` functions across VRNK-01..08, each carrying its V23-VALIDATION `-k` keyword (telemetry, floor, rescore, byte_identical, evict, reindex, drift, pin, cli). Module collects with zero ImportError; references not-yet-existing APIs (`_record_telemetry`, `_load_telemetry_compacted`, `_load_pins`, `reindex`/`pin`/`unpin`/`list`/`show` CLI verbs) inside bodies so RED arrives at call, not collection.
- **Posture:** 15 FAILED (feature-absent), 4 PASSED (intended regression locks), 1 XFAIL (V21 global-store), 0 XPASS. Both setup-sensitive REDs confirmed to fail on the feature assertion, not seeding (rescore: A still leads B with telemetry favouring B; eviction: mtime killed the retrieved-old file).

## Task Commits
1. **Task 1: Fixture bridge** — tests/memory/conftest.py (uncommitted; Ben commits)
2. **Task 2: RED scaffold VRNK-01..08** — tests/memory/test_retrieval_ranking.py (uncommitted)

## Files Created/Modified
- `tests/memory/conftest.py` — `pytest_plugins = ["tests.harness.conftest"]` bridge + V23 docstring.
- `tests/memory/test_retrieval_ranking.py` — 20-test RED scaffold; autouse `_no_chroma`; seed/sidecar/config helpers; sidecar + config-knob contract documented in module docstring.

## Decisions Made
- Sidecar paths locked: `.voss/memory/.retrieval.jsonl` (telemetry), `.voss/memory/.pins.json` (pins). Config knobs extend `_load_memory_config` (`.voss/config.yml` `memory.{chroma_floor,bm25_floor_ratio,rescore}`). These are the contract downstream plans (V23-02/03/04/06) implement against; if a plan picks a different mechanism it must update the corresponding test, not leave it RED.

## Deviations from Plan
- Plan listed 19 named tests "one-or-more per requirement"; delivered 20 (added the explicit V21-gated `test_pinned_global_store_dual_fusion` xfail). Within plan intent (≥15, ≤1 xfail).
- `tests/harness/__init__.py` absent (plan flagged this) — `pytest_plugins` string still resolves; no `__init__.py` added (out of scope, not needed).

## Verification
- `.venv/bin/python -m pytest tests/memory/ --collect-only -q` — exit 0 (24 collected incl. existing episodic/semantic/working).
- Keyword presence loop (telemetry floor rescore byte_identical evict reindex drift pin cli) — prints nothing (all covered).
- Grep guards: `pytest.skip(` == 0; `xfail` == 1 (names V21); `def test_` == 20; fixture redefinition == 0.
- RED run: 15 failed / 4 passed (regression locks) / 1 xfailed / 0 xpassed.
- Non-regression: existing tests/memory + tests/harness/test_memory_eviction.py green (bridge non-destructive). No runtime surface touched (test-only plan; git status = 2 new files only).

## Next Phase Readiness
Wave 1+ plans (V23-02..07) each have named RED targets + a locked sidecar/config contract. V23-08 regression uses the byte-identical lock already green.

---
*Phase: V23-retrieval-aware-memory-ranking-hygiene*
*Completed: 2026-06-14*
