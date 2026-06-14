---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 03
subsystem: memory
tags: [memory, retrieval, floors, bm25, chroma, rrf, VRNK-02]

# Dependency graph
requires:
  - phase: V23-02
    provides: telemetry substrate + V23 RED scaffold (floor tests)
  - phase: M8 memory store
    provides: _bm25_recall, _chroma_recall, _rrf_merge, _load_memory_config
provides:
  - Pre-fusion BM25 relative-to-top floor (bm25_floor_ratio, default 0.1) at _bm25_recall tail
  - Pre-fusion chroma absolute similarity floor (chroma_floor, default 0.25) at _chroma_recall tail
  - Disable knobs (set either to 0) restoring pre-V23 fill
affects: [V23-04 rescore (operates on floored hits), V23 token-budget hygiene]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Floors are per-retriever pre-fusion (D-06): _rrf_merge stays a config-free staticmethod; a post-fusion floor would punish BM25-only installs"
    - "BM25 floor is relative-to-top (ratio), chroma floor is absolute (similarity) — different shapes per D-04/D-05"
    - "Tiny corpora score via the token-overlap rescue (integer = distinct query tokens matched), NOT graded BM25 — tests must account for this"

key-files:
  created: []
  modified:
    - voss/harness/memory_store.py
    - tests/memory/test_retrieval_ranking.py

key-decisions:
  - "BM25 floor guarded by `ranked and ranked[0][0] > 0 and ratio > 0` (Pitfall 4: a zero top would pass everything)"
  - "float(cfg.get(...)) wrapped in try/except → default, so a malformed config value can never crash recall (T-V23-03-01)"
  - "Corrected the scaffold floor tests: the relative BM25 floor CANNOT zero-out a corpus of equal-scoring docs (my V23-01 'ubiquitous token → 0' assumption was wrong). Rewrote to a strong/weak design that the floor actually discriminates."

patterns-established:
  - "12-distinct-term query → strong matches all (overlap 12), weak matches 1 → weak below 10%-of-top cutoff; the deterministic way to exercise a relative floor in a rescue-scored tiny corpus"

requirements-completed: [VRNK-02]

# Metrics
completed: 2026-06-14
---

# Phase V23 Plan 03: Pre-fusion relevance floors (VRNK-02) Summary

**Each retriever now drops low-quality hits BEFORE `_rrf_merge`: chroma absolute similarity < 0.25 and BM25 < 10% of the query's top score are floored out, so a junk query returns 0 hits instead of filling top_k with nearest-anything. Default-on, config-overridable under `[memory]`, with a disable knob restoring pre-V23 fill.**

## Accomplishments
- BM25 relative-to-top floor at the `_bm25_recall` tail: `bm25_floor_ratio` (default 0.1), zero-top guard, ratio=0 disables. Token-overlap rescue rows compare naturally against the cutoff.
- Chroma absolute floor at the `_chroma_recall` tail: `chroma_floor` (default 0.25, not froots' 0.45), 0 disables. This is what converts a junk query into 0 hits when chroma is present.
- `_rrf_merge` staticmethod untouched (verified config-free) — floors are strictly per-retriever pre-fusion (D-06).
- Both reads via `_load_memory_config()`; malformed values fall back to defaults (no recall crash).

## Files Modified
- `voss/harness/memory_store.py` — floor blocks at the two retriever tails.
- `tests/memory/test_retrieval_ranking.py` — corrected the two scaffold floor tests + added `test_bm25_floor_drops_weak_matches`.

## Decisions Made
- **Floor test correction (necessary scaffold fix).** The V23-01 floor tests assumed a query over equal-scoring docs would floor to 0. A *relative-to-top* BM25 floor can never do that — the top always clears its own cutoff, so equal scores all survive. Empirically, tiny corpora also score via the integer token-overlap rescue, not graded BM25. Rewrote the tests around a strong (matches all 12 query terms → score 12) vs weak (matches 1 → score 1, below the 1.2 cutoff) design that the relative floor genuinely discriminates, plus a true-no-overlap query for the no-match→0 contract.

## Deviations from Plan
- `files_modified` expanded to include `tests/memory/test_retrieval_ranking.py` (plan listed only memory_store.py). Required: the scaffold floor tests were semantically incompatible with the relative-floor design and would have blocked VRNK-02 green. Flagged per the V23-01 contract note ("a plan that picks a different mechanism must update the matching test, not leave it RED"). Net floor tests 2→3 (module 20→21).
- Chroma floor is exercised by code inspection + the no-match contract, not a live-chroma unit test — tests run BM25-only via autouse `_no_chroma` (Pitfall 3: no DefaultEmbeddingFunction in test env).

## Verification
- VRNK-02 floor tests GREEN: 3 passed (`-k floor`).
- `_rrf_merge` config-free (awk scan between `def _rrf_merge` and `def _chroma_recall`: 0 `_load_memory_config` leaks).
- Greps: `bm25_floor_ratio` ×5, `chroma_floor` ×6, zero-top guard `ranked[0][0] > 0` ×1.
- Broad memory regression sweep (store/eviction/vacuum/tools + tests/memory existing): **36 passed, 0 failed** — byte-identical recall baseline intact for matched queries.
- Module posture: 11 failed / 9 passed / 1 xfailed (was 12/7/1) — floors flipped net +2 green.

## Next Phase Readiness
Floored hit lists feed V23-04 rescore. Remaining RED: rescore-deterministic, eviction×2, reindex×3, pins×3, CLI verbs.

---
*Phase: V23-retrieval-aware-memory-ranking-hygiene*
*Completed: 2026-06-14*
