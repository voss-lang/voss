---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 05
subsystem: memory
tags: [memory, eviction, pins, reindex, drift, manifest, sha256, VRNK-04, VRNK-05]

# Dependency graph
requires:
  - phase: V23-02
    provides: _load_telemetry_compacted (eviction reads last_retrieved); gitignore already lists .reindex-manifest.json
  - phase: M8 memory store
    provides: _maybe_evict, _locator_from_path, _maybe_chroma, vacuum
provides:
  - Retrieval-aware eviction (_eviction_key) — never-retrieved/stale evict before recently-retrieved; pinned exempt; mtime fallback
  - Pin primitives _load_pins/_save_pins + .pins.json committed schema (consumed by V23-06 injection + V23-07 CLI)
  - reindex() store method + ReindexResult + sha256 manifest helpers + file-based source walk
affects: [V23-06 pin injection, V23-07 pin/unpin/list/show/reindex CLI verbs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Eviction key is a 3-tuple (bucket, sort_ts, mtime): bucket 0 (cold) before bucket 1 (retrieved); ascending last_retrieved then mtime"
    - "No telemetry sidecar → every file bucket 0 → sort degrades to pre-V23 mtime ordering (back-compat)"
    - "reindex manifest mirrors V19 semantic_index (sha256 per relative path, json indent=0 sort_keys=True); upsert NOT add; chroma-absent = clean no-op"

key-files:
  created: []
  modified:
    - voss/harness/memory_store.py
    - tests/memory/test_retrieval_ranking.py

key-decisions:
  - "Pin filter applied AFTER the quota check — pinned bytes still count toward quota, pins just can't be eviction victims (loop over filtered files only)"
  - "reindex(check=True) is read-only (no embed, no manifest write); check=False upserts stale + rewrites manifest; chroma None → ReindexResult(chroma_available=False) no-op, never raises"
  - "Reindex scaffold tests converted CLI→store-level: this plan ships only the store method (CLI verb is V23-07), and VALIDATION maps reindex-green to V23-05"

patterns-established:
  - "Fake-chroma test double (_collection.upsert) lets drift/repair run with real chromadb absent; chroma-absent path uses the autouse _no_chroma None"

requirements-completed: [VRNK-04, VRNK-05]

# Metrics
completed: 2026-06-14
---

# Phase V23 Plan 05: Retrieval-aware eviction + reindex hygiene (VRNK-04/05) Summary

**Hot memories survive purges (retrieval-aware eviction with pin exemption + mtime fallback) and hand-edited mirror files stop serving stale embeddings (sha256 drift manifest + chroma re-embed via upsert). Also lands the pin primitives that VRNK-06 injection and VRNK-07 CLI verbs both consume.**

## Accomplishments
- `_eviction_key(path, telemetry)` 3-tuple ordering; `_maybe_evict` now drops pinned locators from candidates then sorts by the key. No sidecar → bucket-0 everywhere → pre-V23 mtime ordering. `decisions/` early-return preserved.
- Pin primitives `_load_pins() -> set[str]` / `_save_pins(...)` + `_pins_path`; committed `.pins.json` schema `{"pins":[{"locator","pinned_at"}]}` (NOT gitignored, D-02). Pin locators use `_locator_from_path` vocabulary (Pitfall 6).
- `reindex(*, check)` + `ReindexResult` + `_reindex_manifest_path`/`_load_reindex_manifest`/`_save_reindex_manifest` + `_file_based_sources` (notes/decisions/conventions only, D-10). sha256 manifest diff; upsert (not add); chroma-absent clean no-op. `_file_hash` module helper.

## Files Modified
- `voss/harness/memory_store.py` — `ReindexResult` + `_file_hash`; `_maybe_evict` sort-line swap; pin/eviction-key/reindex methods appended to the class.
- `tests/memory/test_retrieval_ranking.py` — converted 3 reindex tests CLI→store-level (+ `_FakeChroma`); fixed `_write_pins` to the committed `{"pins":[...]}` schema.

## Decisions Made
- **Reindex tests are store-level here.** This plan ships only `store.reindex(...)`; the `voss memory reindex` CLI verb is V23-07. VALIDATION maps reindex-green to V23-05, so the scaffold's CLI-based reindex tests were retargeted to the store API (the CLI verb test is added in V23-07). Real chromadb is absent in the test env, so drift/repair inject a `_FakeChroma`; the chroma-absent test uses the autouse `_no_chroma` None.
- **`_write_pins` helper schema fix.** The V23-01 helper wrote a bare list; `_load_pins` reads `{"pins":[...]}`. Aligned the helper to the committed schema (also unblocks `test_pinned_survives_over_quota_eviction`).

## Deviations from Plan
- `files_modified` expanded to the test file (plan listed only memory_store.py) — reindex test retargeting + pin-helper schema fix, per the V23-01 contract note.
- The two VRNK-06 pin tests (`test_pinned_memory_always_injected`, `test_pin_cap_overflow_warns`) still RED — they assume `_load_pins` returns dicts; it returns a set of locators. That assertion shape is corrected in V23-06 (their owning plan), not here.

## Verification
- VRNK-04/05 store tests GREEN: `-k "evict or reindex or drift"` → 6 passed (retrieval-aware evict, mtime fallback, pinned-survives-eviction, reindex drift/repair/chroma-absent).
- Greps: `_eviction_key`/`_load_pins`/`_save_pins` ×3; `reindex`/`_file_based_sources`/`_reindex_manifest_path` ×5; `clear_system_cache` 0 (Pitfall 2); `_collection.upsert` ×1, no new `add(`; decisions guard present; `.pins.json` not gitignored; `.reindex-manifest.json` gitignored.
- Existing eviction + vacuum suites: 7 passed. Broad memory sweep: **36 passed, 0 failed**.
- Module posture: 5 failed / 15 passed / 1 xfailed (was 10/10/1) — flipped 5 green. Remaining 5 = VRNK-06 pins (2) + VRNK-07 CLI (3).

## Next Phase Readiness
Pin primitives + reindex store logic ready. V23-06 wires pinned-memory context injection (+ fixes the 2 pin-shape tests); V23-07 surfaces pin/unpin/list/show/reindex CLI verbs.

---
*Phase: V23-retrieval-aware-memory-ranking-hygiene*
*Completed: 2026-06-14*
