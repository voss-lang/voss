---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 07
subsystem: memory
tags: [memory, cli, pins, telemetry, reindex, operator-surface, VRNK-07]

# Dependency graph
requires:
  - phase: V23-05
    provides: _load_pins/_save_pins/reindex/ReindexResult + .pins.json schema
  - phase: V23-02
    provides: _load_telemetry_compacted (list/show telemetry columns)
provides:
  - voss memory pin/unpin/show/list/reindex verbs under the existing memory_group
  - Operator visibility into pins + telemetry + the reindex drift gate (sync --check exit contract)
affects: [operators; closes the VRNK-01..07 feature set]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Locator validation against _VALID_PIN_PREFIXES + backing-row existence before any .pins.json write (path-injection guard, T-V23-07-01)"
    - "reindex verb mirrors `voss sync --check`: chroma-absent no-op exit 0; --check drift → list + SystemExit(1); clean → exit 0"
    - "Verbs delegate to store methods; --global resolves via make_global_store (D-12)"

key-files:
  created: []
  modified:
    - voss/harness/memory_cli.py
    - tests/memory/test_retrieval_ranking.py

key-decisions:
  - "Shared _memory_store_for / _read_pins_raw / _locator_exists / _locator_body helpers to DRY 5 verbs (existing verbs duplicate the resolve block; helpers keep the new surface readable)"
  - "reindex --check echoes stale locators to STDOUT (not stderr) so the exit-1 listing is robustly capturable across click versions; exit code is the contract"
  - "pin is idempotent (already-pinned → success no-op); unpin/show on unknown locator → exit 1 stderr (VRNK-07 contract)"

patterns-established:
  - "list builds rows from _bm25_corpus(None) (file/line enumeration) unioned with pinned locators; columns locator/source/retrieval_count/last_retrieved/pin; --source/--pinned/--json filters"

requirements-completed: [VRNK-07]

# Metrics
completed: 2026-06-14
---

# Phase V23 Plan 07: Operator CLI verbs (VRNK-07) Summary

**Five `voss memory` verbs surface the pins (V23-05) and telemetry (V23-02) that were otherwise operator-invisible, and expose the reindex drift gate with the `voss sync --check` exit contract. Completes the VRNK-01..07 feature set.**

## Accomplishments
- `pin <locator>` / `unpin <locator>` — validate locator (known prefix + backing row) then toggle `.pins.json` via `_read_pins_raw`/`_save_pins`; idempotent pin; unknown/not-pinned → exit 1.
- `show <locator>` — full body (D-14) + `retrieval_count`/`last_retrieved` (from `_load_telemetry_compacted`) + pin flag; unknown → exit 1.
- `list [--source] [--pinned] [--json]` — rows from `_bm25_corpus` ∪ pins with telemetry + pin columns; empty → `(none)` exit 0; only missing-store → exit 1.
- `reindex [--check]` — delegates to `store.reindex`; chroma-absent no-op exit 0; `--check` drift → lists stale + `SystemExit(1)`; clean → exit 0; bare → `re-embedded: N`.
- All verbs accept `--global` (D-12) via `make_global_store`.

## Files Modified
- `voss/harness/memory_cli.py` — `import json`; helpers + 5 commands.
- `tests/memory/test_retrieval_ranking.py` — added `test_reindex_cli_check_exit_1_on_drift` (CLI verb + exit contract).

## Decisions Made
- **Stale listing to stdout.** `reindex --check` echoes stale locators to stdout (the SystemExit(1) is the contract) so the listing is capturable regardless of click's stderr-merge behavior across versions.
- **Validation before write.** `_locator_exists` checks prefix ∈ {turn,ledger,decision,convention,note} AND a backing row exists, rejecting `pin "../.."` style injection (T-V23-07-01).

## Deviations from Plan
- `files_modified` expanded to the test file to add the CLI reindex test (V23-05 had moved the reindex tests to store-level; the CLI verb's exit contract gets its own test here).

## Issues Encountered
- 5 failures in `tests/harness/test_memory_global.py` are **pre-existing** (V21 not merged) — confirmed by stashing all my edits and re-running (still 5 failed). Root cause: `attach_memory_tools() got an unexpected keyword argument 'global_store'` — a V21 surface absent from this tree. This independently confirms the V23 global-store xfail is correct (no global path to wire yet).

## Verification
- VRNK-07 GREEN: `-k "cli or pin or reindex or drift or show or unknown"` → 11 passed, 1 xfailed, 0 failed.
- Greps: pin/unpin/show ×3, list/reindex ×2, `--global` ×7 (≥3), `SystemExit(1)` ×1.
- **Full V23 module: 21 passed, 1 xfailed, 0 failed** — every VRNK-01..07 test green; only the V21-gated global pin dual-fusion stays xfail.
- Broad memory sweep (store/eviction/vacuum/tools + all tests/memory): **57 passed, 1 xfailed, 0 failed**.

## Next Phase Readiness
VRNK-01..07 complete and green. V23-08 is the regression-gate plan (existing memory + code_recall suites green; no frozen-schema drift; byte-identical baseline). The V21-gated global pin path remains the one xfail, un-xfailed when V21 lands.

---
*Phase: V23-retrieval-aware-memory-ranking-hygiene*
*Completed: 2026-06-14*
