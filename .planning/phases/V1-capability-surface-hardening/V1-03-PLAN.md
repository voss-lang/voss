---
phase: V1-capability-surface-hardening
plan: 03
type: execute
wave: 2
depends_on: ["V1-01"]
files_modified:
  - voss/harness/mcp/registry.py
  - voss/harness/net.py
  - tests/harness/test_mcp_capability_unify.py
autonomous: true
requirements: [VCAP-07, VCAP-09]
must_haves:
  truths:
    - "Every MCP-provided capability defaults to is_mutating=True unless the MCP server explicitly declares the tool read-only"
    - "MCP capabilities carry group=\"mcp\" and scope_requirements include \"mcp\" (and \"net\")"
    - "A mutating MCP capability triggers a gate prompt in mode=edit via the same PermissionGate as native tools"
    - "A server-declared read-only MCP tool does not prompt for mutation"
    - "MCP namespaced capabilities are subject to the net rate-limit bucket on the agent path (the blanket __ bypass no longer applies to agent invocation)"
  artifacts:
    - path: "voss/harness/mcp/registry.py"
      provides: "Default-deny MCP ToolEntry tagging with capability metadata"
      contains: "group"
    - path: "voss/harness/net.py"
      provides: "Scoped MCP net-bucket handling (no blanket bypass for agent path)"
      contains: "__"
    - path: "tests/harness/test_mcp_capability_unify.py"
      provides: "Default-deny + gate-on-mutation + read-only-no-prompt fixtures"
      contains: "def test_"
  key_links:
    - from: "register_mcp_tools"
      to: "ToolEntry(group=\"mcp\", ...)"
      via: "default-deny mutability + capability metadata"
      pattern: "group=\"mcp\""
    - from: "MCP ToolEntry.is_mutating"
      to: "PermissionGate.check (agent.py:1183)"
      via: "same registry, same gate"
      pattern: "is_mutating"
---

<objective>
Unify MCP tools into the same capability registry and gating path as native tools (CAP-07), with a default-deny posture (CAP-09 / D-02): every MCP capability is `is_mutating=True` unless the server explicitly declares it read-only. Tag MCP entries with capability metadata (group="mcp"). Close the agent-path net-bucket bypass for MCP namespaced names.

Purpose: A mislabeled or hostile MCP server must not silently run a mutating tool without a gate prompt. Routing MCP through the same `ToolEntry` + `PermissionGate` as native tools is the safe-by-default unification.
Output: Hardened `register_mcp_tools`, scoped net-bucket handling, and a deterministic MCP-gate fixture test.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V1-capability-surface-hardening/V1-CONTEXT.md

<interfaces>
<!-- register_mcp_tools: voss/harness/mcp/registry.py L66-87 — wraps cached MCP tools as ToolEntry(is_mutating=..., is_network=True). -->
<!-- _is_mutating_from_descriptor: registry.py L15-21 — today reads annotations.destructiveHint default True (scope=="plan" forces False). -->
<!-- Agent gate path: voss/harness/agent.py L1183 gate.check(step.name, step.args, is_mutating=entry.is_mutating, is_network=entry.is_network) — ALREADY gates anything in the registry, incl. MCP entries merged via _merge_mcp_tools (tools.py L743-790). -->
<!-- Net rate-limit bucket: voss/harness/net.py L66-75 acquire(): `if "__" in tool_name: return True, 0.0` blanket-bypasses MCP namespaced names. -->
<!-- PermissionGate.check signature: permissions.py L219 (is_mutating, is_network kwargs). -->
<!-- Developer bypass to PRESERVE: cli.py mcp_call_cmd (~L3321) "voss mcp call" stays a documented PermissionGate bypass per D-02. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Default-deny MCP mutability + capability metadata tagging</name>
  <files>voss/harness/mcp/registry.py, tests/harness/test_mcp_capability_unify.py</files>
  <read_first>
    - voss/harness/mcp/registry.py (full file — L15-21 _is_mutating_from_descriptor, L66-87 register_mcp_tools)
    - voss/harness/tools.py (extended ToolEntry + CAPABILITY_GROUPS from V1-01)
    - .planning/phases/V1-capability-surface-hardening/V1-CONTEXT.md (D-02 default-deny: is_mutating=True unless server declares read-only)
    - .planning/docs/ORCHESTRATION_LAYERS.md §"Phase 1" (CAP-07 unify, CAP-09 gate-on-mutation)
  </read_first>
  <behavior>
    - An MCP tool with NO annotations defaults to is_mutating=True (default-deny, D-02), NOT False.
    - An MCP tool whose annotations declare read-only (annotations.readOnlyHint == True) is is_mutating=False.
    - destructiveHint=False alone does NOT make a tool read-only for mutation purposes unless readOnlyHint is also True — the server must explicitly declare read-only; absence ⇒ treat as mutating.
    - Every MCP ToolEntry carries group="mcp", scope_requirements=("mcp", "net"), is_network=True, audit_behavior="full", is_stateful=False (MCP calls treated order-agnostic unless a future server hint says otherwise).
    - The existing scope=="plan" behavior (descriptor invoke returns a denied-by-scope error for destructive tools at plan) is preserved.
  </behavior>
  <action>
    Rewrite `_is_mutating_from_descriptor` so the default is MUTATING: read `annotations = tool.get("annotations") or {}`; if `annotations.get("readOnlyHint") is True` return False; otherwise return True (default-deny — D-02). Keep the `scope == "plan"` short-circuit returning False only if that is required for the existing plan-scope descriptor behavior; if removing it changes plan-scope semantics, keep it but document in summary. In `register_mcp_tools`, add the capability metadata literals to the `ToolEntry(...)` construction at L82-86: `group="mcp"`, `scope_requirements=("mcp", "net")`, `audit_behavior="full"`, `is_stateful=False`, keeping `descriptor=descriptor`, `is_mutating=_is_mutating_from_descriptor(tool, scope)`, `is_network=True`. Write tests/harness/test_mcp_capability_unify.py with deterministic fixtures (no live MCP server): construct fake tool metadata dicts and call `register_mcp_tools` against a stub McpClient whose `_tools_cache` is pre-seeded (mirror the existing MCP registry test pattern if one exists). Assert: (a) a tool with empty annotations → ToolEntry.is_mutating True; (b) a tool with `annotations={"readOnlyHint": True}` → is_mutating False; (c) a tool with `annotations={"destructiveHint": False}` (no readOnlyHint) → is_mutating True (default-deny); (d) every produced entry has group=="mcp" and "mcp" in scope_requirements and is_network True.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_mcp_capability_unify.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - MCP tool with no annotations → is_mutating True (default-deny asserted)
    - MCP tool with readOnlyHint=True → is_mutating False (asserted)
    - destructiveHint=False without readOnlyHint → is_mutating True (asserted)
    - Every register_mcp_tools entry tagged group="mcp", scope_requirements contains "mcp", is_network True
    - Source assertion: `register_mcp_tools` in voss/harness/mcp/registry.py constructs ToolEntry with `group="mcp"`
  </acceptance_criteria>
  <done>MCP capabilities default to mutating unless server-declared read-only, tagged with capability metadata group="mcp"; deterministic fixtures prove the default-deny + read-only paths.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Gate-on-mutation parity + scoped MCP net bucket</name>
  <files>voss/harness/net.py, tests/harness/test_mcp_capability_unify.py</files>
  <read_first>
    - voss/harness/net.py (L55-100: acquire() with the `if "__" in tool_name` blanket bypass + emit_request)
    - voss/harness/agent.py (L1153-1248 _invoke_step_with_gate — confirms MCP entries in the registry already hit gate.check at L1183)
    - voss/harness/permissions.py (L95-111 mode_allows, L202-211 needs_prompt, L219-327 check — the gate a mutating MCP capability must clear)
    - .planning/phases/V1-capability-surface-hardening/V1-CONTEXT.md (D-02 close agent-path bypasses; developer voss mcp call stays a documented bypass)
  </read_first>
  <behavior>
    - A mutating MCP capability in mode=edit triggers a permission prompt through the SAME PermissionGate as a native mutating tool (no parallel gate).
    - A server-declared read-only MCP capability in mode=edit does not prompt for mutation.
    - The blanket `if "__" in tool_name: return True, 0.0` in net.acquire no longer unconditionally exempts MCP namespaced names from the rate-limit bucket on the agent path: if a bucket is configured for the namespaced name it is honored; only genuinely unconfigured names fall through (as today for native tools).
    - The developer `voss mcp call` path remains a documented PermissionGate bypass (do NOT change cli.py mcp_call_cmd).
  </behavior>
  <action>
    In voss/harness/net.py `acquire`, remove the blanket `if "__" in tool_name: return True, 0.0` short-circuit so MCP namespaced names follow the same `self._buckets.get(tool_name)` path as native tools (unknown/unconfigured names still return `True, 0.0` via the existing fallthrough — preserving today's behavior for tools with no configured bucket, while allowing a configured MCP bucket to apply). Add a code comment that the prior blanket bypass (D-16/NET-07e) is superseded by V1 CAP-07 unification. Do NOT modify the gate call site at agent.py:1183 — it already gates MCP entries via entry.is_mutating/is_network; this task only verifies that path and tightens the net bucket. Extend tests/harness/test_mcp_capability_unify.py: build a registry containing a fake mutating MCP entry (is_mutating=True, group="mcp") and a fake read-only MCP entry (is_mutating=False); instantiate `PermissionGate(mode="edit", auto_yes=False, prompt_fn=<recording stub>)`; call `gate.check(name, args, is_mutating=entry.is_mutating, is_network=entry.is_network)` for each and assert the mutating one invoked the prompt_fn (or returned needing-prompt) while the read-only one did not prompt for mutation (note: is_network=True still subjects it to the net gate — set gate.allow_net=True in the read-only assertion so only the mutation axis is under test). Add a net-bucket test asserting a configured bucket key like `"srv__do_thing"` is consulted (no blanket bypass).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_mcp_capability_unify.py tests/harness/test_permissions_modes.py -q</automated>
  </verify>
  <acceptance_criteria>
    - A mutating MCP capability triggers a gate prompt in mode=edit (recording prompt_fn called / check returns prompt path) — asserted
    - A server-declared read-only MCP capability does not prompt for mutation in mode=edit — asserted
    - net.acquire no longer blanket-returns True for every `__` name; a configured MCP bucket is honored — asserted
    - Source assertion: the `if "__" in tool_name` blanket bypass is removed from voss/harness/net.py acquire (grep no longer finds it as an unconditional early return)
    - `pytest tests/harness/test_permissions_modes.py` still exits 0 (no native-gate regression)
  </acceptance_criteria>
  <done>MCP mutating capabilities clear the same gate as native tools; read-only MCP capabilities skip the mutation prompt; the agent-path net blanket bypass is closed; developer voss mcp call bypass untouched.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| MCP server → harness registry | Tool descriptors + annotations from an external (possibly hostile/mislabeled) MCP server cross into the capability registry and gating decisions. |
| agent → PermissionGate | LLM-chosen tool invocations (native + MCP) cross the gate before execution. |
| capability → network bucket | net-capable capabilities cross the net rate-limit + allow_net axis. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V1-01 | Spoofing/Tampering | MCP server mislabels a mutating tool as read-only | mitigate | D-02 default-deny: `_is_mutating_from_descriptor` returns True unless `readOnlyHint is True`; absence of annotations ⇒ mutating. Test asserts no-annotation and destructiveHint=False (without readOnlyHint) both yield is_mutating=True. |
| T-V1-02 | Elevation of Privilege | MCP capability bypasses PermissionGate via a separate path | mitigate | CAP-07 unification: MCP entries live in the same registry and clear the same `gate.check` at agent.py:1183. Test asserts a mutating MCP entry prompts in mode=edit. Developer `voss mcp call` bypass remains documented (out of agent path). |
| T-V1-03 | Information Disclosure / DoS | net-capable MCP capability reaches network without rate-limit / allow_net | mitigate | scope_requirements include "net" + is_network=True so allow_net default-deny applies; net.acquire blanket `__` bypass removed so configured buckets apply on the agent path. |
| T-V1-SC | Tampering | npm/pip/cargo installs | accept | No new package installs in this plan (edits to existing modules only); no Package Legitimacy Gate triggered. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_mcp_capability_unify.py tests/harness/test_permissions_modes.py tests/harness/test_permission_rules.py -q` exits 0
- Source assertion: cli.py mcp_call_cmd still documents "Bypasses PermissionGate (developer tool)" (unchanged)
</verification>

<success_criteria>
- MCP capabilities default to mutating unless server-declared read-only (D-02)
- MCP capabilities tagged group="mcp" and gated through the same PermissionGate as native tools (CAP-07/09)
- Agent-path net blanket bypass for `__` names closed; developer bypass preserved
</success_criteria>

<output>
Create `.planning/phases/V1-capability-surface-hardening/V1-03-SUMMARY.md` when done
</output>
