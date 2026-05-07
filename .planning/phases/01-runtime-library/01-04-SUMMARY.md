---
phase: 01-runtime-library
plan: 04
subsystem: runtime
tags: [python, asyncio, agents, tools, pydantic, structured-output]

requires:
  - phase: 01-runtime-library/01-03
    provides: Provider abstraction, config, exceptions, semantic/memory runtime exports
provides:
  - VossAgent base class with active ModelProvider integration and structured Pydantic response_format
  - AgentHandle wrapper around asyncio.Task with result/cancel helpers
  - gather(handles, timeout=...) preserving order and returning None for failed/timed-out slots
  - tool decorator and ToolDescriptor with OpenAI/Anthropic-compatible function schemas
affects: [codegen, examples, agent-runtime, tool-calling]

tech-stack:
  added: []
  patterns:
    - "Agent subclasses configure system_prompt/tools/model/retries/return_type and override async run when needed"
    - "Structured agent outputs use Pydantic BaseModel via provider response_format"
    - "Tool schemas are generated from inspect.signature, typing.get_type_hints, and first-line docstrings"

key-files:
  created:
    - voss_runtime/agent.py
    - voss_runtime/tools.py
    - tests/test_agent.py
    - tests/test_tools.py
  modified:
    - voss_runtime/__init__.py
    - voss_runtime/semantic.py

key-decisions:
  - "Agent retry budget means initial attempt plus retries; retries=2 makes three provider attempts before surfacing ProviderError/ParseError"
  - "gather() uses asyncio.wait so timeout cancellation preserves one result slot per input handle"
  - "SemanticMatcher now lazy-loads numpy to keep package import/coverage collection lightweight while preserving behavior"

patterns-established:
  - "Tests register StubProvider instances under unique model names and assert provider call history"
  - "Tool-decorated callables are ToolDescriptor objects that remain directly callable and expose invoke()/schema()"

requirements-completed:
  - RUN-05
  - RUN-09

duration: 23min
completed: 2026-05-07
---

# Phase 01 Plan 04: Agent Runtime + Tool Schema Summary

**Async Voss agents with ordered spawn/gather orchestration plus generated tool-calling schemas for provider-backed model calls.**

## Performance

- **Duration:** 23 min
- **Started:** 2026-05-07T19:22:00Z
- **Completed:** 2026-05-07T19:45:00Z
- **Tasks:** 2 completed
- **Files modified:** 6

## Accomplishments

- Added `VossAgent`, `AgentHandle`, and `gather()` runtime primitives over asyncio tasks.
- Added provider-backed `_ask()` with system prompt construction, tool schema forwarding, Pydantic `response_format`, and retry exhaustion behavior.
- Added `@tool` / `ToolDescriptor` schema generation from function signatures, type hints, defaults, Pydantic models, and docstrings.
- Re-exported `VossAgent`, `AgentHandle`, `gather`, `tool`, and `ToolDescriptor` from `voss_runtime`.
- Verified focused tests, full non-live runtime suite, import smoke test, and coverage gate for `agent.py`/`tools.py`.

## Task Commits

1. **Task 1: Implement @tool decorator and schema generation** - `709b639` (feat; code/tests already present in HEAD at run start)
2. **Task 2: Implement VossAgent + AgentHandle + gather** - `709b639` (feat; code/tests already present in HEAD at run start)
3. **Verification fix:** `61fc680` (fix) defer `SemanticMatcher` numpy import so coverage/import verification can run cleanly

**Plan metadata:** docs commit containing this summary.

## Files Created/Modified

- `voss_runtime/tools.py` - `@tool` decorator, JSON-schema type conversion, `ToolDescriptor.schema()`, `invoke()`, and callable passthrough.
- `tests/test_tools.py` - Primitive/default/optional/Pydantic/list-dict schema coverage plus invocation behavior.
- `voss_runtime/agent.py` - `VossAgent`, `AgentHandle`, and `gather()` implementation.
- `tests/test_agent.py` - StubProvider-driven tests for run/spawn/gather/timeout/structured output/retries/tools.
- `voss_runtime/__init__.py` - Public runtime exports for agent/tool APIs.
- `voss_runtime/semantic.py` - Lazy numpy import deviation fix for lightweight package import under coverage.

## Decisions Made

- Retry semantics follow the plan: `retries=N` means N retries after the first attempt.
- `gather()` returns `None` for exceptions and cancellations rather than raising, matching PRD §3.6.
- Tool schemas use OpenAI function tool shape: top-level `type: function` with nested `function.name/description/parameters`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Lazy-load SemanticMatcher numpy import**
- **Found during:** Plan verification coverage gate
- **Issue:** Coverage collection imported `voss_runtime`, which eagerly imported `SemanticMatcher` and `numpy`; local Python/coverage/numpy architecture state failed with `ImportError: cannot load module more than once per process`.
- **Fix:** Moved numpy import in `voss_runtime/semantic.py` behind a small `_numpy()` helper used only when semantic matching needs arrays.
- **Files modified:** `voss_runtime/semantic.py`
- **Verification:** Focused semantic/agent/tool tests pass; coverage command now reports 94% total for `agent.py` + `tools.py`.
- **Committed in:** `61fc680`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** No API change; improves import ergonomics and preserves existing SemanticMatcher behavior.

## Issues Encountered

- The default `python3` invocation on this machine is architecture-mismatched for Pydantic/numpy extensions. Verification used `arch -arm64 python3`, consistent with prior runtime summaries.
- The code/test artifacts for this plan were already present in HEAD when execution began; this run verified them, fixed the coverage/import blocker, and created the required summary.

## Verification

- `arch -arm64 python3 -m pytest tests/test_tools.py -q` → 5 passed
- `arch -arm64 python3 -m pytest tests/test_agent.py -q` → 7 passed
- `arch -arm64 python3 -m pytest tests/test_tools.py tests/test_agent.py -q` → 12 passed
- `arch -arm64 python3 - <<'PY' ... from voss_runtime import VossAgent, AgentHandle, gather, tool, ToolDescriptor ... PY` → `imports-ok`
- `arch -arm64 python3 -m pytest tests/test_tools.py tests/test_agent.py --cov=voss_runtime.agent --cov=voss_runtime.tools --cov-report=term-missing -q` → 94% total coverage (`agent.py` 91%, `tools.py` 98%)
- `arch -arm64 python3 -m pytest -q -m 'not live'` → full non-live suite passed

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 01-05 can build runtime examples and integration flows on top of the completed provider, scope, memory, agent, and tool primitives. No blockers.

---
*Phase: 01-runtime-library*
*Completed: 2026-05-07*
