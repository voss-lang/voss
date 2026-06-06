---
phase: V1-capability-surface-hardening
plan: 04
subsystem: audit
tags: [recorder, audit, capability, telemetry, redaction]

requires:
  - phase: V1-01
    provides: "ToolEntry.group / is_mutating / is_network / audit_behavior"
  - phase: V1-03
    provides: "unified MCP entries that now also flow through this audit path"
provides:
  - "RunRecorder.observe_capability + capability_invocations field (CAP-08)"
  - "RunRecord.capability_invocations forwarded on finalize"
  - "Every entry-resolved invocation (ok/error/denied) audited at the single agent site"
  - "CAP-10 deterministic stub fixture: invocation→audit with no live LLM/MCP/network"
affects: [audit/review product, recorder consumers, V-track verification phases]

tech-stack:
  added: []
  patterns:
    - "Audit row per capability invocation, args shaped by audit_behavior (full/redact_args redact; metadata_only omits)"

key-files:
  created:
    - tests/harness/test_capability_invocation_audit.py
  modified:
    - voss/harness/recorder.py
    - voss/harness/session.py
    - voss/harness/agent.py
    - tests/harness/test_session_redaction.py

key-decisions:
  - "full AND redact_args both pass args through telemetry.redact_tool_args (never store raw args); metadata_only sets args=None"
  - "observe_capability wired in the 3 entry-resolved branches (denied/exception/success); the unknown-tool branch is skipped (no entry → no group/flags)"
  - "All existing recorder.observe + telemetry.emit calls preserved (additive, no consumer regression)"
  - "getattr fallbacks (group→'shell', audit_behavior→'full') so a non-V1 ToolEntry can't crash the audit call"

patterns-established:
  - "capability_invocations is the canonical per-invocation audit stream consumers read"

requirements-completed: [VCAP-08, VCAP-10]

duration: 25min
completed: 2026-06-06
---

# Phase V1-04: Capability Surface Hardening — Invocation Audit Summary

**Every capability invocation now produces a structured RunRecorder audit row (name + group + mutating/network flags + redacted args, honoring audit_behavior), wired at the single agent invocation site across all outcome branches and provable end-to-end with zero live dependencies.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2 / 2 (TDD)
- **Files modified:** 3 source + 1 test created + 1 pre-existing test updated

## Accomplishments

### Task 1 — capability-invocation audit event on RunRecorder
- Added `capability_invocations: list[dict]` to `RunRecorder` (next to skill_events/scope_denials) and the symmetric field on `RunRecord` (session.py), forwarded in `finalize()`.
- Added `observe_capability(name, group, args, *, is_mutating, is_network, audit_behavior="full", ok=True)`: appends `{name, group, is_mutating, is_network, ok, args}`. Args via `telemetry.redact_tool_args` for full/redact_args, `None` for metadata_only. Never raises on malformed args.

### Task 2 — wire at agent site + CAP-10 fixture
- In `_invoke_step_with_gate`, added `recorder.observe_capability(...)` in the **denied**, **exception**, and **success** branches (guarded by `if recorder is not None`, `getattr` fallbacks). Existing `recorder.observe` + `telemetry.emit` calls left intact (additive).
- CAP-10 deterministic fixtures: stub `ToolEntry` (trivial async descriptor) + in-memory `RunRecorder` + permissive/plan `PermissionGate` + null renderer; assert exactly one `capability_invocations` entry with correct name/group/ok on both the success (auto) and denied (plan + mutating) paths — no provider, MCP, or network.

## Verification

- `test_capability_invocation_audit.py` (8) green: recorder unit (full/metadata_only/bad-args/finalize-forward) + agent fixtures (success ok=True, denial ok=False, legacy observe preserved).
- `test_tools.py`, `test_recorder.py`, `test_session_redaction.py`, `test_agent_loop.py`, `test_partition_scheduler.py` green.
- Source: agent.py retains pre-existing `recorder.observe` + `telemetry.emit("tool.result")` (no regression).

## Deviations / known non-blocking failures

- **Updated `tests/harness/test_session_redaction.py`** (`test_run_record_top_level_keys`): added `capability_invocations` to the expected RunRecord key set and bumped the field count 23→24 (additive field; default empty, no credentials).
- **`test_m11_acceptance.py::test_protected_runtime_recorder_files_not_modified_in_git_diff` is transiently red.** It asserts no *uncommitted* `git diff` for `recorder.py` (a working-tree dirty-check, not a permanent freeze) — it fails only because this session's recorder.py edit is uncommitted, and self-resolves once committed (it passed in every prior committed state). V1-04's plan explicitly lists `recorder.py` in `files_modified`, so the modification is authorized; the M11 guard is left unchanged (out of scope, passes post-commit).
- **Pre-existing (not caused by V1-04):** `test_session_iterations`/`test_session_tree_additive` EXIT_REASONS-frozenset drift (extra `timeout`/`killed`), confirmed failing at base commit in earlier sessions. EXIT_REASONS untouched by this plan.
