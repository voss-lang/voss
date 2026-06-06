# Phase V1: Capability Surface Hardening - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning
**Source:** /gsd-discuss-phase (default mode; options presented in plain language per Ben's standing V-track preference)

<domain>
## Phase Boundary

Turn the agent toolbelt into one normalized, typed, permissioned, auditable **capability
registry** by EXTENDING the existing `ToolEntry` (`voss/harness/tools.py`) — not replacing it.
Deliver `voss capabilities list` + `voss capabilities inspect <name>`, capability groups,
MCP unification into the same registry, recorder events on invocation, and gate-on-mutation.

Requirements VCAP-01..10 (PRD CAP-01..10) are LOCKED by the roadmap/PRD — this discussion
decides HOW, not WHAT. Hardens the M10–M15 tool surfaces.
</domain>

<decisions>
## Implementation Decisions

### D-01 — Capability metadata source: tag every tool by hand
- Add the new metadata fields directly to each `ToolEntry(...)` registration in
  `voss/harness/tools.py` (~30 entries in `make_toolset` + the code-tool and MCP merges).
- Explicit per-entry literals — NO name-prefix auto-derivation, NO convention magic.
  Rationale: precision over typing-savings; a mis-grouped mutating tool is a security bug.
- New fields extend the existing frozen dataclass (which today carries only
  `descriptor`, `is_mutating`, `is_network`). Keep `is_mutating`/`is_network` as-is; the new
  metadata layers on top (impl note: "add metadata fields incrementally").

### D-02 — MCP / external tools: default-deny posture (CAP-07, CAP-09)
- Every MCP-provided capability defaults to `is_mutating = true` and **requires gate approval**
  unless the MCP server explicitly declares the tool read-only.
- A few genuinely read-only MCP tools will prompt unnecessarily — accepted tradeoff vs. a
  mislabeled/hostile server silently running a mutating tool. Safe-by-default.
- This closes today's gaps where MCP paths bypass the normal gate (`cli.py` mcp-call bypasses
  PermissionGate; `net.py` MCP namespaced names bypass the net bucket). V1 routes MCP capability
  invocations through the same registry + gate as native tools. (Direct developer `voss mcp call`
  may remain a documented bypass; agent-facing invocation must not.)

### D-03 — Scope requirements: coarse group-level buckets (CAP-02 "scope requirements")
- A capability's `scope_requirements` names the permission BUCKET/group it needs
  (`fs`, `net`, `shell`, `git`, `code`, `memory`, `review`, `mcp`, `test`) — NOT specific
  paths or hosts in V1.
- Matches today's PermissionGate (mode-tier + `allow_net`); enough for role-based tool
  filtering on groups (acceptance criterion: "Role tool filters can operate on capability groups").
- Fine-grained per-path / per-host resource scopes are DEFERRED (see Deferred — that is V3 role-cage
  / V4 session-tree scope-containment territory, not V1).

### D-04 — `voss capabilities list` output: compact, grouped by group
- `list` prints each capability group as a header with its capability NAMES underneath. Compact,
  fast to scan, low noise. No badges/columns in `list`.
- `voss capabilities inspect <name>` carries the FULL detail (description, input/output schema,
  mutability, network, scope group, audit behavior, stateful flag).
- Both commands are JSON-first (impl note + a `--json` path); the grouped view is the human render.

### D-05 — Capability groups (CAP-06): exact set
- `fs`, `git`, `test`, `shell`, `net`, `code`, `memory`, `review`, `mcp` — exactly these nine.

### Claude's Discretion (not worth Ben's time, lock during planning)
- **Audit-behavior field values (CAP-02):** enumerate as `full | redact_args | metadata_only`,
  default `full` reusing the existing recorder arg-redaction (`telemetry.redact_tool_args`).
- **Stateful flag (CAP-03 "order-agnostic unless stateful"):** add `is_stateful: bool = False`;
  capabilities are order-agnostic by default, only the few stateful ones flag true.
- **Recorder event shape (CAP-08):** reuse `RunRecorder` / `telemetry.emit`; emit one
  capability-invocation event per call carrying capability name + group + mutating/net flags +
  redacted args, consistent with existing `mcp.request`/`mcp.response` telemetry rows.
- **Input/output schema source (CAP-01/02):** input schema = existing `descriptor.parameters`;
  output schema authored per capability (JSON-first), stubbed where a tool has no stable shape yet.
- Exact field names on the extended `ToolEntry`, dataclass vs. attached metadata object, and the
  `voss capabilities` CLI wiring location.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The thing being extended
- `voss/harness/tools.py` — `ToolEntry` (frozen dataclass, line ~56), `make_toolset` registry
  (line ~110/635), `_merge_mcp_tools` / `register_mcp_tools` (line ~743). PRIMARY edit target.
- `voss/harness/permissions.py` — `PermissionGate` (line ~192), `mode_allows`,
  `match_permission_rules`, `allow_net`. Gate that mutating/net capabilities clear.
- `voss/harness/recorder.py` — `RunRecorder` (capability-invocation events, CAP-08).
- `voss/harness/telemetry.py` — existing `mcp.request`/`mcp.response` event rows + `redact_tool_args`; pattern for the new capability event + audit-behavior.
- `voss/harness/mcp/` — MCP client/config/`register_mcp_tools` (unification target, CAP-07).
- `voss/harness/sandbox.py`, `voss/harness/code/` — listed existing assets.

### Spec/PRD
- `.planning/docs/ORCHESTRATION_LAYERS.md` §"Phase 1: Capability Surface Hardening" — the
  CAP-01..10 requirement table + acceptance criteria (canonical PRD, promoted in V0).
- `.planning/ROADMAP.md` §"Phase V1" — VCAP-01..10 mapping + cross-cutting constraints.

### Tests (existing patterns to extend for CAP-10 stub-testability)
- `tests/harness/test_tools.py`, `tests/harness/test_permissions_modes.py`,
  `tests/harness/test_permission_rules.py`, `tests/harness/test_tools_config_cmds.py`.
</canonical_refs>

<code_context>
## Reusable Assets / Integration Points

- `ToolEntry` already classifies `is_mutating` + `is_network` as DATA at registration (not
  name-matching) — the right place to add `group`, `scope_requirements`, schemas, `audit_behavior`,
  `is_stateful`. Frozen dataclass; extend its fields.
- `PermissionGate.needs_prompt` / `mode_allows` already deny mutating tools by mode tier and gate
  `allow_net` — CAP-09 wires capability mutability through this existing path; do not build a parallel gate.
- MCP tools already become `ToolEntry`s via `_merge_mcp_tools`, but with a SEPARATE
  `permissions_mcp` and bypass paths (`cli.py:3321` mcp-call bypasses gate; `net.py:68` MCP
  namespaced names bypass the bucket). CAP-07 unifies these.
- Telemetry already has `mcp.request`/`mcp.response` rows with arg redaction — model the new
  capability-invocation event (CAP-08) on this.
- `make_toolset` is the single registration choke point — all per-entry hand-tagging (D-01) lands here.
</code_context>

<specifics>
## Specific Ideas

- Acceptance (from PRD §"Phase 1"): agent can list+inspect capabilities; role filters operate on
  capability GROUPS; network tools default-deny unless role allows `net`; every capability
  invocation appears in audit output.
- Preserve all current call sites; extend `ToolEntry`, don't replace it; output JSON-first.
</specifics>

<deferred>
## Deferred Ideas

- **Fine-grained resource scopes** (per-path / per-host capability scopes) — V3 role-cage +
  V4 session-tree scope containment, not V1.
- **`.voss` `team{}` role→capability filtering grammar** — V3 (V1 only makes groups filterable;
  the declarative role roster that consumes them is V3).
- Public CLI help/docs polish for `voss capabilities` beyond list/inspect — later.
</deferred>

---

*Phase: V1-capability-surface-hardening*
*Context gathered 2026-06-06 via /gsd-discuss-phase*
