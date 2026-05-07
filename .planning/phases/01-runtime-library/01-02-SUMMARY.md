---
phase: 01-runtime-library
plan: 02
subsystem: runtime
tags: [python, asyncio, dataclass, pydantic, contextvar, generics]

requires:
  - phase: 01-runtime-library/01-01
    provides: package skeleton, exceptions, config singleton, ModelProvider Protocol, StubProvider
provides:
  - ProbableValue[T] confidence-typed values with @ / gate / unwrap
  - BudgetScope async ctx mgr with token/cost/latency enforcement and ContextVar tracking
  - ContextScope with token-counted add, oldest-first summarize compression, typed ask routing
  - run_with_budget helper wrapping asyncio.wait_for for latency budgets
affects: [agents, memory, codegen, ctx.ask call sites]

tech-stack:
  added: []
  patterns:
    - "ContextVar-based scope tracking for nested async budgets"
    - "Provider-agnostic token counting via ModelProvider.count_tokens"
    - "Compressor as injectable async callable for testability"

key-files:
  created:
    - voss_runtime/probable.py
    - voss_runtime/budget.py
    - voss_runtime/context.py
    - tests/test_probable.py
    - tests/test_budget.py
    - tests/test_context.py
  modified:
    - voss_runtime/__init__.py

key-decisions:
  - "ProbableValue is a frozen Generic dataclass; __matmul__ overload supplies the `value @ threshold` syntax PRD §3.2 prescribes"
  - "BudgetScope uses contextvars.ContextVar so nested scopes restore cleanly under asyncio without explicit threading locks"
  - "run_with_budget converts asyncio.TimeoutError → BudgetExceededError(reason='latency') so codegen can pattern-match a single exception type"
  - "ContextScope counts tokens per add() (D-07) and triggers compression immediately, oldest-slot-first, halving each slot until under budget (floor 64 tokens)"
  - "ContextScope.ask routes return_type: ProbableValue → wrap text with heuristic confidence; Pydantic BaseModel → forward as response_format and return parsed instance; otherwise return raw text"
  - "ContextScope reports usage to current_budget() if one is active — composition seam for `within { ctx { ... } }` codegen"

patterns-established:
  - "Async-first: every model-touching surface is `async`; no sync shims"
  - "Inject-don't-import for testability: ContextScope accepts provider+compressor; BudgetScope's latency check is a plain helper"
  - "Heuristic ProbableValue confidence at runtime — refined later by structured-output finish-reason inspection"

requirements-completed:
  - RUN-01
  - RUN-02
  - RUN-03

duration: ~5min
completed: 2026-05-07
---

# Phase 01 Plan 02: Core Scopes Summary

**ProbableValue, BudgetScope, ContextScope land — the runtime now enforces confidence, budget, and context-window semantics behind every model call.**

## Performance

- **Tasks:** 3
- **Files created:** 6
- **Files modified:** 1
- **Tests added:** 23 (11 probable + 6 budget + 6 context)
- **Suite total:** 42 passing under `pytest -q -m "not live"`

## Accomplishments
- `ProbableValue[T]` frozen generic with confidence validation, `gate`, `unwrap`, and `@`-threshold overload
- `BudgetScope` async ctx mgr enforcing tokens/cost/latency, with `current_budget()` ContextVar lookup and `run_with_budget()` latency helper
- `ContextScope` with per-`add()` token counting, oldest-first summarize compression, and `ask()` routing to text / `ProbableValue` / Pydantic-parsed result; reports usage to active `BudgetScope`

## Files Created/Modified
- `voss_runtime/probable.py` — `ProbableValue[T]` dataclass + matmul threshold check
- `voss_runtime/budget.py` — `BudgetScope`, `current_budget`, `run_with_budget`
- `voss_runtime/context.py` — `ContextScope`, `_summarize_compress`, `_Slot`
- `tests/test_probable.py` — 11 cases incl. frozen-instance assertions
- `tests/test_budget.py` — 6 cases incl. nested-scope restore + asyncio.wait_for latency
- `tests/test_context.py` — 6 cases via `StubProvider` incl. `BudgetScope` composition
- `voss_runtime/__init__.py` — re-exports `ProbableValue`, `BudgetScope`, `current_budget`, `run_with_budget`, `ContextScope`

## Verification
- `pytest tests/test_probable.py tests/test_budget.py tests/test_context.py -q` → 23 passed
- Full stub-mode suite: 42 passed
- `from voss_runtime import ProbableValue, BudgetScope, ContextScope, current_budget, run_with_budget` clean

## Next
Plan 01-03 builds `SemanticMatcher` and embedding plumbing on top of the now-stable scope primitives.
