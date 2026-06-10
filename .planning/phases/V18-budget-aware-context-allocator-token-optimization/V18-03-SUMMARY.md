---
phase: V18-budget-aware-context-allocator-token-optimization
plan: 03
status: complete
date: 2026-06-10
commits:
  - 2b34533 feat(V18-03): wire allocator at agent.py seam — packing_enabled, [context] config, --no-pack
requirements: [VOPT-03, VOPT-06]
---

# V18-03 Summary — Agent Seam + Config + Escape Hatch

## What landed

- **agent.py**: `packing_enabled: bool = True` on `run_turn` and `_run_turn_exec`, threaded through. Allocator + `get_packing_profile()` resolved ONCE before the while-loop (Pitfall 1 — stable-region state persists). Seam at the replay chokepoint is `if all_iter_records and not _packing_disabled:` → `_allocator.pack(...)`; the else branch is the original four-line `for prior in all_iter_records` loop **verbatim** (byte-identity by code path). `packing_budget = max(token_budget - reserve, 0)` where reserve = cached-prefix est + rider est + user-prompt est + `cfg.max_output_tokens`. sys_blocks never enters the allocator; M13 steer block and the ctx.token_budget halt untouched. Env/config/flag-disabled packing now records ledger method `no-pack`, not `full`.
- **config.py**: `_CONTEXT_BLOCK` regex, `_parse_context_section` (quoted + bare kv), `load_context_config`, `get_packing_profile` (int/float/bool coercion, range validation, warn+default, never raises; conservative defaults). Invalid `recent_full_k`, `digest_cutoff_m`, or high/low watermarks fall back to defaults.
- **cli.py**: `--no-pack` (is_flag, envvar `VOSS_NO_PACK`) on `do_cmd`, threaded as `packing_enabled=not no_pack` into the do_cmd run_turn call. REPL run_turn calls (:2137/:2228) left at default per plan.

## Deviation

- `test_cache_coherence_steady_state` needed `configure(max_iterations=12)` — runtime default cap of 8 truncated the scripted 10-iteration run (turn exited `max-iter` at 8). The `_reset_runtime` autouse fixture restores config. Test-side fix; production untouched.

## Verification

- `test_agent_packing.py` 3/3 GREEN (byte-identity, prefix-unchanged, steady-state cache reads > 0 with packing on).
- Regression: `test_agent_loop.py`, `test_voss_loop_parity.py`, `test_harness_config.py`, `test_context_allocator.py` all green (31 passed, 1 expected xfail).
- `voss do --help` lists `--no-pack`; `VOSS_NO_PACK=1 ... do --help` parses clean.
- Config acceptance: defaults k=8/hw=0.80/enabled=True with no [context] block; `enabled=false`/`recent_full_k=4`/`high_water=0.9` parse as strings via bare-kv matcher; invalid/out-of-order profile values warn and fall back.
