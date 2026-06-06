---
phase: V2-principles-layer
plan: 02
subsystem: agent
tags: [principles, system-prompt, injection, cache-prefix, overflow, renderer]

requires:
  - phase: V2-01
    provides: "resolve_principles / PrinciplesConfig (the active merged principle set)"
provides:
  - "## Principles injected as a distinct cacheable block in the voss do/chat system prefix (VPRIN-04)"
  - "PRINCIPLES_BUDGET_TOKENS=1000 cap with deterministic end-of-list truncation"
  - "show_principles_overflow renderer event across all Renderer impls + typed server event"
affects: [V2-03 show/opacity guard, V3/V6/V7 role-context injection]

tech-stack:
  added: []
  patterns:
    - "Mirror cognition's budget→measure→truncate→overflow-event pattern for the principles block"

key-files:
  created:
    - tests/harness/test_principles_injection.py
  modified:
    - voss/harness/agent.py
    - voss/harness/render.py
    - voss/harness/tui/renderer.py
    - voss/harness/server/renderer.py
    - voss/harness/server/events.py

key-decisions:
  - "Principles block slotted immediately AFTER cognition_text in _compose_system_blocks (its own block, inside the cacheable prefix + trailing cache_control)"
  - "Overflow truncation: drop whole principles from the END of the ordered list until under budget + append '(principles truncated due to budget)' — earlier/default principles survive deterministically"
  - "Block body is opaque: iterate config.principles, one bullet per principle, never branch on a key"

patterns-established:
  - "principles_overflow event id mirrors cognition_overflow across every renderer + the server event union"

requirements-completed: [VPRIN-04]

duration: 30min
completed: 2026-06-06
---

# Phase V2-02: Principles Layer — Injection Summary

**Resolved principles inject as a distinct, capped `## Principles` block into the `voss do`/`voss chat` cacheable system prefix, with a ~1k-token budget that truncates deterministically and emits a `principles_overflow` event across every renderer.**

## Performance

- **Duration:** ~30 min (incl. Protocol-conformance fanout)
- **Tasks:** 2 / 2 (TDD)
- **Files modified:** 5 source + 1 test created

## Accomplishments

### Task 1 — show_principles_overflow renderer event
- Added `show_principles_overflow(*, principles_tokens, budget=1000)` to the `Renderer` Protocol and all impls in render.py (Tty/Compact/Plain/Json), mirroring `show_cognition_overflow`. Event id `principles_overflow`.

### Task 2 — compose + inject the capped block
- `PRINCIPLES_BUDGET_TOKENS = 1000` next to `COGNITION_BUDGET_TOKENS`.
- `_compose_principles_block(config, *, model, token_count_fn, renderer)` — `## Principles` heading + one bullet per principle (opaque); reuses `_default_token_count`; on overflow emits `show_principles_overflow` and drops principles from the end until under budget (+ marker).
- `_compose_system_blocks` gained `principles_text` slotted immediately after `cognition_text` (own block, inside falsy-filter + trailing `cache_control: ephemeral`).
- Call site composes `principles_text = _compose_principles_block(resolve_principles(cwd), ...)` and passes it in; imported `resolve_principles`.

## Verification

- `test_principles_injection.py` (8) green: overflow event shape; all-renderers-have-method; heading+defaults; overflow truncates+emits; under-budget keeps full; distinct-block (not merged); empty→no block.
- `test_agent_caching.py` green (cache-prefix block-list invariant intact).
- agent/render/principles regression slice green (X = pre-existing xpass).
- `PRINCIPLES_BUDGET_TOKENS = 1000` present; `principles_overflow` wired in render.py + agent.py; no new deps (pyproject clean).

## Deviations

- **Touched 3 files beyond the plan's `files_modified`:** `voss/harness/tui/renderer.py` (TextualRenderer), `voss/harness/server/renderer.py` (EventBusRenderer), and `voss/harness/server/events.py` (new `PrinciplesOverflow` typed event + union registration). Adding a method to the `runtime_checkable` `Renderer` Protocol breaks `isinstance(x, Renderer)` for EVERY impl that lacks it — `test_textual_renderer_protocol` and `test_server_renderer::test_satisfies_renderer_protocol` failed until those two renderers implemented the method (the server renderer's method→typed-event contract required the new event). Mechanical parity additions; no behavior change to existing events.
