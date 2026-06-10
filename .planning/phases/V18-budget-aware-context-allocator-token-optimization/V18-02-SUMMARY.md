---
phase: V18-budget-aware-context-allocator-token-optimization
plan: 02
status: complete
date: 2026-06-10
commits:
  - abe4e6f (bundled by concurrent auto-commit process; allocator authored this session)
requirements: [VOPT-01, VOPT-02, VOPT-03, VOPT-04]
---

# V18-02 Summary — Pure ContextAllocator

## What landed

`voss/harness/context_allocator.py` — allocator unit tests GREEN.

- **PackingProfile** dataclass: recent_full_k=8, digest_cutoff_m=20, high_water=0.80, low_water=0.60, enabled=True.
- **FULL tier** delegates to `agent._serialize_iter_for_replay` via lazy import (`_full_renderer()`) — no re-implementation, redaction + 400-char caps preserved, below-threshold output byte-identical (early return when n <= recent_full_k).
- **DIGEST tier** mirrors the rider format: `[digest] Iter {i}: {steps} steps, {tools} tools, {snippet[:120]}` with a tiny user msg. Per-iter Pitfall-4 fallback: if a digest would cost more tokens than the full pair, render full.
- **FOLD tier** = single "Earlier work summary" pair: index range + union of tool names + eviction pointers (`↻ re-fetch via code_search("path")` / `find_definition("symbol")`), deduped via dict.fromkeys, capped at 5. Whole-fold Pitfall-4 fallback to full pairs.
- **Hysteresis (VOPT-03)**: stable region = frozen FOLD pairs. First pack with n > K seeds the fold boundary age-based (baseline). Below high_water the frozen fold is returned verbatim (append-only); at est >= high_water*budget, recompaction re-folds and absorbs digests oldest-first until est <= low_water*budget. `stable_region_hash()` = SHA-256 of frozen pairs — changes exactly once per crossing.
- **Hard ceiling guard (review fix)**: after normal full/digest/fold selection, `_fit_to_budget` guarantees the returned replay region does not exceed `packing_budget`; tiny/zero replay budgets degrade to the largest suffix that fits, a minimal omission note, or an empty replay.
- Purity: stdlib only (hashlib/json/dataclasses/typing); token_count injected; no fs/model-client/os/pathlib; gates verified (AST import scan + greps all 0).

## Design decision (recorded)

Stable region = FOLD only, digest boundary slides per turn. A fully-frozen prefix (fold+digest) would break test_stable_region_append_only (the first digest at n=9 would change the hash). The fold carries the bulk content; digest lines are deterministic one-liners. Recompaction is the only event that rewrites stable bytes.

## Verification

- `pytest tests/harness/test_context_allocator.py -q` → green, including tiny-budget ceiling coverage.
- AST gate: imports = `__future__, dataclasses, typing, voss.harness.agent` (lazy, function-scope for agent).
- `grep -Ec "chromadb|faiss|annoy|embedding|sentence_transformers|numpy"` → 0; `grep -Ec "open\(|pathlib|import os\b|requests|provider"` → 0.

## Note

Commit was swept into concurrent auto-commit `abe4e6f` (bundled with unrelated OpenAIOAuthProvider edit) — known repo behavior; verified via `git log -- voss/harness/context_allocator.py`.
