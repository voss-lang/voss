---
phase: M12-mcp-bridge-caps-01c
plan: 02
status: complete
date: 2026-05-19
wave: 2
---

# M12-02 Summary - MCP Tool Advertisement + Dispatch

## Change Locations

### `voss/harness/mcp/server_tools.py`

- Added `DEFAULT_LOW_LEVEL_TOOLS` with the exact M12 curated low-level surface:
  `fs_read`, `fs_glob`, `fs_grep`, `voss_check`, `git_status`, `git_diff`.
- Added `resolve_tool_names()` and `resolve_skill_ids()`:
  - default `*` tool exposure resolves to the curated low-level set, filtered to available tools.
  - default `*` skill exposure resolves to `SkillRegistry.ids()`.
  - explicit unknown tool or skill names raise `McpConfigError`.
- Added `build_tool_descriptors()`:
  - emits MCP descriptors with `name`, `description`, `inputSchema`, and `annotations.destructiveHint`.
  - maps low-level `destructiveHint` from `ToolEntry.is_mutating`.
  - maps skill `destructiveHint` from `SkillEntry.mutating`.
  - keeps tools first, then skills.
- Added `build_tool_dispatch()`:
  - resolves low-level tools and skills by advertised name.
  - calls `gate.check(name, args, is_mutating=..., is_network=...)` before any invocation.
  - returns gate denial, unknown name, unwired skill bridge, and exception failures as MCP-style `isError=True` text envelopes.
  - invokes low-level tools directly and routes skills through the injected `skill_dispatch` callable for M12-03.

### `tests/harness/mcp/test_mcp_server_tools.py`

- Added eight tests covering:
  - default 13-descriptor surface.
  - destructive hint parity with source mutation flags.
  - unknown explicit tool and skill config errors.
  - plan-mode denial for all four mutating skills.
  - read-only tool dispatch.
  - unwired skill bridge error.
  - tool exception envelope behavior.
  - unknown call envelope behavior.

## Verification

All M12-02 checks passed:

- `python3 -m pytest -q tests/harness/mcp/test_mcp_server_tools.py`: 8 passed.
- `python3 -m pytest -q tests/harness/mcp/`: 27 passed.
- `server_tools.py` AST parse: passed.
- `DEFAULT_LOW_LEVEL_TOOLS` exact tuple check: passed.
- `build_tool_dispatch` signature check: passed.
- `gate.check(name, ...)` source guard: passed.
- top-level import discipline check: passed; no runtime import of `tools.py` or `skill_registry.py`.
- M12-03 sibling file check: `server_skills.py` does not exist yet.
- M12-01 file-disjointness check: no current diff in `server.py`, `__init__.py`, or `config.py`.
- `git diff --check`: passed.

M12-02 is complete and ready for M12-03/M12-04 integration.
