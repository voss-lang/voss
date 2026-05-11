---
phase: M1-harness-happy-path
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/tools.py
  - voss/harness/permissions.py
  - tests/harness/test_permissions_modes.py
  - tests/harness/test_tools.py
autonomous: true
requirements:
  - CTRL-01
  - CTRL-02
  - CTRL-03
  - CTRL-04
  - CTRL-05
  - CTRL-06
  - CTRL-07
tags:
  - harness
  - permissions
  - tools

must_haves:
  truths:
    - "Every registered tool exposes an explicit is_mutating boolean."
    - "Mode `plan` returns denied for any mutating tool call."
    - "Mode `edit` allows fs_write/fs_edit with prompt, denies shell_run structurally."
    - "Mode `auto` allows shell_run but still enforces shell allowlist + timeout."
    - "Mode is escalation-gated: `/mode auto` from REPL refuses without --confirm (enforced in Plan 05; this plan exposes the predicate)."
  artifacts:
    - path: "voss/harness/tools.py"
      provides: "Tool registry that returns ToolEntry objects carrying is_mutating"
      contains: "is_mutating"
    - path: "voss/harness/permissions.py"
      provides: "Mode tier predicate mode_allows(mode, tool_name, is_mutating)"
      contains: "def mode_allows"
    - path: "tests/harness/test_permissions_modes.py"
      provides: "Allow/deny matrix coverage per tier"
  key_links:
    - from: "voss/harness/permissions.py::PermissionGate.check"
      to: "voss/harness/tools.py::ToolEntry.is_mutating"
      via: "mode_allows(self.mode, tool_name, entry.is_mutating)"
      pattern: "mode_allows\\("
---

<objective>
Establish the permission-tier foundation for M1: every tool carries an explicit `is_mutating` flag, and `PermissionGate` uses strict tier semantics to allow/deny tool calls before the existing `[y/once/always/n]` prompt fires.

Purpose: This is the structural enforcement layer that makes `plan` mode genuinely read-only (not "advise read-only"). Every other M1 plan that touches modes depends on this contract. Implements D-05, D-06, and the structural half of D-07. Covers CTRL-01..07.

Output:
- `make_toolset(cwd)` returns `dict[str, ToolEntry]` where `ToolEntry` bundles the existing `ToolDescriptor` callable with a new `is_mutating: bool` field.
- `voss/harness/permissions.py` exposes `mode_allows(mode, tool_name, is_mutating) -> tuple[bool, str]` returning `(False, "denied by mode plan")` etc.
- `PermissionGate.check` consults `mode_allows` first; structural denials skip the prompt entirely.
- Test matrix in `tests/harness/test_permissions_modes.py` covers all 3 modes x 3 tool categories (read/write/shell).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M1-harness-happy-path/M1-CONTEXT.md
@voss/harness/tools.py
@voss/harness/permissions.py
@voss/harness/sandbox.py
@tests/harness/test_tools.py

<interfaces>
Current tool registry shape (from voss/harness/tools.py):
```python
def make_toolset(cwd: Path) -> dict[str, Any]:
    # Returns dict of name -> ToolDescriptor (from voss_runtime @tool decorator).
    # ToolDescriptor exposes .name, .description, .parameters, .invoke(**kwargs).
```

Current PermissionGate (voss/harness/permissions.py):
```python
READ_ONLY = {"fs_read", "fs_glob", "fs_grep", "git_status", "git_diff", "voss_check"}
WRITE = {"fs_write", "fs_edit"}
SHELL = {"shell_run"}

@dataclass
class PermissionGate:
    mode: Mode = "edit"  # Literal["plan", "edit", "auto"]
    store: PermissionStore | None = None
    auto_yes: bool = False

    def needs_prompt(self, tool_name: str) -> bool: ...
    def check(self, tool_name: str, args: dict) -> tuple[bool, str]: ...
```

Note: existing READ_ONLY/WRITE/SHELL string sets are pattern-matching by name. D-06 requires
data-driven classification via an explicit `is_mutating` flag attached to each tool descriptor.
Keep the string sets only for backward-compatible callers; new logic must use is_mutating.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add is_mutating flag to tool registry</name>
  <files>voss/harness/tools.py, tests/harness/test_tools.py</files>
  <read_first>
    - voss/harness/tools.py (entire file — 170 LOC, all 9 tool definitions)
    - voss/harness/permissions.py (READ_ONLY/WRITE/SHELL sets define current classification)
    - tests/harness/test_tools.py (existing test shape — assertion patterns to mirror)
    - .planning/phases/M1-harness-happy-path/M1-CONTEXT.md (§decisions D-05, D-06)
  </read_first>
  <behavior>
    - Test 1: `make_toolset(tmp_path)` returns a dict where every value is a `ToolEntry` with `.descriptor` (the original ToolDescriptor) and `.is_mutating: bool`.
    - Test 2: `fs_read`, `fs_glob`, `fs_grep`, `git_status`, `git_diff`, `voss_check` all have `is_mutating == False`.
    - Test 3: `fs_write`, `fs_edit`, `shell_run` all have `is_mutating == True`.
    - Test 4: `ToolEntry.descriptor.invoke(...)` still works (backward compat for run_turn).
    - Test 5: Iterating registry entries: `assert sum(1 for e in tools.values() if e.is_mutating) == 3`.
  </behavior>
  <action>
1. In `voss/harness/tools.py`, add a `ToolEntry` dataclass at module level:
```python
from dataclasses import dataclass
from voss_runtime import ToolDescriptor

@dataclass(frozen=True)
class ToolEntry:
    descriptor: ToolDescriptor
    is_mutating: bool

    @property
    def name(self) -> str:
        return self.descriptor.name

    @property
    def description(self) -> str:
        return self.descriptor.description

    @property
    def parameters(self) -> dict:
        return self.descriptor.parameters

    async def invoke(self, **kwargs):
        return await self.descriptor.invoke(**kwargs)
```

2. Change `make_toolset(cwd: Path) -> dict[str, ToolEntry]`. The return dict literal becomes:
```python
return {
    "fs_read": ToolEntry(descriptor=fs_read, is_mutating=False),
    "fs_glob": ToolEntry(descriptor=fs_glob, is_mutating=False),
    "fs_grep": ToolEntry(descriptor=fs_grep, is_mutating=False),
    "fs_write": ToolEntry(descriptor=fs_write, is_mutating=True),
    "fs_edit": ToolEntry(descriptor=fs_edit, is_mutating=True),
    "shell_run": ToolEntry(descriptor=shell_run, is_mutating=True),
    "git_status": ToolEntry(descriptor=git_status, is_mutating=False),
    "git_diff": ToolEntry(descriptor=git_diff, is_mutating=False),
    "voss_check": ToolEntry(descriptor=voss_check, is_mutating=False),
}
```

3. Per D-06: classification is data-driven. Do NOT introduce a function like `_is_mutating_by_name`. Hardcoded per-tool boolean at registration is the contract.

4. In `tests/harness/test_tools.py`, add a new test class `TestToolEntryClassification` covering behaviors 1-5 above. Use `tmp_path` fixture for cwd.

5. Run `pytest tests/harness/test_tools.py -x`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/test_tools.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "is_mutating" voss/harness/tools.py` returns at least 10 (one per tool + class def).
    - `grep -c "class ToolEntry" voss/harness/tools.py` returns 1.
    - `grep -c "is_mutating=True" voss/harness/tools.py` returns exactly 3 (fs_write, fs_edit, shell_run).
    - `grep -c "is_mutating=False" voss/harness/tools.py` returns exactly 6.
    - `pytest tests/harness/test_tools.py -x` exits 0.
    - `grep -c "TestToolEntryClassification" tests/harness/test_tools.py` returns at least 1.
  </acceptance_criteria>
  <done>ToolEntry dataclass exported; all 9 tools registered with explicit is_mutating; tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add mode_allows predicate and wire structural denial into PermissionGate</name>
  <files>voss/harness/permissions.py, voss/harness/agent.py, tests/harness/test_permissions_modes.py</files>
  <read_first>
    - voss/harness/permissions.py (entire file — 126 LOC)
    - voss/harness/agent.py:182-207 (the tool-invocation loop that calls gate.check)
    - voss/harness/tools.py (ToolEntry from Task 1)
    - .planning/phases/M1-harness-happy-path/M1-CONTEXT.md (§decisions D-05: strict tier mapping)
  </read_first>
  <behavior>
    - Test 1 (plan mode): `mode_allows("plan", "fs_read", False) == (True, "ok")`.
    - Test 2 (plan mode): `mode_allows("plan", "fs_write", True) == (False, "denied by mode plan")`.
    - Test 3 (plan mode): `mode_allows("plan", "shell_run", True) == (False, "denied by mode plan")`.
    - Test 4 (edit mode): `mode_allows("edit", "fs_write", True) == (True, "ok")` (still prompts in gate.check, but mode allows).
    - Test 5 (edit mode): `mode_allows("edit", "shell_run", True) == (False, "denied by mode edit")` — shell_run is special-cased, NOT available in edit per D-05.
    - Test 6 (auto mode): `mode_allows("auto", "shell_run", True) == (True, "ok")`.
    - Test 7 (gate integration): with `PermissionGate(mode="plan")`, `gate.check("fs_write", {"path": "x", "content": "y"})` returns `(False, "denied by mode plan")` WITHOUT calling the interactive prompt — verify by injecting a prompt_fn that records calls.
    - Test 8 (gate integration): with `PermissionGate(mode="edit", auto_yes=True)`, `gate.check("shell_run", {"cmd": "ls"})` returns `(False, "denied by mode edit")`.
  </behavior>
  <action>
1. In `voss/harness/permissions.py`, add at module level (below the SHELL constant):
```python
def mode_allows(mode: Mode, tool_name: str, is_mutating: bool) -> tuple[bool, str]:
    """Strict tier check. Returns (allowed_by_mode, reason).

    plan : read-only — denies all mutating tools.
    edit : reads + fs_write/fs_edit — explicitly denies shell_run.
    auto : everything — caller still enforces allowlist/timeouts downstream.
    """
    if mode == "plan":
        if is_mutating:
            return False, "denied by mode plan"
        return True, "ok"
    if mode == "edit":
        if tool_name == "shell_run":
            return False, "denied by mode edit"
        return True, "ok"
    # auto
    return True, "ok"
```

2. Extend `PermissionGate` with an `is_mutating` lookup. Change `check` signature:
```python
def check(self, tool_name: str, args: dict, *, is_mutating: bool = False) -> tuple[bool, str]:
    allowed, why = mode_allows(self.mode, tool_name, is_mutating)
    if not allowed:
        return False, why
    if not self.needs_prompt(tool_name):
        return True, "auto"
    # ... rest unchanged
```

   Keep the `needs_prompt` body backward-compatible (still uses READ_ONLY/WRITE/SHELL sets for prompting policy), but factor structural denial through `mode_allows` first.

3. In `voss/harness/agent.py`, the tool-invocation loop (lines ~185-207) currently does:
```python
allowed, why = gate.check(step.name, step.args)
```
   Change to thread `is_mutating` through. The `tools` parameter type is now `dict[str, ToolEntry]`. Update line 186 from `td = tools.get(step.name)` and use:
```python
entry = tools.get(step.name)
if entry is None:
    # ... existing unknown-tool branch
allowed, why = gate.check(step.name, step.args, is_mutating=entry.is_mutating)
# ... and replace td.invoke(...) with entry.invoke(...)
```

   Also update the type hint on `run_turn(tools: dict[str, ToolEntry], ...)`. Import `ToolEntry` from `.tools`. The `_format_tools` helper still works because `ToolEntry.parameters` proxies to descriptor.

4. Create `tests/harness/test_permissions_modes.py`:
```python
from voss.harness.permissions import PermissionGate, PermissionStore, mode_allows


class TestModeAllows:
    def test_plan_allows_reads(self): ...
    def test_plan_denies_writes(self): ...
    def test_plan_denies_shell(self): ...
    def test_edit_allows_writes(self): ...
    def test_edit_denies_shell(self): ...
    def test_auto_allows_everything(self): ...


class TestGateStructuralDenial:
    def test_plan_mode_denies_write_without_prompting(self, tmp_path): ...
    def test_edit_mode_denies_shell_without_prompting(self, tmp_path): ...
```
   In the gate tests, inject `prompt_fn=lambda *a, **kw: pytest.fail("prompt called")` to prove structural denial bypasses prompting.

5. Run `pytest tests/harness/test_permissions_modes.py tests/harness/test_tools.py tests/harness/test_agent_integration.py -x`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/test_permissions_modes.py tests/harness/test_tools.py tests/harness/test_agent_integration.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def mode_allows" voss/harness/permissions.py` returns 1.
    - `grep -c "denied by mode plan" voss/harness/permissions.py` returns at least 1.
    - `grep -c "denied by mode edit" voss/harness/permissions.py` returns at least 1.
    - `grep -c "is_mutating" voss/harness/permissions.py` returns at least 2.
    - `grep -c "is_mutating=entry.is_mutating" voss/harness/agent.py` returns 1.
    - `pytest tests/harness/test_permissions_modes.py -x` exits 0.
    - `pytest tests/harness/test_agent_integration.py -x` exits 0 (existing agent integration test still passes after signature change).
  </acceptance_criteria>
  <done>mode_allows lives in permissions.py; PermissionGate.check structurally denies before prompting; agent loop threads is_mutating from ToolEntry; matrix tests + existing agent tests pass.</done>
</task>

</tasks>

<verification>
- `pytest tests/harness/test_tools.py tests/harness/test_permissions_modes.py tests/harness/test_agent_integration.py -x` exits 0.
- Manual: `python -c "from voss.harness.tools import make_toolset; from pathlib import Path; t = make_toolset(Path('.')); print({k: v.is_mutating for k, v in t.items()})"` shows the 6 read-only / 3 mutating split.
- Manual: `python -c "from voss.harness.permissions import mode_allows; print(mode_allows('plan', 'fs_write', True))"` prints `(False, 'denied by mode plan')`.
</verification>

<success_criteria>
- Tool registry is data-driven for mutation classification (D-06).
- `plan` mode structurally denies all mutating tools (D-05).
- `edit` mode structurally denies `shell_run` (D-05).
- `auto` mode allows everything subject to downstream allowlist/timeout (D-05).
- Existing `[y/once/always/n]` prompt path is preserved for in-mode prompts (D-07 structural half).
- Existing agent loop continues to function with new ToolEntry shape.
</success_criteria>

<output>
After completion, create `.planning/phases/M1-harness-happy-path/M1-01-SUMMARY.md` covering: ToolEntry dataclass, mode_allows predicate, integration points for downstream plans (Plan 04 edit-scope gate, Plan 05 /mode REPL).
</output>
