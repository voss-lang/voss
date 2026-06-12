---
phase: V19-semantic-code-memory-tiered-index-routing
plan: 01
subsystem: testing
tags: [nyquist, red-scaffold, semantic-index, code-recall, chroma]
requires: []
provides:
  - "tests/code_recall/ RED suite pinning VSEM-01..08 against the planned voss.harness.code.semantic_index API"
  - "Hit dataclass with line_start/line_end (shared contract for all V19 waves)"
  - "conftest fixtures: fake_embed_fn, indexed_fixture_repo, chroma_disabled_env, stub_provider"
affects: [V19-02, V19-03, V19-04, V19-05, V19-06]
tech-stack:
  added: []
  patterns:
    - "deferred in-body imports of unbuilt planned modules — ImportError IS the RED signal; collection stays clean"
    - "CountingEmbed/GatedEmbed DefaultEmbeddingFunction subclasses for embed-call counting and not-ready windows"
key-files:
  created:
    - tests/code_recall/__init__.py
    - tests/code_recall/conftest.py
    - tests/code_recall/test_chunker.py
    - tests/code_recall/test_incremental.py
    - tests/code_recall/test_background.py
    - tests/code_recall/test_code_recall_tool.py
    - tests/code_recall/test_recall_cli.py
    - tests/code_recall/test_injection.py
    - tests/code_recall/test_enrichment.py
    - tests/code_recall/test_golden_queries.py
  modified:
    - voss/harness/memory_store.py
key-decisions:
  - "Plain failing tests (no xfail at all) — ModuleNotFoundError/TypeError on planned APIs is the RED state; implemented features flip green naturally with zero marker churn"
  - "chroma_disabled_env patches SemanticMemory.__init__ to raise ModuleNotFoundError (construction-time absence) rather than CodeIndex._maybe_semantic — exercises the real lazy-import guard"
  - "stub_provider intercepts model_router.build_provider_for_model at the module attribute; impls must resolve via the module, not a from-import binding (documented in fixture docstring)"
  - "test_evictable pins the _compose_system_blocks(code_recall_text=...) contract standalone (no Wave-1 fixture dep) — RED via TypeError today, stays RED until V19-05 wires the param"
requirements-completed: [VSEM-01, VSEM-02, VSEM-03, VSEM-04, VSEM-05, VSEM-06, VSEM-07, VSEM-08]
duration: 25 min
completed: 2026-06-12
---

# Phase V19 Plan 01: Wave-0 RED Nyquist Scaffold Summary

Full RED test floor for V19 semantic code memory: 23 tests across 8 modules pinning VSEM-01..08 + the golden-query gate against the planned `voss.harness.code.semantic_index` API, plus the one shared-contract source change (`Hit.line_start`/`line_end`) every downstream plan implements against.

- Duration: ~25 min (commits 3720458 → 654d6ac, 2026-06-12)
- Tasks: 3/3 (Hit extension · marker+fixtures · 8 RED test files)
- Files: 10 created, 1 modified

## What Was Built

**Task 1 — Hit contract:** `Hit` gains trailing optionals `line_start`/`line_end` (memory hits leave both `None`; code hits populate). `_rrf_merge` untouched — `dataclasses.replace` and locator-dedup carry the fields through. `tests/memory/` stays green (12 passed).

**Task 2 — package + fixtures:** `tests/code_recall/conftest.py` exposes the four named fixtures (`fake_embed_fn`, `indexed_fixture_repo`, `chroma_disabled_env`, `stub_provider`) plus a shared 3-file `FIXTURE_FILES` repo with distinct per-file vocab (retry/backoff · json codec · cache eviction) so queries discriminate files. Planned imports pinned to the `<interfaces>` block exactly (`CodeIndex`, `CodeIndexService`, `extract_chunks`, `_chunk_id`, `attach_code_recall_tool`, `get_code_recall_config`, `get_index_enrich_model`, `_render_code_recall_text`).

**Task 3 — RED suite (verified state):** 21 non-slow tests run: 18 FAILED + 3 ERROR, **zero passes** — all failures are ModuleNotFoundError/TypeError/ImportError on the planned API. 2 slow-marked (`test_perf_p95`, `test_golden_concept_queries` with 12 concept-query pairs against real repo files). Collection 23/23 clean. `grep strict=False` → empty.

## Verification Log (acceptance gates)

- `pytest tests/code_recall/ --co -q` — 23 collected, no collection errors — PASS
- `pytest tests/code_recall/ -m "not slow"` — 18F+3E, 0 passes — PASS (RED state)
- `pytest tests/memory/ -q` — 12 passed — PASS (Hit extension non-breaking)
- `grep -rn strict=False tests/code_recall/` — empty — PASS
- planned-import grep — present in conftest + all 8 test modules — PASS
- `slow` marker in pyproject `[tool.pytest.ini_options].markers` — present — PASS
- VSEM-01..08 → ≥1 named test each (chunker/incremental/background/tool/cli/injection/enrichment) — PASS
- `test_targeted_rehash_on_fs_write` pins D-13 trigger #2 (queue_rehash targeted re-embed, not-ready no-op, non-blocking) — PASS

## Deviations from Plan

- **[Rule 1 - already satisfied] slow marker pre-registered** — Found during: Task 2 | `pyproject.toml` markers already contain `slow: takes > 1s` (`--strict-markers` compatible) | Fix: no edit; plan's `files_modified: pyproject.toml` not needed | Verification: tomllib readback shows `slow:` entry | No commit (no change).
- **[Environment - concurrent auto-committer] 6 test files absorbed mid-write as 757d834** — Found during: Task 3 close | the known concurrent process committed background/chunker/tool/incremental/injection/recall_cli under a mislabeled `feat(E4-02)` message before my Task 3 commit; remaining files (enrichment, golden_queries, evictable fix) landed in 654d6ac | Verification: `git diff 654d6ac -- tests/code_recall/ voss/harness/memory_store.py` empty; on-disk content is the verified RED suite | Impact: history split across 757d834+654d6ac; content correct.
- **requirements.mark-complete skipped** — VSEM reqs live in V19-SPEC.md, not REQUIREMENTS.md (V-track GSD SDK quirk, E4-01 precedent); scaffold seeds them rather than completing them — they go GREEN per-wave.

**Total deviations:** 3 (1 no-op, 1 environmental, 1 process). **Impact:** none on deliverables.

## Next Phase Readiness

Wave 1 (V19-02 CodeIndex/chunker) executes against a pre-written failing suite. Contracts most likely to bite implementers, pinned here on purpose: `extract_chunks(db_path, rel_path, content) -> [(line_start, line_end, text)]`, `_chunk_id` → `code:<rel>:<seq:03d>`, `build(session_id=...)` threading to the `.voss/sessions/<id>/token-savings.jsonl` ledger, stub interception requires module-attr resolution of `build_provider_for_model`, and `inject = false` ⇒ `_render_code_recall_text` returns `""`.

## Self-Check: PASSED
