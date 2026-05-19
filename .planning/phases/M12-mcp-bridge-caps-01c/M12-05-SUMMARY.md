---
phase: M12-mcp-bridge-caps-01c
plan: 05
subsystem: mcp
tags: [mcp, e2e, subprocess, stdio, acceptance, nyquist-dim8]

requires:
  - phase: M12-01
    provides: "McpServer stdio handshake + unknown-name JSON-RPC -32601 guard"
  - phase: M12-02
    provides: "13-tool advertisement + gate dispatch"
  - phase: M12-03
    provides: "skill bridge"
  - phase: M12-04
    provides: "voss mcp serve CLI entry"
provides:
  - "tests/harness/mcp/test_mcp_serve_e2e.py — true subprocess JSON-RPC roundtrip"
  - "wire-level proof of MCP-01..07"
affects: []

tech-stack:
  added: []
  patterns:
    - "subprocess.Popen(voss.cli mcp serve) + line-framed JSON-RPC over PIPE; per-id response matching; notification = write-no-wait"
    - "telemetry capture across processes via VOSS_LOG=1 + VOSS_LOG_PATH=<tmpfile>, parse 'kind' field"

key-files:
  created:
    - tests/harness/mcp/test_mcp_serve_e2e.py
  modified: []

key-decisions:
  - "Unknown-tool test asserts the M12-01 JSON-RPC error contract (-32601 'tool not found: <name>'), NOT M12-02's 'unknown tool:' isError envelope — the server's _tool_names guard fires before dispatch, making the dispatcher path unreachable through the server. Server behaviour is correct (matches M12-01 must-have); the plan's case-5 expectation was wrong."
  - "Telemetry test uses the real VOSS_LOG_PATH file sink (mechanism confirmed in telemetry.py) — NOT skipped. Event name lives in the 'kind' field; path sink writes plain JSON lines (no _LINE_PREFIX, that is stderr-sink only)."

patterns-established:
  - "MCP server e2e: spawn real CLI subprocess, assert handshake + advertisement count + gate-deny + read-only-allow + EOF + telemetry at the wire"

requirements-completed: [MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, MCP-06, MCP-07]

duration: 9 min
completed: 2026-05-18
---

# Phase M12 Plan 05: Acceptance E2E Summary

**True subprocess stdio roundtrip: spawns `voss mcp serve`, completes the 2025-11-25 handshake, asserts 13-tool advertisement, plan-mode mutating deny, plan-mode read-only allow, edit-mode read-only skill, JSON-RPC error for unknown tool, clean EOF exit, and `mcp.server.*` telemetry. Closes MCP-01..07.**

## Performance

- **Duration:** ~9 min
- **Tasks:** 1
- **Files modified:** 1 (1 created)
- **Completed:** 2026-05-18

## Accomplishments
- `tests/harness/mcp/test_mcp_serve_e2e.py` — 7 subprocess-level tests, all green:
  1. handshake + protocolVersion `2025-11-25` + `serverInfo.name == "voss"` + exactly 13 advertised tools (all expected names; every `annotations.destructiveHint` a bool)
  2. plan-mode `analyze` → `isError=True` + `denied by mode plan` (block-on-high T-M12-02-01 proven on the wire)
  3. plan-mode `fs_read` → success + file contents (read-only invariant)
  4. edit-mode `voss-lint-as-skill` → `isError=False` + schema v1 (skill bridge under non-plan mode)
  5. unknown tool → JSON-RPC `error -32601 tool not found: nope` (M12-01 contract)
  6. stdin EOF → subprocess exits returncode 0 (T-M12-01-05)
  7. `VOSS_LOG_PATH` capture → both `mcp.server.request` and `mcp.server.response` events emitted (D-04)
- Full `tests/harness/mcp/` green (44); `tests/harness/ -k mcp` green (56). `git diff --check` clean.

## Task Commits

1. **Task 1: e2e subprocess acceptance** — `f94a781` (test) — committed cleanly as mine.

**Plan metadata:** this commit (docs).

## Files Created/Modified
- `tests/harness/mcp/test_mcp_serve_e2e.py` — 7 e2e tests + spawn/send/handshake/close helpers

## Decisions Made
- **Unknown-tool assertion follows the M12-01 server contract, not the plan's case-5 text.** M12-01's `serve` loop rejects any name not in the advertised set with a JSON-RPC `error {code:-32601, message:"tool not found: <name>"}` BEFORE reaching the M12-02 dispatcher, so the dispatcher's `unknown tool:` `isError` envelope is unreachable through the server. The server behaviour is the correct, more spec-compliant one (it is M12-01's own stated must-have). Test asserts `resp["error"]["code"] == -32601` + `"tool not found: nope"`.
- **Telemetry test not skipped.** `voss/harness/telemetry.py` confirms `VOSS_LOG=1` + `VOSS_LOG_PATH=<file>` appends one JSON object per line; event name is the `kind` field; the path sink writes plain JSON (the `_LINE_PREFIX` is stderr-sink only). Test spawns with that env and parses `kind`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan assumption contradicted by upstream contract] unknown-tool envelope shape**
- **Found during:** Task 1 (test run — `KeyError: 'result'`)
- **Issue:** Plan case 5 asserted `resp["result"]["isError"] is True` + `unknown tool: nope`. The shipped M12-01 server returns a JSON-RPC `error -32601 tool not found: nope` (its own must-have) and never reaches the M12-02 dispatcher envelope for unadvertised names.
- **Fix:** Renamed test `test_unknown_tool_returns_jsonrpc_error`; asserts `"result" not in resp`, `error.code == -32601`, `"tool not found: nope"` in `error.message`. Code unchanged — the server is correct.
- **Files modified:** tests/harness/mcp/test_mcp_serve_e2e.py
- **Verification:** 7/7 e2e green; full mcp suite green.
- **Committed in:** f94a781

---

**Total deviations:** 1 auto-fixed (Rule 1 — plan text contradicted M12-01's own shipped contract; resolved by asserting the correct upstream behaviour, no code change). All other MCP-01..07 wire assertions land exactly as planned.

## Issues Encountered
- Telemetry line schema: assumed `event` key, actual is `kind` (verified in `telemetry.py:205`). Fixed before commit. Both M12-05 task commits this run landed cleanly as mine (no concurrent sweep).

## User Setup Required
None.

## Next Phase Readiness
- **M12 implementation complete: all 5 plans executed (M12-01..05), every plan has a SUMMARY.**
- MCP-01..07 each have ≥1 wire-level assertion in the e2e suite.
- Remaining to CLOSE the phase: `VERIFICATION.md` (goal-backward verify) — phase is `Executed`, not yet `Complete`.
- No blockers.

## Self-Check: PASSED
- `tests/harness/mcp/test_mcp_serve_e2e.py`: 7/7 green.
- Full `tests/harness/mcp/` green (44); `tests/harness/ -k mcp` green (56).
- Handshake test asserts exactly 13 tools + all expected names + bool destructiveHint.
- Plan-mode deny (`analyze` → `denied by mode plan`) + plan-mode allow (`fs_read`) both proven on the wire.
- Telemetry `mcp.server.request`/`response` captured via real `VOSS_LOG_PATH` sink.
- EOF → returncode 0.
- `git diff --check` clean.

---
*Phase: M12-mcp-bridge-caps-01c*
*Completed: 2026-05-18*
