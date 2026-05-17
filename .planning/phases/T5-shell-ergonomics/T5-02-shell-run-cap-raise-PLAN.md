---
phase: T5-shell-ergonomics
plan: 02
type: execute
wave: 2
depends_on: [T5-01]
files_modified:
  - voss/harness/tools.py
autonomous: true
requirements: [SHELL-01]
user_setup: []

must_haves:
  truths:
    - "shell_run output up to 30KB is returned uncut; beyond 30KB it truncates with the unchanged <truncated, total N bytes> envelope"
    - "Both 4096 literals (shell_run AND _shell_capture) are raised to 30720 for consistency (Flag 1 resolved: raise both)"
    - "The 30s timeout and the [exit N] envelope are untouched (D-07)"
  artifacts:
    - path: "voss/harness/tools.py"
      provides: "30KB output cap for shell_run and _shell_capture"
      contains: "30720"
  key_links:
    - from: "tests/harness/test_shell_timeout.py"
      to: "voss/harness/tools.py make_toolset source"
      via: "source-inspection guard"
      pattern: "30720"
---

<objective>
Raise the `shell_run` output truncation cap from 4096 to 30720 (4KB → 30KB) per SHELL-01 / D-07, AND raise the second, independent `4096` literal in `_shell_capture` (tools.py:398-399) for consistency — Flag 1 resolution: raise BOTH.

Purpose: Real build/test output (pytest, npm) routinely exceeds 4KB; the agent currently loses 96% of a typical failure trace. `fs_read_many` already proved `30720` at tools.py:68. `_shell_capture` backs `voss_check`/git tools; leaving it at 4096 would create an inconsistent cap surface and a confusing review.
Output: Two constant pairs in `voss/harness/tools.py` changed `4096`→`30720`. Envelope text and the 30s timeout unchanged.

Flag 1 decision (recorded for plan-checker): CONTEXT/RESEARCH/D-07 cite only `tools.py:156` ("single-line change at tools.py:156 area"). The pattern-mapper found a SECOND independent `4096` literal at `_shell_capture` (tools.py:398-399). **Resolution: raise both.** Rationale: SHELL-01's intent is "real builds and test runs survive the shell tool"; `voss_check`/`git_diff` route through `_shell_capture` and produce exactly the kind of large output SHELL-01 targets. A split cap (foreground 30KB, capture 4KB) is a latent inconsistency with no upside. D-07's "single-line ... :156 area" describes the headline change, not an exclusion of the sibling literal — confirmed against SHELL-01 verbatim ("output cap raised 4KB → 30KB", tool-agnostic).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T5-shell-ergonomics/T5-PATTERNS.md

<existing_patterns>
shell_run cap — voss/harness/tools.py:155-158 (BEFORE):
```python
text = out.decode("utf-8", errors="replace")
if len(text) > 4096:
    text = text[:4096] + f"\n<truncated, total {len(out)} bytes>"
return f"[exit {proc.returncode}]\n{text}"
```

_shell_capture cap — voss/harness/tools.py:397-400 (BEFORE):
```python
text = out.decode("utf-8", errors="replace")
if len(text) > 4096:
    text = text[:4096] + f"\n<truncated, total {len(out)} bytes>"
return f"[exit {proc.returncode}]\n{text}"
```

Proven sibling already shipped — voss/harness/tools.py:68-69 (`fs_read_many`):
```python
if len(text) > 30720:  # 30KB cap (T2-CONTEXT.md D-13)
    text = text[:30720] + f"\n<truncated, total {len(text)} bytes>"
```

Source-inspection guard (RED until this plan) — tests/harness/test_shell_timeout.py
sibling of `test_real_shell_run_timeout_contract_documented` (added in T5-01),
asserts `"30720" in inspect.getsource(tools_mod.make_toolset)`.
</existing_patterns>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Raise both 4096 caps to 30720</name>
  <files>voss/harness/tools.py</files>
  <action>
    Edit voss/harness/tools.py in exactly two places, surgically (no other line touched):

    1. Inside `shell_run` (tools.py:156-157): change `if len(text) > 4096:` → `if len(text) > 30720:` and `text = text[:4096] + ...` → `text = text[:30720] + ...`. Add a trailing comment matching the shipped sibling style at tools.py:68: `# 30KB cap (T5 SHELL-01 / D-07; matches fs_read_many tools.py:68)`. Keep the `<truncated, total {len(out)} bytes>` envelope text EXACTLY as-is (D-07 — envelope unchanged). Do NOT touch the `wait_for(..., timeout=30.0)` at tools.py:149.

    2. Inside `_shell_capture` (tools.py:398-399): identical change `4096`→`30720` (both occurrences on the line pair). Same comment form. Envelope unchanged.

    Also update the `shell_run` `@tool` description string at tools.py:128 — it currently reads `"... Output truncated to 4KB."`; change `4KB` → `30KB` so the agent-visible description matches the new behavior (the only doc-string the model sees). Do not change anything else in the descriptor.

    Do NOT add new code paths, do NOT change the timeout, do NOT add a constant — match the inline-literal style already shipped at tools.py:68 (no module constant was introduced there).
  </action>
  <verify>
    <automated>python -m pytest "tests/harness/test_shell_timeout.py::test_shell_run_30kb_cap_documented" "tests/harness/test_shell_timeout.py::test_real_shell_run_timeout_contract_documented" -q && python -c "import inspect; from voss.harness import tools as t; s=inspect.getsource(t.make_toolset); assert s.count('30720')>=2, s.count('30720'); assert '4096' not in inspect.getsource(t._shell_capture), 'capture still 4096'"</automated>
    <requirement>SHELL-01</requirement>
    <expected>The new `30720` source guard (RED in T5-01) now passes; `make_toolset` source contains ≥2 occurrences of `30720`; `_shell_capture` no longer contains `4096`; the existing `timeout=30.0` guard still passes (timeout untouched).</expected>
  </verify>
  <done>Both `4096` literals are `30720`; envelope text + 30s timeout unchanged; `@tool` description says `30KB`; the T5-01 source guard `test_shell_run_30kb_cap_documented` is GREEN (referenced by exact node id, not `-k` — no false-green); `test_shell_run_30kb_truncation` in test_t5_shell.py is GREEN.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| subprocess stdout → agent context | Larger untrusted output now reaches the model (30KB vs 4KB) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T5-02 | DoS (context bloat) | shell_run / _shell_capture output cap | accept | 30KB is the deliberate ceiling (D-07, matches the already-shipped fs_read_many cap). Hard cap preserved; only the constant moved. No unbounded growth. |
| T-T5-02b | Tampering | cap constant regression | mitigate | Source-inspection guard `assert "30720" in src` (authored T5-01) fails on any regression below 30720. |
</threat_model>

<verification>
- `pytest tests/harness/test_shell_timeout.py -q` — both source-inspection guards (`timeout=30.0` and `30720`) green.
- `pytest tests/harness/test_t5_shell.py::test_shell_run_30kb_truncation -q` green.
- `_shell_capture` source contains no `4096`; `make_toolset` source contains `30720` (≥2).
</verification>

<success_criteria>
- shell_run and _shell_capture both cap at 30720 with the unchanged `<truncated, total N bytes>` envelope.
- 30s timeout and `[exit N]` prefix untouched (D-07).
- Agent-visible `@tool` description reads `30KB`.
- SHELL-01 regression guard green.
</success_criteria>

<output>
Create `.planning/phases/T5-shell-ergonomics/T5-02-SUMMARY.md` when done.
</output>
