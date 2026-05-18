---
phase: M12
slug: mcp-bridge-caps-01c
type: plan-outline
created: 2026-05-18
---

# Phase M12 — MCP Bridge (Server side) — Plan Outline

M12 ships the server side of the MCP bridge (client side landed in T3-07).
Five plans across four waves. Waves 2's M12-02 and M12-03 are file-disjoint and
run in parallel; everything else is serial because it touches the same
`voss/harness/mcp/server.py` surface.

| Plan ID | Objective | Wave | Depends On | Requirements |
|---|---|---:|---|---|
| M12-01 | Server scaffold: stdio JSON-RPC framing, `initialize`/`notifications/initialized`/`tools/list` handshake, `mcp.server.*` telemetry, `McpServerExposureConfig` schema in `config.py`, test scaffold. | 1 | - | MCP-01, MCP-02, MCP-06, MCP-07 |
| M12-02 | Tool advertisement + `tools/call` dispatch through `PermissionGate.check`. Builds the 13-tool surface from `make_toolset` (6 curated) + `default_skill_registry()` (7 skills) with `destructiveHint = is_mutating`. Error envelopes for denied/jailed/timeout. | 2 | M12-01 | MCP-03, MCP-04, MCP-05 |
| M12-03 | Skills bridge: adapter that runs `SkillEntry.handler(ctx, args)` server-side, builds a stub `ctx` with the server's `PermissionGate`/`provider`/`renderer`/`tools`, captures skill stdout into one `CallToolResult` `TextContent` block. Documents the cost-attribution implication of D-05. | 2 | M12-01 | MCP-03 |
| M12-04 | `voss mcp serve --mode plan\|edit\|auto` foreground click subcommand. `--mode` REQUIRED (no default). Wires `McpServer` + loaded `server:` block + curated default set. Adds `voss mcp` subcommand sibling to existing `list`/`call`. | 3 | M12-01, M12-02, M12-03 | MCP-01 |
| M12-05 | End-to-end acceptance: spawn `voss mcp serve --mode plan` as subprocess, complete real stdio handshake, list 13 tools, call one read-only tool successfully, attempt one mutating skill and assert denied-by-mode-plan envelope, switch `--mode edit` and assert allowed. Telemetry-event capture asserts `mcp.server.request`/`response` shape (Nyquist Dim-8 acceptance). | 4 | M12-02, M12-03, M12-04 | MCP-01..07 |

## Dependency Notes

- M12-01 owns the transport + handshake; every later plan calls into it.
- M12-02 and M12-03 split horizontally: M12-02 owns tool advertisement +
  dispatch + `make_toolset` filtering; M12-03 owns the SkillEntry adapter.
  They share no files and run in parallel (Wave 2).
- M12-04 is wave 3 because it needs both M12-02 (tool surface) and M12-03
  (skills bridge) to exist before exposing them via the CLI.
- M12-05 is wave 4 because it spawns the actual CLI as a subprocess and
  asserts the full stdio roundtrip — the phase acceptance gate.

## Out-of-Scope Reminders (from CONTEXT)

- HTTP transport (streamable-HTTP / SSE). stdio only.
- Daemon mode + PID-file lifecycle. Foreground only.
- Mutating low-level tools (`fs_write`, `fs_edit`) in the default surface.
- Shell + network tools (`shell_run`, `web_fetch`, `web_search`) in the
  default surface (available via explicit `exposed_tools:` opt-in only).
- Per-client allowlist auth (`clients:` block).
- Full M2 SessionRecord per MCP invocation (`--record-sessions`).
- Per-skill cost-attribution back to calling host (unsolved upstream).

These exist as Deferred items in `M12-CONTEXT.md` and MUST NOT be expanded by
any plan.
