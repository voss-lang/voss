---
phase: M12-mcp-bridge-caps-01c
plan: 01
status: complete
date: 2026-05-19
wave: 1
---

# M12-01 Summary - MCP Server Scaffold

## Change Locations

### `voss/harness/mcp/config.py`

- Added `McpServerExposureConfig` with strict `extra="forbid"` behavior.
- Added optional `McpConfig.server: McpServerExposureConfig | None = None`.
- Left the existing outbound `servers: dict[str, McpServerConfig]` loader contract intact.

### `voss/harness/mcp/server.py`

- Added the stdio JSON-RPC `McpServer` scaffold.
- Reuses `client.py`'s `_PROTOCOL_VERSION` constant instead of redeclaring the protocol string.
- Handles:
  - stdin EOF clean exit
  - `initialize`
  - `notifications/initialized`
  - `tools/list`
  - `tools/call`
  - malformed JSON parse errors
  - unknown methods
  - unknown tool names
- Emits exactly one `mcp.server.request` before `tools/call` dispatch and one `mcp.server.response` after dispatch.
- Redacts tool args via `telemetry.redact_tool_args`.
- Keeps the scaffold decoupled from later-wave tool and permission surfaces.

### `voss/harness/mcp/__init__.py`

- Re-exported `McpServerExposureConfig`.
- Added lazy `McpServer` export without eagerly importing `voss.harness.mcp.server`.
- Preserved the existing lazy `McpClient` and `register_mcp_tools` exports.

### `tests/harness/mcp/test_mcp_server_scaffold.py`

- Added six in-memory async scaffold tests covering:
  - handshake roundtrip
  - `tools/list` descriptors
  - `tools/call` dispatch and telemetry
  - unknown tool JSON-RPC error
  - parse-error survival
  - clean EOF return

## Verification

All M12-01 plan-level checks passed:

- Schema/export smoke: passed.
- `server.py` AST parse: passed.
- `_PROTOCOL_VERSION` single-source import and `LINE_LIMIT_BYTES` checks: passed.
- Source guards for no protocol redeclaration and no later-wave coupling: passed.
- `tests/harness/mcp/test_mcp_server_scaffold.py`: 6 passed.
- Full `tests/harness/mcp/`: 19 passed.
- Over-1-MiB line-limit survival smoke: passed.
- `git diff --check`: passed.

## Notes

- `gsd-sdk query init.execute-phase M12-mcp-bridge-caps-01c` did not recognize this M12 phase directory in the local GSD index, so execution used the supplied plan file as the contract directly.
- The pre-existing dirty file `apps/voss-app/src-tauri/tauri.conf.json` was left untouched.

M12-01 is complete and unblocks M12-02/M12-03.
