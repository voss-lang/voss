---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 06
subsystem: memory
tags: [memory, pins, context-injection, agent-compose, run-turn, VRNK-06]

# Dependency graph
requires:
  - phase: V23-05
    provides: _load_pins / _save_pins / .pins.json committed schema; pinned eviction exemption
  - phase: V18/V19
    provides: _compose_system_blocks variable region, _default_token_count, code_recall_text threading + signature-guard idiom
provides:
  - MemoryStore.render_pinned_memory_text (full body per pin, per-item + tier token caps, newest-wins overflow + warn)
  - pinned_memory_text threaded through agent._compose_system_blocks + run_turn + _run_turn_exec (non-evictable cacheable-prefix block)
  - cli._pinned_memory_kwargs signature-guarded splat at all 3 run_turn call sites
affects: [V23-07 pin/unpin/list/show CLI verbs (write pins this renders); post-V21 global-store pin fusion]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pin block injected in the cacheable static prefix (ahead of the evictable code_recall slot) → fixed-cost, never folded/evicted (D-07)"
    - "Signature-guarded kwarg splat (inspect.signature) keeps compiled loop.voss run_turn variants TypeError-safe (V18 gotcha)"
    - "Pins are an independent injection path — never routed through recall(), no telemetry recorded"

key-files:
  created: []
  modified:
    - voss/harness/memory_store.py
    - voss/harness/agent.py
    - voss/harness/cli.py
    - tests/memory/test_retrieval_ranking.py

key-decisions:
  - "Pin block placed before code_recall_text in _compose_system_blocks (cacheable prefix = fixed-cost), satisfying D-07 non-evictability without a new region type"
  - "_pinned_memory_kwargs takes cwd (builds MemoryStore internally) like _code_recall_kwargs — works at all 3 sites with just cwd+model, no store var threading"
  - "Global-store pin dual-fusion (D-09) STUBBED with a TODO; no global_store auto-injection site exists in this tree (only the V23-02 comment) → the V21-gated xfail stays xfail"

patterns-established:
  - "Renderer overflow: newest-pinned (pinned_at desc) kept under tier cap, oldest dropped + one stderr warning; per-item soft-cap by char-budget proxy"

requirements-completed: [VRNK-06]

# Metrics
completed: 2026-06-14
---

# Phase V23 Plan 06: Pinned-tier injection (VRNK-06) Summary

**Operator-pinned memories always inject into agent context without competing through recall — a non-evictable fixed-cost block in the existing V18/V19 variable region, capped at ~500 tok tier / ~200 tok per item with newest-wins overflow + warning. Pinned files are already eviction-exempt (V23-05).**

## Accomplishments
- `MemoryStore.render_pinned_memory_text(model=...)` — full body per pin (no excerpt truncation, D-08); per-item soft cap (`pin_item_cap_tokens` 200) + tier cap (`pin_cap_tokens` 500); newest-pinned kept on overflow, oldest dropped + one stderr warning; "" when no pins. `_read_pinned_body` resolves locator→file. Token accounting via `_default_token_count` (lazy import, no cycle).
- `pinned_memory_text` param threaded: `_compose_system_blocks` (block placed ahead of the evictable code_recall slot → non-evictable), `run_turn`, `_run_turn_exec`.
- `cli._pinned_memory_kwargs(run_turn, cwd, model=...)` — inspect.signature guard (compiled-loop safe) → renders + splats only when accepted + non-empty. Wired at all 3 run_turn sites (do_cmd + 2 chat).

## Files Modified
- `voss/harness/memory_store.py` — `_read_pinned_body` + `render_pinned_memory_text`.
- `voss/harness/agent.py` — `pinned_memory_text` param ×3 (compose/run_turn/_run_turn_exec) + block-tuple insertion.
- `voss/harness/cli.py` — `_pinned_memory_kwargs` def + 3 call-site splats.
- `tests/memory/test_retrieval_ranking.py` — rewrote the 2 VRNK-06 pin tests to the renderer contract.

## Decisions Made
- **Pin tests retargeted to the renderer.** V23-01's pin tests assumed `_load_pins()` returned dicts and capped on load; it returns a locator set and caps live in the renderer. `test_pinned_memory_always_injected` now asserts `render_pinned_memory_text` contains the pin body (+ that recall of an unrelated query is empty → independent path). `test_pin_cap_overflow_warns` seeds 8 large distinct pins and asserts newest (PINID7) kept, oldest (PINID0) dropped, "dropped" warned.
- **Global path stubbed.** No global-store auto-injection site exists yet (grep: only the V23-02 comment). The V21-gated `test_pinned_global_store_dual_fusion` stays xfail; a TODO marks the merge point in the renderer.

## Deviations from Plan
- `_pinned_memory_kwargs` takes `cwd` not a `store` instance (mirrors `_code_recall_kwargs`) — avoids store-var availability differences across the 3 sites.
- `files_modified` expanded to the test file (pin-test retargeting), per the V23-01 contract note.

## Issues Encountered
- 3 failures in `tests/harness/tui/test_cli_integration.py` (install_tui / no_unicode) are **pre-existing** — confirmed by stashing my cli/agent/store edits and re-running (still failed). Unrelated to pinned-memory (different code path).
- Plan's `-k pin` acceptance also matches `test_pin_unpin_list_cli` (a VRNK-07 CLI verb test, RED until V23-07) — keyword collision; the 3 actual VRNK-06 tests are green.

## Verification
- VRNK-06 GREEN: `test_pinned_memory_always_injected`, `test_pin_cap_overflow_warns`, `test_pinned_survives_over_quota_eviction` pass; global dual-fusion xfailed (V21 pending).
- Greps: `pin_cap_tokens`/`pin_item_cap_tokens` ×3; `_default_token_count` in memory_store ×3; `pinned_memory_text` in agent.py ×6; `_pinned_memory_kwargs` in cli.py ×4; `_record_telemetry` in cli.py **0** (recall stays no-touch).
- Regression: `test_agent_packing.py` 4 passed (byte-identical prefix intact); broad memory sweep 36 passed, 0 failed.
- Module posture: 3 failed / 17 passed / 1 xfailed (was 5/15/1) — 2 pin tests flipped green. Remaining 3 = VRNK-07 CLI verbs.

## Next Phase Readiness
Pin injection live. V23-07 adds the `pin/unpin/list/show` (+ `reindex`) CLI verbs that write the `.pins.json` this renderer consumes — turning the last 3 RED tests green.

---
*Phase: V23-retrieval-aware-memory-ranking-hygiene*
*Completed: 2026-06-14*
