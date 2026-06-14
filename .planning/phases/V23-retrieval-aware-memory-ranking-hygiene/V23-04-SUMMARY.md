---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 04
subsystem: memory
tags: [memory, retrieval, rescore, recency, frequency, telemetry, VRNK-03]

# Dependency graph
requires:
  - phase: V23-02
    provides: _load_telemetry_compacted ({locator: {count, last_retrieved}})
  - phase: V23-03
    provides: floored hit lists (rescore operates on post-floor output)
provides:
  - MemoryStore._rescore (deterministic recency×frequency multiplicative boost, bounded)
  - Config-gated rescore hook in recall() (default OFF; byte-identical off-path)
affects: [E-track quality eval (flip-on proposal), V23-08 byte-identical regression gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Rescore is a config-gated multiplicative boost on the final hit list; OFF returns `fused` untouched → byte-identical to pre-V23"
    - "Boost bounded [1.0, 1+w_recency+w_freq] so similarity dominates; telemetry only breaks near-ties (D-13)"
    - "recall() restructured to a single hooked return so BOTH the fused and BM25-only-degraded paths route through rescore"

key-files:
  created: []
  modified:
    - voss/harness/memory_store.py
    - tests/memory/test_retrieval_ranking.py

key-decisions:
  - "Rescore hook applied on BOTH paths (fused + chroma-absent BM25-only), not fusion-only. The plan offered the choice; BM25-only is required because the unit tests run chroma-disabled and would otherwise never rescore."
  - "Off-path byte-identical preserved: when rescore=False, `fused` is the exact value each old branch returned; only an added _load_memory_config() read + a no-op `if` run (plan-sanctioned)."
  - "Corrupt/naive last_retrieved guarded (ValueError, TypeError) → recency 0.0 (Pitfall 5 + aware/naive datetime subtraction safety)."

patterns-established:
  - "Deterministic re-rank is asserted on an equal-score TIE (telemetry breaks it), not a score gap — a bounded boost cannot override real similarity separation"

requirements-completed: [VRNK-03]

# Metrics
completed: 2026-06-14
---

# Phase V23 Plan 04: Recency×frequency rescore (VRNK-03) Summary

**Telemetry becomes ranking signal: a config-gated, deterministic recency×frequency boost lifts hot memories, while the default-OFF path stays byte-identical to pre-V23 (the hard VRNK-08 regression gate). Empty telemetry + rescore-on is a no-op.**

## Accomplishments
- `MemoryStore._rescore(hits, cfg)` — empty-telemetry no-op; per-hit `boost = 1 + w_recency*exp(-days/half_life) + w_freq*min(log1p(count)/log1p(freq_scale), 1)`; bounded so similarity dominates; deterministic with `(-score, locator)` tie-break; pure.
- Config-gated hook in `recall()` after the fused/BM25-only branches converge: `if cfg.get("rescore", False): fused = self._rescore(fused, cfg)`. Default OFF → byte-identical output.
- `import math` added (stdlib, no install).
- Weights configurable under `[memory]`: `rescore`, `rescore_half_life_days` (7.0), `rescore_w_recency` (0.3), `rescore_w_freq` (0.2), `rescore_freq_scale` (10.0).

## Files Modified
- `voss/harness/memory_store.py` — `import math`; `recall()` restructured to a single hooked return; `_rescore` after `_rrf_merge`.
- `tests/memory/test_retrieval_ranking.py` — corrected `test_rescore_deterministic_under_fixture`.

## Decisions Made
- **Hook on both paths.** Tests run BM25-only (autouse `_no_chroma`), so the `chroma is None` early-return would bypass a fusion-only hook and never rescore. Restructured `recall()` so every branch assigns `fused` then hits one rescore hook. Verified byte-identical off-path preserved.
- **Deterministic test on a tie.** My V23-01 test favoured B where A held a 2× lexical lead; a bounded boost (≤~1.5×) cannot flip that (and shouldn't — D-13). Rewrote to two identical-score docs where telemetry deterministically breaks the tie (B boosted above A).

## Deviations from Plan
- `files_modified` expanded to `tests/memory/test_retrieval_ranking.py` (plan listed only memory_store.py) — same scaffold-correction rationale as V23-03; the original deterministic assertion was unsatisfiable under a bounded boost.
- recall() restructured (3 returns → 1 hooked return) rather than a literal "replace the final return"; required for BM25-only rescore + still byte-identical when off.

## Verification
- VRNK-03 GREEN: `-k "rescore or byte_identical"` → 3 passed (deterministic, off-byte-identical, empty-telemetry no-op).
- Greps: `def _rescore` ×1, `^import math` ×1, `if cfg.get("rescore"` ×1.
- Broad memory regression sweep: **36 passed, 0 failed** — byte-identical recall baseline intact through the recall() restructure.
- Module posture: 10 failed / 10 passed / 1 xfailed (was 11/9/1) — rescore-deterministic flipped +1 green.

## Next Phase Readiness
Telemetry now drives both rescore (VRNK-03) and the upcoming retrieval-aware eviction (VRNK-04, V23-05, reads `last_retrieved`). Remaining RED: eviction×2, reindex×3, pins×3, CLI verbs.

---
*Phase: V23-retrieval-aware-memory-ranking-hygiene*
*Completed: 2026-06-14*
