---
phase: M12-mcp-bridge-caps-01c
plan: 04
subsystem: mcp
tags: [mcp, cli, click, serve, stdio, permission-mode]

requires:
  - phase: M12-01
    provides: "McpServer.serve_stdio(reader, writer)"
  - phase: M12-02
    provides: "build_tool_descriptors, build_tool_dispatch"
  - phase: M12-03
    provides: "make_skill_dispatch bridge"
provides:
  - "voss mcp serve --mode {plan|edit|auto} foreground click subcommand"
  - "wired pipeline: load_mcp_config -> build_tool_descriptors -> make_skill_dispatch -> build_tool_dispatch -> McpServer.serve_stdio over real stdio"
  - "_NullRenderer guaranteeing JSON-RPC stdout purity"
affects: [M12-05]

tech-stack:
  added: []
  patterns:
    - "asyncio.connect_read_pipe/connect_write_pipe wraps sys.stdin.buffer/sys.stdout.buffer as StreamReader/StreamWriter for the MCP wire"
    - "_NullRenderer (__getattr__ -> no-op lambda) replaces PlainRenderer in any context where stdout must stay pure"
    - "Lazy intra-command imports + click.exceptions.Exit (mirrors existing mcp_list_cmd/mcp_call_cmd)"

key-files:
  created:
    - tests/harness/mcp/test_mcp_serve_cli.py
  modified:
    - voss/harness/cli.py

key-decisions:
  - "_NullRenderer instead of literal PlainRenderer() — PlainRenderer.show_final/stream_delta/finalize_stream write to STDOUT (verified in voss/harness/render.py), which would corrupt the JSON-RPC frame stream (Threat T-M12-04-02). Plan explicitly authorized this fallback."
  - "asyncio.streams.FlowControlMixin path used (importable + stable on Python 3.13.5, the only runtime here); mcp SDK fallback not needed."
  - "Lazy imports inside mcp_serve_cmd + raise click.exceptions.Exit(N) — matches the surrounding mcp_list_cmd/mcp_call_cmd convention rather than the plan's literal sys.exit()."

patterns-established:
  - "MCP server CLI entry: no-default --mode (click.Choice required=True) is the D-03 forcing function; missing/invalid --mode exits 2"

requirements-completed: [MCP-01]

duration: 7 min
completed: 2026-05-18
---

# Phase M12 Plan 04: CLI Serve Command Summary

**`voss mcp serve --mode {plan|edit|auto}` — foreground stdio MCP server wiring M12-01/02/03 into the existing `voss mcp` click group; `--mode` required (no default), stdout kept pure for JSON-RPC.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-05-18
- **Completed:** 2026-05-18
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments
- `voss/harness/cli.py`: new `@mcp_group.command("serve")` sibling of `list`/`call`. `--mode` `click.Choice([plan,edit,auto])` `required=True` (no default — D-03 forcing function; missing/invalid exits 2). `--cwd` option. Body: `load_mcp_config` → `server_cfg` (None→default `McpServerExposureConfig()`) → `make_toolset` → `default_skill_registry()` → `build_tool_descriptors` → `PermissionGate(mode=…, auto_yes=True)` → `make_skill_dispatch` → `build_tool_dispatch` → `McpServer` → `asyncio.run(serve_stdio(reader, writer))` over `connect_read_pipe`/`connect_write_pipe`-wrapped stdin/stdout. `--help` documents D-05 cost-attribution.
- `_NullRenderer` added (module-level, `__getattr__`→no-op) — keeps stdout free of non-JSON-RPC bytes (T-M12-04-02).
- `tests/harness/mcp/test_mcp_serve_cli.py`: 6 CliRunner tests — mode-required, mode-rejects-invalid, help-cost-attribution, help-three-modes, serve-sibling-of-list/call, malformed-mcp.yml-nonzero. All green.
- Full `tests/harness/mcp/` suite green: 37 (31 prior + 6 new).

## Task Commits

1. **Task 1: mcp serve command** — `ddbdaf4` (feat) — committed cleanly as mine
2. **Task 2: CliRunner tests** — `fa2d36d` (test) — committed cleanly as mine

**Plan metadata:** this commit (docs).

## Files Created/Modified
- `voss/harness/cli.py` — `_NullRenderer` + `mcp_serve_cmd` (inserted after `mcp_call_cmd`, before `logs_group`)
- `tests/harness/mcp/test_mcp_serve_cli.py` — 6 surface tests

## Decisions Made
- **`_NullRenderer` over `PlainRenderer()`:** verified `voss/harness/render.py` — `PlainRenderer.show_final`/`stream_delta`/`finalize_stream` write to `sys.stdout`. The MCP server's stdout IS the JSON-RPC wire; any renderer byte there corrupts frames. Plan text explicitly authorized: "replace it with a renderer that writes to stderr OR construct a no-op". Chose a `__getattr__`→no-op class (zero stdout regardless of which renderer method any skill calls).
- **`asyncio.streams.FlowControlMixin` path:** verified importable + Python 3.13.5 (the only runtime). The plan's mcp-SDK fallback was unnecessary.
- **Lazy imports + `click.exceptions.Exit`:** mirrored the adjacent `mcp_list_cmd`/`mcp_call_cmd` style instead of the plan's literal top-level imports + `sys.exit()`. Surgical-change rule: match existing surrounding code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan-authorized fallback] `_NullRenderer` instead of `PlainRenderer()`**
- **Found during:** Task 1
- **Issue:** Plan's literal code used `renderer = PlainRenderer()` but its own threat T-M12-04-02 + inline note flagged PlainRenderer writes stdout. Confirmed in `render.py`.
- **Fix:** Added module-level `_NullRenderer` (`__getattr__`→no-op), used in `mcp_serve_cmd`.
- **Files modified:** voss/harness/cli.py
- **Verification:** grep shows no `PlainRenderer` inside `mcp_serve_cmd`; full mcp suite green.
- **Committed in:** ddbdaf4

**2. [Rule 1 - Surgical-change conformance] lazy imports + click.exceptions.Exit**
- **Found during:** Task 1
- **Issue:** Plan used top-level imports + `sys.exit(1)`; surrounding `mcp_list_cmd`/`mcp_call_cmd` use intra-function lazy imports + `raise click.exceptions.Exit(1)`.
- **Fix:** Matched the existing convention.
- **Files modified:** voss/harness/cli.py
- **Verification:** cli.py parses; non-zero exits confirmed (no-mode=2, bad-mode=2, malformed-yaml≠0).
- **Committed in:** ddbdaf4

---

**Total deviations:** 2 auto-fixed (both Rule 1 — plan-anticipated fallback + surgical-style conformance). No scope/behavior change vs the plan's must-have truths; the no-default-mode forcing function, the wired pipeline, and stdout purity all hold exactly as specified.

## Issues Encountered
- `voss/harness/cli.py` had pending external state (concurrent automation touched it earlier in the session) — re-Read via the Read tool before Edit (first Edit attempt blocked on stale read state; resolved by reading the target region, then editing). Both task commits this run landed cleanly as mine (no sweep).

## User Setup Required
None.

## Next Phase Readiness
- M12-04 surfaces the full server. M12-05 (e2e subprocess acceptance) can now spawn `voss mcp serve --mode plan` and assert the JSON-RPC roundtrip + plan-deny + telemetry.
- M12-05 verifies the stdout-purity constraint at the wire level (every line `json.loads`-able).
- No blockers.

## Self-Check: PASSED
- `cli.py` parses; `mcp_serve_cmd` registered as `list`/`call` sibling.
- `--mode` required (`click.Choice`); no-mode + bad-mode both exit 2; `--help` carries `REQUIRED` + `SERVER's configured LLM provider` + all three modes.
- All 4 key_links present in cli.py (`McpServer(`, `build_tool_descriptors(`, `make_skill_dispatch(`, `PermissionGate(mode=`).
- `_NullRenderer` used (no `PlainRenderer` in the serve command body) → JSON-RPC stdout purity.
- 6/6 `test_mcp_serve_cli.py` green; full `tests/harness/mcp/` green (37).
- `git diff --check` / `--cached --check` clean.

---
*Phase: M12-mcp-bridge-caps-01c*
*Completed: 2026-05-18*
