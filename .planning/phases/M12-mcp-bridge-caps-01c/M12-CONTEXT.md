# Phase M12: MCP Bridge (CAPS-01c) — Context

**Gathered:** 2026-05-18
**Status:** Ready for planning
**Source:** `/gsd-discuss-phase M12`. No SPEC.md exists; this CONTEXT + the ROADMAP M12 block + the T3 SUMMARY/SPEC ("M12 reduces to expose harness as MCP server only") are the planner's authority.

<domain>
## Phase Boundary

M12 ships the **server side** of the MCP bridge ONLY. The client side (consuming external MCP tools as harness tools) shipped in **T3-07** (`voss/harness/mcp/{config,client,registry}.py`), per T3-SPEC line 81 ("Expose harness AS MCP server (server side) — M12 keeps server-side; T3 is client-side only") and the ROADMAP M12 block.

What M12 delivers:
1. A `voss mcp serve` CLI subcommand that speaks MCP 2025-11-25 over **stdio only** and is launched as a subprocess by external hosts (Claude Desktop, Cursor, Continue, etc.).
2. Exposure of a **curated read-only subset of low-level harness tools** + the **7 T7 skills** as MCP tools advertised via `tools/list` and dispatched via `tools/call`.
3. Server-side reuse of the existing `PermissionGate` + mode-tier denial — every incoming tool call passes through `gate.check(...)` in the operator-chosen mode.
4. A `server:` top-level block in `.voss/mcp.yml` (symmetric with T3's `servers:` plural client block) declaring `exposed_tools`, `exposed_skills`, and optional `name`.
5. **Telemetry-only audit trail:** `mcp.server.request` / `mcp.server.response` events (mirroring T3 inbound `mcp.request` / `mcp.response`). No new M2 SessionRecord per invocation.

In scope: stdio transport, curated 6-tool + 7-skill surface, mode-gated dispatch, telemetry events, server `.voss/mcp.yml` schema, `voss mcp serve` foreground command.

Out of scope (deferred): HTTP transport (streamable-HTTP or SSE), daemon mode + PID-file lifecycle, mutating low-level tools (`fs_write`/`fs_edit`/`shell_run`), per-client allowlist auth, MCP UI catalog (M9 follow-up), cross-org service registry, full M2 SessionRecord-per-call accounting.
</domain>

## No SPEC — Requirements Posture

`MCP-01..0N` and success criteria are not locked (ROADMAP defers them to `M12-SPEC.md`). This CONTEXT + ROADMAP M12 block + the T3 reduction note are the planner's authority. Recommended `MCP-XX` mapping for the planner / a thin downstream SPEC:

- **MCP-01** — `voss mcp serve --mode plan|edit|auto` foreground stdio command exists. **No default mode** — invocation without `--mode` errors and exits non-zero.
- **MCP-02** — Server completes MCP 2025-11-25 handshake (`initialize` → `notifications/initialized`) over stdin/stdout JSON-RPC. Protocol version mismatch warns but continues (mirrors T3 client).
- **MCP-03** — `tools/list` advertises exactly the 6 curated low-level tools (`fs_read`, `fs_glob`, `fs_grep`, `voss_check`, `git_status`, `git_diff`) plus the 7 T7 skills (`analyze`, `rename-symbol`, `voss-lint-as-skill`, `summarize-diff`, `audit-cognition`, `add-test`, `port-py-to-voss`). 13 tools total.
- **MCP-04** — Each advertised tool's `destructiveHint` annotation mirrors its source `is_mutating` flag verbatim: 6 low-level tools all `false`; 7 skills follow `SkillEntry.mutating` (`analyze`/`rename-symbol`/`add-test`/`port-py-to-voss` = `true`; `voss-lint-as-skill`/`summarize-diff`/`audit-cognition` = `false`).
- **MCP-05** — `tools/call` dispatches through `PermissionGate.check(tool_name, args, is_mutating=...)`. In `plan` mode, every `is_mutating=True` tool is denied with the standard `denied by mode plan` reason; the MCP response carries an `<error: denied by mode plan>` envelope (T3-07 client-error precedent).
- **MCP-06** — `.voss/mcp.yml` schema gains a top-level `server:` block (symmetric with `servers:` plural). Fields: `exposed_tools: list[str] | "*"`, `exposed_skills: list[str] | "*"`, `name: str | null`. `*` resolves to the curated default set in MCP-03. Existing T3 `servers:` (plural) loader untouched.
- **MCP-07** — Every incoming `tools/call` emits `mcp.server.request` BEFORE dispatch and `mcp.server.response` AFTER (success or error). Event shape mirrors T3's `mcp.request` / `mcp.response` (redacted args, tool name, elapsed ms, allowed/denied). No M2 SessionRecord write per call.

A `/gsd:spec-phase M12` invocation may formalize these.

<canonical_refs>
## Canonical References (MANDATORY)

Downstream agents (researcher, planner) MUST read these before acting:

- `.planning/ROADMAP.md` (lines 564-586) — Phase M12 block (authoritative since no SPEC).
- `.planning/ROADMAP.md` (lines 876-928) — Phase T3 Network Surface block; lines 912-913 set the M12 scope reduction (server-side only).
- `.planning/phases/T3-network-surface/T3-SPEC.md` (lines 19, 81) — T3 explicitly carves the M12/T3 boundary.
- `.planning/phases/T3-network-surface/T3-07-SUMMARY.md` — full client-side surface as it shipped: `McpClient`, `register_mcp_tools`, handshake, telemetry, namespacing.
- `voss/harness/mcp/__init__.py` — public re-exports (`McpServerConfig`, `McpConfig`, `load_mcp_config`, `substitute_server`, `McpConfigError`, `McpClient`, `register_mcp_tools`). M12 extends this surface.
- `voss/harness/mcp/config.py` — Pydantic `McpServerConfig`/`McpConfig` schema; M12 adds the `server:` top-level block here (must keep `extra="forbid"`).
- `voss/harness/mcp/client.py` — stdio JSON-RPC framing + telemetry helpers + `_PROTOCOL_VERSION = "2025-11-25"`. The server's transport layer mirrors this in reverse.
- `voss/harness/mcp/registry.py` — `register_mcp_tools` adapter (`destructiveHint` → `is_mutating` mapping convention). Same convention runs in reverse for outbound advertisement.
- `voss/harness/tools.py` (lines 444-465) — full `make_toolset` table; lines 444-460 contain the 6 curated read-only tools.
- `voss/harness/permissions.py` (lines 49-65) — `mode_allows()` tier rules used by the server-side gate.
- `voss/harness/skill_registry.py` (after T7) — `default_skill_registry()` returns the 7 skills with their `mutating` flags; this drives MCP-04 advertisement.
- `voss/harness/cli.py` (lines 2292-2398) — existing `voss mcp list` + `voss mcp call` click group; M12 adds `voss mcp serve` to it.
- `voss/harness/telemetry.py` (and `voss/harness/mcp/client.py` `_emit_mcp_request`/`_emit_mcp_response`) — the event-emission helpers M12 mirrors as `mcp.server.request`/`mcp.server.response`.
- `voss/harness/lifecycle.py` — `register_subprocess` reaping pattern (server side uses analogous SIGTERM/SIGKILL grace if/when a daemon mode lands; foreground `voss mcp serve` cleans up on its own SIGTERM).
- Upstream MCP spec — protocol version `2025-11-25` (frozen in `client.py:_PROTOCOL_VERSION`). The official Anthropic Python `mcp` package is importable in this env (`import mcp` succeeds) and may be used for the server stdio framing if the planner deems it lower-risk than hand-rolling JSON-RPC parity with `client.py`.

</canonical_refs>

<code_context>
## Reusable Assets and Patterns

| Asset | Source | M12 Use |
|---|---|---|
| `McpConfig` pydantic schema with `extra="forbid"` | `voss/harness/mcp/config.py` | Extend with a `server:` field (default `None`). New optional class `McpServerExposureConfig` (don't confuse with `McpServerConfig` which is per-OUTBOUND-server). |
| `McpClient._stdio_send_recv` / line framing | `voss/harness/mcp/client.py` | Mirror in reverse for the server: read JSON-RPC lines from stdin, write to stdout. The `mcp` Python SDK provides server-side stdio framing — preferred unless RESEARCH finds a blocker. |
| `_PROTOCOL_VERSION = "2025-11-25"` constant | `voss/harness/mcp/client.py` | Share it; server reads the same constant for `initialize` response. |
| `telemetry.emit("mcp.request"/"mcp.response", ...)` | `voss/harness/mcp/client.py` `_emit_mcp_request`/`_emit_mcp_response` + redact helpers | M12 adds parallel `_emit_mcp_server_request`/`_emit_mcp_server_response` calling `telemetry.emit("mcp.server.request"/"mcp.server.response", ...)`. Same redaction policy. |
| `make_toolset(cwd, ...)` returning `dict[str, ToolEntry]` | `voss/harness/tools.py:77+` | Server calls `make_toolset` then filters by the curated 6-name list (`exposed_tools` from `server:` block, default-`*` resolved). |
| `default_skill_registry()` returning 7 `SkillEntry`s with `mutating` | `voss/harness/skill_registry.py` (post-T7) | Server iterates the registry and exposes each as a tool. `destructiveHint = entry.mutating`. |
| `PermissionGate(mode=..., auto_yes=True)` | `voss/harness/permissions.py` | Server constructs ONE `PermissionGate(mode=<operator --mode>, auto_yes=True)` for its lifetime. Every `tools/call` calls `gate.check(tool_name, args, is_mutating=<from ToolEntry/SkillEntry>)`. |
| `register_mcp_tools` `destructiveHint`→`is_mutating` mapping convention | `voss/harness/mcp/registry.py` | The INVERSE mapping is M12's `tools/list` advertisement rule: `is_mutating` → `destructiveHint`. Symmetric. |
| `click.group("mcp")` + `voss mcp list/call` | `voss/harness/cli.py:2292-2398` | Add `voss mcp serve` as a third sibling command in this group. |
| Top-level click error-envelope pattern `<error: ...>` | `voss/harness/cli.py:2310` + `voss/harness/mcp/client.py` MCP-error replies | Reuse for `tools/call` error responses (denied/jailed/timeout). |
| `lifecycle.register_subprocess` SIGTERM+5s+SIGKILL grace | `voss/harness/lifecycle.py` | NOT needed for foreground `voss mcp serve` (it's the process itself). Listed for reference if/when daemon mode lands later. |

**Conventions to honor:**
- Per-tool `name` advertised over MCP MUST be stable. Recommend: low-level tools use bare names (`fs_read` etc.); skills use their `SkillEntry.id` (`rename-symbol`, `voss-lint-as-skill`, …). No namespacing prefix is added for v0.1 — the SERVER advertises only its own surface, not other servers'. (T3 client-side namespaces inbound `{server}__{tool}` because it merges multiple inbound servers.)
- `extra="forbid"` on every pydantic model — unknown YAML keys must error, not silently drop.
- All MCP error responses are JSON-RPC errors, not exceptions across the wire. Internal Python exceptions caught and converted at the dispatch boundary.

</code_context>

<decisions>
## Implementation Decisions

### D-01 — Transport: stdio only
Ship MCP 2025-11-25 over stdio. Matches the T3 client transport and how external hosts (Claude Desktop, Cursor, Continue) launch MCP servers as subprocesses. HTTP (streamable-HTTP per current MCP spec; SSE is deprecated) is **explicitly deferred**, not partially built. ROADMAP wording "stdio + HTTP" is a v0.2-scope hint, not a v0.1 deliverable. Re-open only on a concrete dogfood signal (a host that requires network-MCP and cannot subprocess).

### D-02 — Tool surface: 6 low-level + 7 skills, destructiveHint = is_mutating
**Low-level (6):** exactly the ROADMAP example set — `fs_read`, `fs_glob`, `fs_grep`, `voss_check`, `git_status`, `git_diff`. All `is_mutating=False` and `is_network=False`. No `fs_write`, no `fs_edit`, no shell, no `web_fetch`, no `web_search` in the v0.1 default surface. Operators can opt in via `exposed_tools:` in `.voss/mcp.yml` to add tools from the live `make_toolset` table, but the default `*` resolves only to these 6.

**Skills (7):** all 7 T7 skills exposed — `analyze`, `rename-symbol`, `voss-lint-as-skill`, `summarize-diff`, `audit-cognition`, `add-test`, `port-py-to-voss`. Skill tool names = `SkillEntry.id` verbatim. Skill execution drives `run_turn` server-side; the LLM call is charged to the SERVER's provider config (Voss's own keys, NOT the calling host's). Document this cost-attribution clearly in `voss mcp serve --help`.

**destructiveHint mapping convention:** `destructiveHint = ToolEntry.is_mutating` for low-level; `destructiveHint = SkillEntry.mutating` for skills. Verbatim. Symmetric with T3 inbound rule. Result for the default surface: 4 destructive tools (`analyze`, `rename-symbol`, `add-test`, `port-py-to-voss`), 9 non-destructive.

### D-03 — Lifecycle + permission posture
**Invocation:** `voss mcp serve --mode plan|edit|auto` runs in foreground, blocks on stdin/stdout, exits on SIGTERM. **No daemon mode in v0.1**. The external MCP host (Claude Desktop, Cursor) owns subprocess lifecycle — Voss does not start, monitor, or restart itself.

**No default mode:** the operator MUST pass `--mode`. Running `voss mcp serve` with no `--mode` errors out (non-zero exit, `<error: --mode required (plan|edit|auto)>`). Rationale: an MCP server exposes a tool surface to whoever can spawn the subprocess; making the operator name the mode every launch is a one-line forcing function that prevents accidentally shipping `auto`-mode to a host config. Deviates from T3 NET-04's "default plan" — accepted: the T3 NET-04 default applied to OUTBOUND tools the harness consumes; M12 INBOUND is the dual case and warrants stricter opt-in.

**Server PermissionGate:** server constructs ONE `PermissionGate(mode=<--mode>, auto_yes=True)` for its lifetime. Every `tools/call` passes through `gate.check(name, args, is_mutating=<from registry>)`. Denied calls return JSON-RPC error with the gate's `reason` text (`denied by mode plan`, etc.).

**`.voss/mcp.yml` schema extension:** add a top-level optional `server:` block (singular). Schema:
```yaml
server:
  name: "voss"          # advertised in initialize response; optional, defaults to "voss"
  exposed_tools: "*"    # or explicit list[str]; "*" resolves to the 6-tool default set
  exposed_skills: "*"   # or explicit list[str]; "*" resolves to the 7-skill default set
```
`server:` is OPTIONAL. When absent, defaults are the curated full set. `extra="forbid"` on the pydantic model. T3 outbound `servers:` (plural) block untouched.

### D-04 — Audit trail: telemetry only
Every incoming `tools/call` emits two telemetry events:
- `mcp.server.request` BEFORE dispatch (name, redacted args, mode, client name from `initialize`, sequence id).
- `mcp.server.response` AFTER dispatch (sequence id, allowed/denied, elapsed_ms, result-shape summary, error envelope on failure).

Naming mirrors T3 outbound `mcp.request`/`mcp.response`. Redaction helpers reused.

**No M2 SessionRecord per call.** This diverges from ROADMAP "every MCP invocation logged through M2 RunRecorder" — explicitly accepted for v0.1: writing a SessionRecord+IterationRecord per request would clutter `/sessions` with one entry per remote-tool-poke, and the inspectable surfaces (`/probable`, `/btrace`) are designed around LLM-driven turns, not RPC pokes. Re-open on real audit demand (compliance need, post-incident forensics) by adding a `--record-sessions` flag that promotes telemetry to RunRecorder writes.

### D-05 — Skill execution: server-side LLM cost lands on the SERVER's provider config
When an external MCP client invokes a skill tool (e.g. `summarize-diff`), the skill runs `run_turn` inside `voss mcp serve`'s process, using `voss mcp serve`'s configured provider/keys/model. The calling host does NOT see the LLM cost. Document in `--help` and the published `tools/list` description. Operators who don't want this should set `exposed_skills: []` in `.voss/mcp.yml`.

</decisions>

<deferred>
## Deferred Ideas

These came up in discussion (or are present in ROADMAP wording) and are intentionally not in M12. Capture them so they're not lost.

- **HTTP transport** (streamable-HTTP per current MCP spec). Re-open when a host that requires it surfaces. ROADMAP wording "stdio + HTTP" notwithstanding.
- **Daemon mode + PID file lifecycle** (`voss mcp serve --daemon`, `voss mcp serve stop`). Defer until a workflow that can't use foreground-launch arrives.
- **Mutating low-level tools (`fs_write`, `fs_edit`)** in the default surface. Available via explicit `exposed_tools:` opt-in but not in `*`. Re-open if a host workflow proves the need.
- **Shell + network tools (`shell_run`, `web_fetch`, `web_search`)** in the default surface. Same opt-in availability via `exposed_tools:`; not advertised by `*`.
- **Per-client allowlist auth** (`clients:` allowlist under `server:`). v0.1 trusts whoever can spawn the subprocess (same trust posture as a local LSP); add only on a concrete threat model.
- **Full M2 SessionRecord per MCP invocation** (`--record-sessions` flag, ROADMAP literal). Defer until compliance / forensics demand exists.
- **MCP catalog UI in M9 TUI** for browsing remote tools. Listed out-of-scope in ROADMAP M12; revisit as an M9 follow-up.
- **Cross-org MCP service registry**. Out-of-scope in ROADMAP; ecosystem-level concern.
- **Encrypted MCP transports beyond protocol mandate**. Out-of-scope in ROADMAP.
- **Per-skill cost-attribution back to calling host** (would need MCP spec extension; unsolved upstream).

</deferred>

<open_questions>
## Open Questions for Research

None blocking. Recommended for `gsd-phase-researcher` to confirm during M12-RESEARCH:

1. **Use the Anthropic `mcp` Python SDK for server stdio framing, or hand-roll parity with `client.py`?** `import mcp` succeeds in this env. The SDK provides `mcp.server.Server` + `mcp.server.stdio.stdio_server` helpers. Hand-rolling keeps line-for-line symmetry with `client.py`'s framing; SDK reduces our maintenance load. Researcher to compare LOC, test surface, and protocol-drift risk.
2. **`initialize` clientInfo handling.** The MCP `initialize` request carries a `clientInfo: {name, version}` from the host. Should `mcp.server.request` events include it (default: yes, redact nothing — clientInfo is not secret)? Confirm against telemetry redaction policy.
3. **`tools/call` result shape for skills.** Skills currently write to stdout via the renderer; the MCP `CallToolResult` expects a structured `content: list[TextContent | ...]`. Capture skill stdout into one `TextContent` block? Researcher to confirm by inspecting an MCP host's expectations (Claude Desktop is the reference).
4. **Subprocess reap behavior of incoming-stdio.** When the parent MCP host (Claude Desktop) is killed ungracefully, our `voss mcp serve` may be orphaned. T3 uses `lifecycle.register_subprocess` for outbound clients; what's the symmetric handling for our own process when stdin EOFs? Likely: exit cleanly on stdin EOF.

</open_questions>

---
*Phase: M12-mcp-bridge-caps-01c*
*Context gathered: 2026-05-18*
*Next: `/gsd:plan-phase M12`*
