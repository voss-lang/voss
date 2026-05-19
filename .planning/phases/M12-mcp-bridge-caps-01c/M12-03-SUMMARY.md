---
phase: M12-mcp-bridge-caps-01c
plan: 03
subsystem: mcp
tags: [mcp, skills-bridge, asyncio-to-thread, stdout-capture, server-side]

requires:
  - phase: M12-01
    provides: "mcp server scaffold + McpServerExposureConfig (dep satisfied: server.py + config present)"
  - phase: T7
    provides: "default_skill_registry() with 7 SkillEntry handlers the bridge dispatches"
provides:
  - "voss/harness/mcp/server_skills.py — make_skill_dispatch factory (SkillEntry.handler → async (name,args)→stdout-text)"
  - "thread-isolated, per-call-stdout-captured skill execution for the MCP server"
affects: [M12-02, M12-04, M12-05]

tech-stack:
  added: []
  patterns:
    - "asyncio.to_thread wraps the sync SkillHandler so blocking run_turn inside an agentic skill cannot deadlock the server event loop"
    - "Per-call io.StringIO + contextlib.redirect_stdout — no module-level state, no cross-call leak"
    - "Registry-injected, skill-module-decoupled: zero imports of voss.harness.skills.*"

key-files:
  created:
    - voss/harness/mcp/server_skills.py
    - tests/harness/mcp/test_mcp_server_skills.py
  modified: []

key-decisions:
  - "Test convention: explicit @pytest.mark.asyncio on every async test (matches sibling tests/harness/mcp/* despite asyncio_mode=auto)"
  - "Thread-isolation proof uses a concurrent _tick() coroutine asserting 5 loop ticks advance during the handler's 50ms blocking sleep — stronger than a bare gather completion check"

patterns-established:
  - "MCP server consumes SkillEntry.handler through a SimpleNamespace ctx (cwd/provider/history/record/renderer/tools/gate/skill_registry) — same shape every T7 inner handler unpacks"

requirements-completed: [MCP-03]

duration: 6 min
completed: 2026-05-18
---

# Phase M12 Plan 03: Skills Bridge Summary

**`make_skill_dispatch` adapter — runs any T7 `SkillEntry.handler` off the MCP server's event loop with per-call stdout capture; proven end-to-end on `voss-lint-as-skill`.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-18
- **Completed:** 2026-05-18
- **Tasks:** 2
- **Files modified:** 2 (2 created)

## Accomplishments
- `voss/harness/mcp/server_skills.py`: `make_skill_dispatch(*, cwd, provider, history, record, renderer, tools, gate, skill_registry)` → async `(name, args) -> str`. Unknown id → `KeyError`. Handler runs in `asyncio.to_thread` (deadlock mitigation T-M12-03-02) inside a fresh `io.StringIO` + `contextlib.redirect_stdout` (isolation T-M12-03-01). Zero `voss.harness.skills.*` imports (decoupling T-M12-03-03).
- `tests/harness/mcp/test_mcp_server_skills.py`: 4 tests — real `voss-lint-as-skill` roundtrip asserting schema v1 + ANLY001; unknown-skill `KeyError`; thread-non-blocking proof (5 loop ticks during a 50ms handler sleep); per-call stdout isolation (`alpha`/`beta`).
- Full `tests/harness/mcp/` suite green: 31 (27 baseline + 4 new). M12-02 sibling `server_tools.py` byte-untouched (Wave-2 file-disjointness held).

## Task Commits

1. **Task 1: server_skills.py bridge** — `e5ee9e9` (feat) — committed cleanly as mine
2. **Task 2: test_mcp_server_skills.py** — `68343f4` (test) — committed cleanly as mine

**Plan metadata:** this commit (docs).

## Files Created/Modified
- `voss/harness/mcp/server_skills.py` — skill-execution bridge factory
- `tests/harness/mcp/test_mcp_server_skills.py` — 4 bridge tests

## Decisions Made
- Explicit `@pytest.mark.asyncio` on each async test — matches sibling `tests/harness/mcp/test_mcp_client.py` / `test_mcp_server_scaffold.py` even though `pyproject.toml` sets `asyncio_mode = "auto"`. Consistency over minimalism.
- Thread-isolation test uses a concurrent `_tick()` coroutine counting `asyncio.sleep(0.001)` iterations during the handler's blocking `time.sleep(0.05)`; asserts exactly 5 ticks. This proves the loop was NOT blocked — stronger than the plan's bare "both completed via gather" suggestion.

## Deviations from Plan

None — plan executed exactly as written. (The thread-isolation test assertion is strictly stronger than the plan's stated minimum, not a deviation from intent: the plan's truth "does not deadlock the server's event loop" is what is being proven more rigorously.)

## Issues Encountered
- M12-01 and M12-02 were executed by the concurrent same-user automation session (server.py + `McpServerExposureConfig` + `server_tools.py` all present at start). M12-03's `depends_on: [M12-01]` was therefore satisfied; no blocker. This run's two commits (`e5ee9e9`, `68343f4`) landed cleanly as mine — no sweep this time (contrast prior T7/M12-plan runs).

## User Setup Required
None.

## Next Phase Readiness
- M12-03 bridge is ready for M12-04 to inject as `build_tool_dispatch`'s `skill_dispatch` argument.
- Wave-2 sibling M12-02 (`server_tools.py`) present and untouched — the two Wave-2 plans are integrated only at M12-04 (CLI wiring).
- No blockers.

## Self-Check: PASSED
- `server_skills.py` parses; `make_skill_dispatch` 8 kw-only args; `asyncio.to_thread` + `redirect_stdout` present; no `from voss.harness.skills.` import.
- 4/4 tests in `test_mcp_server_skills.py` green; full `tests/harness/mcp/` suite green (31).
- `server_tools.py` (M12-02) byte-untouched — file-disjointness held.
- `git diff --check` / `--cached --check` clean.

---
*Phase: M12-mcp-bridge-caps-01c*
*Completed: 2026-05-18*
