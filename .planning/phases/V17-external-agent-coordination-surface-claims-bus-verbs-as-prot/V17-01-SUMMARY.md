---
phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot
plan: 01
subsystem: testing
tags: [pytest, click, clirunner, sqlite, sse, xfail, coherence-guard]

# Dependency graph
requires: []
provides:
  - RED test surface for every VBUS-01..08 acceptance criterion (named, collectable pytests)
  - tests/harness/claims/ — overlap (6 SPEC cases), two-agent verb sequence, concurrent exactly-one-winner race, TTL, advice array
  - tests/harness/bus/ — wait/timeout, inbox cursor, restart durability (xfail-gated on V15) + restartable loopback-server helper in package __init__
  - tests/harness/test_env_injection.py / test_coordination_doc.py (xfail scaffolds)
  - tests/harness/test_coherence_guard.py — VBUS-08 enforcement, GREEN now
affects: [V17-02, V17-03, V17-04, V17-05, V17-06, V17-07]

# Tech tracking
tech-stack:
  added: []
  patterns: [module-level try/except ImportError + xfail(strict=False) RED scaffold, restartable uvicorn-in-thread bus server helper, baseline-pinned coherence guard]

key-files:
  created:
    - tests/harness/claims/test_overlap.py
    - tests/harness/claims/test_claims_verbs.py
    - tests/harness/claims/test_claims_concurrent.py
    - tests/harness/claims/test_claims_ttl.py
    - tests/harness/claims/test_claims_advice.py
    - tests/harness/bus/__init__.py
    - tests/harness/bus/test_bus_wait.py
    - tests/harness/bus/test_bus_inbox.py
    - tests/harness/bus/test_bus_durability.py
    - tests/harness/test_env_injection.py
    - tests/harness/test_coordination_doc.py
    - tests/harness/test_coherence_guard.py
  modified:
    - pyproject.toml

key-decisions:
  - "Each test body opens with a _require_*() guard that pytest.fail()s while the target module is absent — prevents spurious XPASS from exit-code-1 asserts running against a None command (xfail stays honest RED)"
  - "Bus server helper lives in tests/harness/bus/__init__.py (relative import) — restartable contextmanager over create_app + uvicorn thread, chdir into tmp cwd so the .voss/bus/ journal lands per-test"
  - "Coherence guard allowlists the pre-existing watchdog pin (2 comment-filtered pyproject entries) instead of asserting zero watcher mentions — watchdog pre-dates V17"
  - "Solid-component guard checks forbidden name prefixes (claims/bus/coordination) not a blanket file count — concurrent A-track work adds unrelated components"

patterns-established:
  - "RED scaffold idiom: try/except ImportError flag + module pytestmark xfail(strict=False) + per-test _require guard; mark removed when the wave turns GREEN"
  - "Claims tests pass identity via CliRunner env={'VOSS_AGENT_ID': ...}; absence asserted with env={'VOSS_AGENT_ID': None}"

requirements-completed: [VBUS-01, VBUS-02, VBUS-03, VBUS-04, VBUS-05, VBUS-06, VBUS-07, VBUS-08]

# Metrics
duration: 18min
completed: 2026-06-10
---

# Phase V17 Plan 01: Wave 0 Test Scaffold Summary

**RED pytest surface for all eight VBUS requirements: 21 xfail scaffold tests + 3 green coherence-guard tests, zero collection errors across the 2682-test tree**

## Performance

- **Duration:** ~18 min
- **Completed:** 2026-06-10
- **Tasks:** 3
- **Files modified:** 13 (12 created + pyproject.toml)

## Accomplishments
- Every VBUS-01..08 acceptance bullet maps to a named pytest (RESEARCH "Phase Requirements → Test Map" fully covered); no later plan can claim "no test exists"
- Six SPEC overlap cases as discrete assertions; two-agent acceptance sequence; subprocess race asserting exactly one exit-0 winner; TTL expiry + default-1800s checks; advice-array conflict contract
- Bus wait/inbox/durability scaffolds collect + run as xfail with a reusable restartable server helper for V17-05/06
- VBUS-08 coherence guard enforceable today: swarm/ pinned to {swarmTypes.ts}, watcher deps capped at baseline, no V17-named Solid components

## Task Commits

1. **Task 1: Claims test scaffolds** - `2cf60ef` (test)
2. **Task 2: Bus test scaffolds, V15-gated xfail** - `307e66a` (test)
3. **Task 3: Identity/doc/coherence-guard scaffolds** - `0959609` (test)

## Files Created/Modified
- `tests/harness/claims/*` - VBUS-01/02/06 RED tests (12 tests, all xfail)
- `tests/harness/bus/*` - VBUS-04/05 RED tests (4 tests, xfail, V15-gated) + `bus_server_env` helper
- `tests/harness/test_env_injection.py` - VBUS-03 CLI-side scaffold (2 xfail)
- `tests/harness/test_coordination_doc.py` - VBUS-07 doc + --help scaffold (3 xfail)
- `tests/harness/test_coherence_guard.py` - VBUS-08 guard (3 PASS)
- `pyproject.toml` - registered `integration` pytest marker

## Decisions Made
See frontmatter key-decisions. Notably: `_require_*()` guards keep conflict-exit-code asserts from XPASSing against an unimported module.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `CliRunner(mix_stderr=False)` invalid on click 8.3.3**
- **Found during:** Task 1
- **Issue:** Plan prescribed `CliRunner(mix_stderr=False)`; click 8.2+ removed the param (stderr is always separate now)
- **Fix:** Plain `CliRunner()`; `result.stderr` works as intended
- **Verification:** Collection + run clean
- **Committed in:** 2cf60ef

**2. [Rule 3 - Blocking] `integration` marker unregistered under `--strict-markers`**
- **Found during:** Task 1 (test_claims_concurrent.py)
- **Issue:** Plan mandates `@pytest.mark.integration`; pyproject's `--strict-markers` would error collection on unregistered markers
- **Fix:** Added `integration` to `[tool.pytest.ini_options] markers`
- **Files modified:** pyproject.toml
- **Committed in:** 2cf60ef

**3. [Rule 1 - Wrong assumption] watchdog already a pyproject dependency**
- **Found during:** Task 3 (coherence guard)
- **Issue:** Plan expected 0 fs-watcher matches in pyproject; `watchdog>=4.0,<7` pre-exists twice (runtime + dev)
- **Fix:** Guard asserts the comment-filtered watchdog count equals the baseline of 2 and zero hits for chokidar/watchfiles/fs-watcher/fsevents; package.json watcher set must be empty
- **Verification:** Guard passes today; a new watcher entry changes the count → RED
- **Committed in:** 0959609

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 wrong assumption)
**Impact on plan:** All necessary for collection/correctness. No scope creep.

## Issues Encountered
None beyond the deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- V17-02 (overlap helpers) and V17-03 (claims verbs) have concrete RED targets; turning them GREEN means removing the module xfail marks in tests/harness/claims/ (+ test_env_injection.py for V17-04, test_coordination_doc.py for V17-07)
- Bus plans (V17-05/06) stay xfail until V15 ships; `bus_server_env` helper ready for them
- Coherence guard runs green in every suite invocation from now until phase end

---
*Phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot*
*Completed: 2026-06-10*
