---
phase: V22-external-memory-docs-ingest
plan: 01
subsystem: recall
tags: [external-memory, recall, scaffold, red-tests, fixtures]

requires:
  - phase: V19-semantic-code-memory-tiered-index-routing
    provides: CodeIndex patterns, semantic_index helpers, and recall test analogs
provides:
  - V22 external recall package skeleton
  - RED external_recall pytest scaffold
  - deterministic markdown fixture vault for external-source recall
affects: [V22-external-memory-docs-ingest, recall, memory]

tech-stack:
  added: []
  patterns: [deferred imports for RED collection, markdown fixture corpus]

key-files:
  created:
    - voss/harness/recall/__init__.py
    - voss/harness/recall/external_index.py
    - tests/external_recall/conftest.py
    - tests/external_recall/test_config.py
    - tests/external_recall/test_chunker.py
    - tests/external_recall/test_incremental.py
    - tests/external_recall/test_background.py
    - tests/external_recall/test_recall_cli.py
    - tests/external_recall/test_agent_tool.py
    - tests/external_recall/test_golden_queries.py
    - tests/fixtures/recall_vault/getting-started.md
    - tests/fixtures/recall_vault/api-reference.md
    - tests/fixtures/recall_vault/concepts/chunking.md
    - tests/fixtures/recall_vault/changelog.md
    - tests/fixtures/recall_vault/notes.txt
  modified: []

key-decisions:
  - "Closed out V22-01 from already-tracked scaffold files instead of duplicating code."
  - "Kept V22-01 intentionally RED at runtime for V22-02+ implementation work."

patterns-established:
  - "External recall tests defer imports into test and fixture bodies so collection stays green before implementation."
  - "Fixture vault uses distinct per-file vocabulary plus a non-markdown decoy for ingest filtering."

requirements-completed: [VXMEM-01, VXMEM-02, VXMEM-03, VXMEM-04, VXMEM-05, VXMEM-06, VXMEM-07, VXMEM-08]

duration: 45 min
completed: 2026-06-13
---

# Phase V22 Plan 01: External Recall RED Scaffold Summary

**External recall package contracts, RED test scaffold, and deterministic markdown fixture vault are in place for V22 implementation waves.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-06-13T16:37:00Z
- **Completed:** 2026-06-13T17:22:09Z
- **Tasks:** 3
- **Files modified:** 0 new diffs in this closeout; scaffold files were already tracked

## Accomplishments

- Verified `voss.harness.recall` exports `ExternalSourceIndex`, `ExternalRecallService`, and `extract_md_chunks`.
- Verified `tests/external_recall/` collects successfully with 33 tests and no collection errors.
- Verified the fixture vault has the required markdown corpus, oversize chunking body, fenced `# comment`, preamble text, and `notes.txt` decoy.
- Confirmed the runtime RED signal is correct: config tests fail on missing `get_recall_sources`, and `extract_md_chunks("x")` raises `NotImplementedError("V22-02/03")`.

## Task Commits

The scaffold was already present in tracked history before this closeout:

1. **Task 1: Recall package skeleton** - present in `bc62e0b0` / `82342b09`
2. **Task 2: Fixture vault** - present in `bc62e0b0` / `82342b09`
3. **Task 3: External recall RED tests** - present in `bc62e0b0` / `82342b09`

**Plan metadata:** this summary commit records the V22-01 closeout and roadmap progress.

## Files Created/Modified

- `voss/harness/recall/__init__.py` - package export surface for V22 external recall.
- `voss/harness/recall/external_index.py` - signature-only contracts with `NotImplementedError("V22-02/03")`.
- `tests/external_recall/` - RED test suite for config, chunking, incremental indexing, background build, CLI recall, agent tool recall, and golden queries.
- `tests/fixtures/recall_vault/` - deterministic markdown fixture corpus plus non-markdown decoy.

## Decisions Made

- No production/test edits were made during closeout because the exact scaffold files were already tracked and verified.
- The absent referenced context files (`V22-SPEC.md`, `V22-CONTEXT.md`, `V22-RESEARCH.md`, `V22-VALIDATION.md`) were treated as a documentation artifact gap; the executable contract was recovered from `V22-01-PLAN.md`, downstream V22 plan files, the roadmap, and V19 analogs.

## Deviations from Plan

### Auto-fixed Issues

None - no implementation changes were required.

---

**Total deviations:** 1 closeout deviation (pre-existing scaffold with missing SUMMARY).
**Impact on plan:** Low. The scaffold artifacts satisfy V22-01; this summary repairs the GSD tracking gap without changing behavior.

## Issues Encountered

- `V22-01-SUMMARY.md` was missing even though the scaffold files were already tracked in prior commits. Closed out from verified disk state.
- The plan references V22 context/research/validation files that are not present in this checkout. Downstream plan files and `V22-01-PLAN.md` still contain the required test names, fixture details, and interfaces.

## Verification

- `.venv/bin/python -m pytest tests/external_recall/ --collect-only -q` - passed; 33 tests collected.
- `.venv/bin/python -c "from voss.harness.recall import ExternalSourceIndex, ExternalRecallService, extract_md_chunks; print('ok')"` - passed.
- `.venv/bin/python -c "from voss.harness.recall.external_index import extract_md_chunks; ..."` - passed; confirmed `NotImplementedError("V22-02/03")`.
- `.venv/bin/python -m pytest tests/external_recall/test_config.py -q` - RED as intended: 4 runtime ImportError failures for missing `get_recall_sources`; no collection failure.
- Fixture structural smoke - passed.
- `grep -v '^#' voss/harness/recall/external_index.py | grep -c 'import chromadb\|import sentence_transformers'` - returned `0` matches.
- `git diff --check` - passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for `V22-02-PLAN.md`: implement `get_recall_sources()` and `extract_md_chunks()` to turn the config and chunker tests green.

---
*Phase: V22-external-memory-docs-ingest*
*Completed: 2026-06-13*
