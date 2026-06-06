---
phase: V1-capability-surface-hardening
plan: 03
subsystem: security
tags: [mcp, permissions, capability, default-deny, gate, rate-limit]

requires:
  - phase: V1-01
    provides: "extended ToolEntry (group/scope_requirements/audit/stateful)"
provides:
  - "MCP capabilities default-deny: is_mutating=True unless server declares readOnlyHint"
  - "MCP ToolEntry tagged group=mcp, scope_requirements=(mcp,net), is_network=True"
  - "Gate-on-mutation parity: mutating MCP capabilities prompt in edit mode via the same PermissionGate"
  - "Agent-path net blanket __ bypass removed; configured MCP buckets honored"
affects: [MCP security posture, V1-04, any agent invoking MCP tools]

tech-stack:
  added: []
  patterns:
    - "Default-deny external trust boundary: absence of an explicit read-only declaration ⇒ mutating"

key-files:
  created:
    - tests/harness/test_mcp_capability_unify.py
  modified:
    - voss/harness/mcp/registry.py
    - voss/harness/net.py
    - voss/harness/permissions.py
    - tests/harness/mcp/test_mcp_scope.py

key-decisions:
  - "_is_mutating_from_descriptor: default True; only annotations.readOnlyHint is True → False. destructiveHint=False alone does NOT imply read-only"
  - "Removed the scope=='plan'→False short-circuit from mutability (it labelled every plan-scoped tool non-mutating, defeating default-deny); plan-scope destructive denial still enforced in the descriptor's invoke"
  - "MCP scope_requirements=(mcp,net) — both axes apply (capability bucket + allow_net)"
  - "Gate fix is MCP-scoped (user decision): prompt when is_mutating AND name contains '__', respecting auto_yes/auto — closes the hostile-MCP hole without changing native-tool prompt behavior"

patterns-established:
  - "External (MCP) capabilities cross into the SAME registry + gate as native tools (CAP-07 unification)"

requirements-completed: [VCAP-07, VCAP-09]

duration: 30min
completed: 2026-06-06
---

# Phase V1-03: Capability Surface Hardening — MCP Unification + Default-Deny Summary

**MCP-provided capabilities now default to mutating unless the server explicitly declares them read-only, carry full capability metadata (group=mcp), and clear the same PermissionGate as native tools — closing the path where a hostile/mislabeled MCP server could run a mutating tool with no prompt.**

## Performance

- **Duration:** ~30 min (incl. surfacing a plan-vs-reality security gap)
- **Tasks:** 2 / 2 (TDD)
- **Files modified:** 3 source + 1 test created + 1 pre-existing test updated

## Accomplishments

### Task 1 — Default-deny MCP mutability + metadata tagging
- Rewrote `_is_mutating_from_descriptor(tool)` (dropped the `scope` arg): returns True unless `annotations.readOnlyHint is True`. Absence of annotations ⇒ mutating; `destructiveHint=False` alone is insufficient.
- Removed the `scope=='plan'→False` short-circuit (it made every plan-scoped tool non-mutating, the opposite of default-deny). Plan-scope denial of destructive tools is still enforced in `_make_mcp_descriptor.invoke` (unchanged).
- `register_mcp_tools` ToolEntry now tags `group="mcp", scope_requirements=("mcp","net"), audit_behavior="full", is_stateful=False`.

### Task 2 — Gate-on-mutation parity + scoped net bucket
- **net.py:** removed the blanket `if "__" in tool_name: return True, 0.0` bypass in `acquire` — MCP namespaced names now follow the same bucket lookup as native tools (unconfigured names still fall through to no-limit).
- **permissions.py (deviation — see below):** in `_check_impl`, after the name-set `needs_prompt`, force a prompt when `is_mutating and "__" in tool_name and not auto_yes and mode != "auto"`. The WRITE/SHELL name-sets don't include MCP-namespaced tools, so without this a mutating MCP capability ran in edit mode with NO prompt.
- Developer `voss mcp call` bypass left untouched (still documents "Bypasses PermissionGate").

## Verification

- `test_mcp_capability_unify.py` (8) green: default-deny / readOnlyHint / destructiveHint-only cases; metadata tagging; mutating-MCP-prompts-in-edit; readonly-MCP-no-prompt; configured-bucket-honored.
- Plan regression set green: `test_permissions_modes.py`, `test_permission_rules.py`, full `mcp`/`net`/`rate_limit` slice, `test_tools.py`, `test_capability_metadata.py`, `test_permissions.py`.
- `voss mcp call` bypass docstring intact; net blanket bypass removed (grep confirms).

## Deviations

- **Touched `voss/harness/permissions.py` (not in the plan's `files_modified`).** The plan asserted "agent.py:1183 already gates MCP entries via is_mutating" — FALSE for the prompt axis: `needs_prompt`/`mode_allows` are name-set based (WRITE/SHELL), so mutating MCP tools never prompted in edit mode. Closing CAP-09 required a gate change. Surfaced to the user, who chose the **MCP-scoped (narrow)** fix over a broad all-mutating fix to avoid changing native-tool prompt UX. Native gating behavior is unchanged.
- **Updated pre-existing `tests/harness/mcp/test_mcp_scope.py`** (2 assertions): under default-deny, `write_file` (readOnlyHint=False) is now `is_mutating=True` (was False via the removed plan-scope short-circuit — it genuinely writes); and the merge test's `read_text_file` mock now declares `readOnlyHint=True` so it correctly stays read-only. These encode the new D-02 contract.

## Threat model

- T-V1-01 (server mislabels mutating tool read-only): mitigated — default-deny; only explicit `readOnlyHint:true` downgrades.
- T-V1-02 (MCP bypasses gate): mitigated — unified registry + the MCP-scoped prompt gate; mutating MCP prompts in edit.
- T-V1-03 (net without rate-limit/allow_net): mitigated — scope includes net + is_network=True (allow_net default-deny) and the blanket bucket bypass is removed.
