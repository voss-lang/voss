---
phase: V1-capability-surface-hardening
plan: 04
type: execute
wave: 3
depends_on: ["V1-01", "V1-03"]
files_modified:
  - voss/harness/recorder.py
  - voss/harness/agent.py
  - tests/harness/test_capability_invocation_audit.py
autonomous: true
requirements: [VCAP-08, VCAP-10]
must_haves:
  truths:
    - "Every capability invocation on the agent path produces an audit record carrying capability name, group, mutating, and network flags"
    - "Capability invocation audit args are redacted using the existing telemetry.redact_tool_args path"
    - "Any capability can be invoked with stub inputs against a deterministic in-memory recorder and its invocation event asserted, with no live LLM/MCP/network"
  artifacts:
    - path: "voss/harness/recorder.py"
      provides: "Capability-invocation audit event on RunRecorder"
      contains: "capability"
    - path: "voss/harness/agent.py"
      provides: "Invocation hook emitting the capability event with group/flags"
      contains: "group"
    - path: "tests/harness/test_capability_invocation_audit.py"
      provides: "Deterministic stub-fixture invocation + audit assertions (CAP-10)"
      contains: "def test_"
  key_links:
    - from: "_invoke_step_with_gate (agent.py)"
      to: "RunRecorder capability-invocation event"
      via: "entry metadata (group, is_mutating, is_network) passed to recorder"
      pattern: "capability"
    - from: "capability invocation event"
      to: "telemetry.redact_tool_args"
      via: "redacted args in the audit row"
      pattern: "redact_tool_args"
---

<objective>
Emit a recorder audit event on every capability invocation (CAP-08) carrying capability name + group + mutating/network flags + redacted args, modeled on the existing `mcp.request`/`mcp.response` telemetry rows. Lock in CAP-10 stub-testability with a deterministic fixture proving any capability invocation appears in audit output without a live LLM/MCP/network.

Purpose: "Every capability invocation appears in audit output" is the phase acceptance criterion; CAP-10 guarantees this is testable deterministically.
Output: A capability-invocation audit event on RunRecorder, wired at the agent invocation site, plus a deterministic stub-fixture test.
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
<!-- RunRecorder: voss/harness/recorder.py L150-239 — observe(tool_name, args, result, *, ok), observe_skill_event(...), observe_scope_denial(...). Pattern to mirror for a new capability event list field + observe method. -->
<!-- Agent invocation site: voss/harness/agent.py L1153-1248 _invoke_step_with_gate — has `entry` (ToolEntry), `step.name`, `step.args`, `recorder`. Already calls recorder.observe(...) at L1181/1204/1233/1247 and telemetry.emit("tool.call"/"tool.result", ...) with telemetry.redact_tool_args. -->
<!-- telemetry: voss/harness/telemetry.py — emit(event, level, *, data), redact_tool_args(args), enabled(). Existing mcp.request/mcp.response rows documented L20-21. -->
<!-- ToolEntry (V1-01): entry.group, entry.is_mutating, entry.is_network, entry.audit_behavior, entry.capability_dict(). -->
<!-- audit_behavior values: full | redact_args | metadata_only (reuse redact_tool_args for redact_args; metadata_only omits args). -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Capability-invocation audit event on RunRecorder</name>
  <files>voss/harness/recorder.py, tests/harness/test_capability_invocation_audit.py</files>
  <read_first>
    - voss/harness/recorder.py (L150-239: RunRecorder fields + observe / observe_skill_event / observe_scope_denial pattern; L352-387 finalize forwarding)
    - voss/harness/telemetry.py (L105-130 redact_tool_args; L190+ emit)
    - voss/harness/tools.py (ToolEntry.audit_behavior + capability_dict from V1-01)
    - .planning/phases/V1-CONTEXT.md (CAP-08 reuse RunRecorder/telemetry.emit; audit_behavior full|redact_args|metadata_only)
  </read_first>
  <behavior>
    - RunRecorder gains a `capability_invocations: list[dict]` field (defaults empty) and an `observe_capability(name, group, args, *, is_mutating, is_network, audit_behavior, ok)` method.
    - The recorded event carries: name, group, is_mutating, is_network, ok, and args rendered per audit_behavior — `full`/`redact_args` ⇒ telemetry.redact_tool_args(args) (full and redact_args both redact via the existing path per D-discretion; if `full` is intended to keep raw args, state the chosen semantics in summary), `metadata_only` ⇒ args omitted entirely (e.g. args field set to None or absent).
    - The new field is forwarded on `finalize()` into the RunRecord (if RunRecord has a matching field; if not, add it symmetrically — check RunRecord dataclass).
    - observe_capability never raises on malformed args (mirrors observe tolerance).
  </behavior>
  <action>
    Add `capability_invocations: list[dict] = field(default_factory=list)` to RunRecorder (next to skill_events/scope_denials). Add `observe_capability(self, name, group, args, *, is_mutating, is_network, audit_behavior="full", ok=True)` that appends a dict {name, group, is_mutating, is_network, ok, args:<rendered>}: import telemetry locally (as elsewhere in the module) and render args = `telemetry.redact_tool_args(dict(args))` for "full"/"redact_args", or omit/None for "metadata_only". Check the `RunRecord` dataclass (same file or recorder schema module) and, if it lists skill_events/scope_denials, add `capability_invocations` symmetrically and forward `capability_invocations=list(self.capability_invocations)` in `finalize()`. Write tests/harness/test_capability_invocation_audit.py: instantiate `RunRecorder.start()`; call `observe_capability("fs_write", "fs", {"path":"x","content":"y"}, is_mutating=True, is_network=False, audit_behavior="full", ok=True)`; assert one entry with name/group/is_mutating/ok and redacted args present; call with audit_behavior="metadata_only" and assert no raw args leaked; finalize and assert the RunRecord carries the invocations (if forwarded).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_capability_invocation_audit.py::test_recorder_observe_capability -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `RunRecorder` declares `capability_invocations` and `observe_capability(...)` (source grep)
    - observe_capability records name, group, is_mutating, is_network, ok, and redacted args
    - audit_behavior="metadata_only" omits raw args (no leak asserted)
    - finalize() forwards capability_invocations when RunRecord supports it (or summary justifies why not)
  </acceptance_criteria>
  <done>RunRecorder emits a structured capability-invocation audit event with group + flags + redacted args honoring audit_behavior; unit-tested.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire the audit event at the agent invocation site + deterministic stub fixture (CAP-10)</name>
  <files>voss/harness/agent.py, tests/harness/test_capability_invocation_audit.py</files>
  <read_first>
    - voss/harness/agent.py (L1153-1248 _invoke_step_with_gate — the single resolve/gate/invoke site; existing recorder.observe + telemetry.emit calls)
    - voss/harness/recorder.py (observe_capability from Task 1)
    - .planning/docs/ORCHESTRATION_LAYERS.md §"Phase 1" (CAP-08 every invocation in audit; CAP-10 stub inputs + deterministic fixtures)
  </read_first>
  <behavior>
    - On every capability invocation through _invoke_step_with_gate (success AND failure/denied paths), `recorder.observe_capability(...)` is called with the resolved entry's name, entry.group, args, entry.is_mutating, entry.is_network, entry.audit_behavior, and ok status — so EVERY invocation (allowed-ok, allowed-error, denied) appears in audit.
    - The existing recorder.observe(...) and telemetry.emit(...) calls are preserved (additive, not replaced) to avoid regressing existing audit/telemetry consumers.
    - A capability can be invoked end-to-end against a stub ToolEntry + in-memory RunRecorder + auto_yes/permissive gate with no live provider, MCP server, or network, and its invocation event asserted (CAP-10).
  </behavior>
  <action>
    In `_invoke_step_with_gate`, after `entry` is resolved and at each terminal outcome (denied branch, exception branch, success branch — mirror where `recorder.observe(...)` is already called), add a `recorder.observe_capability(step.name, getattr(entry, "group", "shell"), step.args, is_mutating=entry.is_mutating, is_network=entry.is_network, audit_behavior=getattr(entry, "audit_behavior", "full"), ok=<branch-appropriate>)` call guarded by `if recorder is not None`. Keep all existing observe/emit calls. Use `getattr` fallbacks so the call is resilient if a non-V1 ToolEntry ever appears. Extend tests/harness/test_capability_invocation_audit.py with a CAP-10 deterministic fixture test: build a stub ToolEntry wrapping a trivial async descriptor returning a fixed string (via make_toolset on a tmp_path OR a hand-built ToolEntry with group="fs"); build a `PermissionGate(mode="auto", auto_yes=True)`; build `RunRecorder.start()`; construct a minimal step object (SimpleNamespace name/args) and a null/stub renderer; `await _invoke_step_with_gate(step, tools, gate, renderer, recorder)`; assert the recorder.capability_invocations has exactly one entry for the invoked name with the correct group + ok=True, deterministically (no randomness, no network). Add a second case driving the denied path (mode="plan", mutating tool) and assert an invocation event with ok=False is recorded.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_capability_invocation_audit.py -q</automated>
  </verify>
  <acceptance_criteria>
    - Every branch (ok / error / denied) of _invoke_step_with_gate calls recorder.observe_capability — source grep finds observe_capability in agent.py
    - Existing recorder.observe + telemetry.emit calls preserved (still present in agent.py)
    - CAP-10 fixture: a stub capability invoked against an in-memory recorder produces exactly one capability_invocations entry with the right name+group+ok, with no live LLM/MCP/network
    - Denied-path invocation records ok=False (asserted)
    - `pytest tests/harness/test_capability_invocation_audit.py` exits 0
  </acceptance_criteria>
  <done>Capability invocations are audited at the single agent invocation site on all outcome branches; CAP-10 deterministic stub fixtures prove invocation-to-audit end to end with no live dependencies.</done>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_capability_invocation_audit.py tests/harness/test_tools.py -q` exits 0
- Source assertion: agent.py _invoke_step_with_gate still contains the pre-existing recorder.observe and telemetry.emit("tool.result") calls (no regression)
</verification>

<success_criteria>
- Every capability invocation emits a recorder audit event with name + group + mutating/network flags + redacted args (CAP-08)
- audit_behavior honored (full/redact_args redact; metadata_only omits args)
- CAP-10 deterministic stub-fixture test proves any capability's invocation appears in audit output with zero live dependencies
</success_criteria>

<output>
Create `.planning/phases/V1-capability-surface-hardening/V1-04-SUMMARY.md` when done
</output>
