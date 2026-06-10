---
phase: V18-budget-aware-context-allocator-token-optimization
plan: 01
status: complete
date: 2026-06-10
commits:
  - 3bd3176 test(V18-01): RED allocator + packing integration stubs (VOPT-01/02/03/04/06)
  - 39d3c48 test(V18-01): RED savings-ledger + eval-gate stubs (VOPT-05/07)
requirements: [VOPT-01, VOPT-02, VOPT-03, VOPT-04, VOPT-05, VOPT-06, VOPT-07, VOPT-08]
---

# V18-01 Summary — Nyquist RED Scaffold

## What landed

Four test files under `tests/harness/`, 17 named tests, all RED for the right reason, zero collection errors:

| File | Tests | RED mechanism | GREEN target |
|------|-------|---------------|--------------|
| `test_context_allocator.py` | 8 | `ModuleNotFoundError: voss.harness.context_allocator` | Plan 02 |
| `test_agent_packing.py` | 3 | `TypeError: _run_turn_exec() got an unexpected keyword argument 'packing_enabled'` | Plan 03 |
| `test_savings_ledger.py` | 4 | ImportError on `recorder._append_savings_record` / `estimate_savings_usd`; `/cost` AssertionError (no `context packed:` line) | Plan 04 |
| `test_packing_eval_gate.py` | 2 | `ModuleNotFoundError: voss.harness.packing_eval` | Plan 05 |

## Test names (per V18-VALIDATION map)

- VOPT-01: `test_allocator_pure`, `test_pack_50_iters_under_ceiling`, `test_below_threshold_byte_identical`
- VOPT-02: `test_tier_boundaries_golden_render`, `test_packed_tokens_never_exceed_full`
- VOPT-03: `test_stable_region_append_only`, `test_recompaction_on_high_water` (pure); `test_cache_coherence_steady_state` (integration)
- VOPT-04: `test_eviction_pointer_emitted`
- VOPT-05: `test_ledger_packed_le_original`, `test_no_pack_zero_savings`, `test_cost_slash_prints_savings_line`, `test_saved_usd_nets_cache_reads`
- VOPT-06: `test_no_pack_byte_identical`, `test_cached_prefix_unchanged`
- VOPT-07: `test_quality_preservation_gate`, `test_aggressive_profile_fails_gate`

## Contracts pinned (later plans must conform)

- Plan 02: `ContextAllocator(token_count=callable)`, `.pack(iters, packing_budget, profile) -> list[tuple[dict, dict]]`, `.stable_region_hash() -> str`; `PackingProfile(recent_full_k=8, digest_cutoff_m=20, high_water=0.80, low_water=0.60, enabled=True)`. Digest marker `tools,` (SPEC `Iter i: <n> tools, <snippet>`); fold block contains `Earlier work` exactly once; pointer hints contain `re-fetch` + `code_search`, deduped, ≤5.
- Plan 03: `_run_turn_exec(..., packing_enabled: bool = True)`.
- Plan 04: `_append_savings_record(cwd: Path, session_id: str, record: dict)` writing `.voss/sessions/<id>/token-savings.jsonl` (RESEARCH A7 subdir convention); `estimate_savings_usd(saved_tokens, cache_read_tokens, model) -> float | None`; `/cost` prints `context packed:` line.
- Plan 05: `voss.harness.packing_eval.compare_runs(on=Path, off=Path, tolerance=float)` returning object with `.passed`; aggressive profile injected via `VOSS_PACK_RECENT_K` / `VOSS_PACK_DIGEST_M` env; off-run via `VOSS_NO_PACK=1`.

## Deviations

- `test_tier_boundaries_golden_render` uses 30 iters (not the plan's 20) — default profile M=20 leaves the fold tier empty at 20 iters; 30 populates all three tiers so the "Earlier work" assertion is meaningful.
- `test_cache_coherence_steady_state` passes `packing_enabled=True` so it is RED with the rest of the integration file (rather than green-pinning today's T4 behavior).
- Acceptance grep `xfail(strict=False)` initially matched docstring prose; reworded to "non-strict xfail" so the gate greps clean. No xfail of any kind used — all RED is ImportError/TypeError/AssertionError.

## Verification results

- `--collect-only` (all four files): 8 + 3 + 4 + 2 collected, zero errors.
- Full run: 17 failed (RED), exit non-zero, reasons verified per file above.
- `grep -rn "xfail(strict=False)"` over the four files: empty.
- `grep -c "def test_"` on test_context_allocator.py: 8.
- `TODO(Plan 05)` input-token-metric marker present in test_packing_eval_gate.py (runs.jsonl has no prompt_tokens — verified runner.py:358-377).
- Full pre-existing harness suite still collects: `pytest tests/harness/ --collect-only -q` exit 0.
