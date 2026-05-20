---
phase: O2-voss-team-spec-roster
plan: 03
type: execute
wave: 3
depends_on: [O2-01, O2-02]
files_modified:
  - voss/harness/permissions.py
  - voss/harness/team.py
  - voss/harness/tools.py
  - tests/harness/test_team_gate_compile.py        # NEW
  - tests/harness/test_team_tool_filter.py         # NEW
  - tests/harness/test_team_per_role_net.py        # NEW
  - tests/harness/test_allow_net.py                # MODIFIED (regression for per-gate net override)
autonomous: true
requirements: [OTEAM-03, OTEAM-07]
tech_stack: [python-3.11, pytest, dataclasses-frozen]
key_files:
  created:
    - tests/harness/test_team_gate_compile.py
    - tests/harness/test_team_tool_filter.py
    - tests/harness/test_team_per_role_net.py
  modified:
    - voss/harness/permissions.py
    - voss/harness/team.py
    - voss/harness/tools.py
    - tests/harness/test_allow_net.py
estimated_duration: ~3 hours implementation; ~35% planner-context budget
requirements_addressed: [OTEAM-03, OTEAM-07]

must_haves:
  truths:
    - "`gate_for_role(spec, base_gate)` produces a `PermissionGate` whose `mode` is the min of `base_gate.mode` and `spec.mode` (cap, never expand)."
    - "`gate_for_role` reuses the `scoped_gate` pattern from `voss/harness/skill/scope.py:82-95` — `_min_mode` is shared, `auto_yes=True`, `project_policy` preserved, `store=None`."
    - "`PermissionGate` accepts a new `allow_net: bool | None = None` field — `None` means defer to the process-level `voss_runtime._config.allow_net` (current behaviour); `True`/`False` overrides for that gate's evaluation."
    - "A specialist role's compiled gate has `allow_net=True` IFF `spec.net is True`; non-net roles get `allow_net=False`, blocking `web_fetch`/`web_search` even when the process `--allow-net` is set."
    - "`filter_toolset_for_role(spec, base_toolset)` returns a subset of `make_toolset()`'s output. If `spec.tools` is None → unfiltered. If set → contains only entries whose name is in `spec.tools`, with `web_fetch`/`web_search` included IFF `\"net\"` is in `spec.tools`."
    - "Existing `tests/harness/test_allow_net.py` continues to pass — no regression on the process-level allow_net gate (the new per-gate override is additive)."
  artifacts:
    - path: "voss/harness/permissions.py"
      provides: "Per-gate `allow_net` override; `_check_impl` honours the override when set"
      contains: "allow_net: bool | None"
    - path: "voss/harness/team.py"
      provides: "`gate_for_role(spec, base_gate)` + `filter_toolset_for_role(spec, base_toolset)`"
      contains: "def gate_for_role"
    - path: "voss/harness/tools.py"
      provides: "filter_toolset_by_names helper (or equivalent) if minimal addition; otherwise unchanged"
      contains: ""
    - path: "tests/harness/test_team_gate_compile.py"
      provides: "OTEAM-07 acceptance"
      contains: "def test_gate_for_role_caps_mode"
    - path: "tests/harness/test_team_per_role_net.py"
      provides: "OTEAM-03 net portion + cage-against-AI-role-leaking-net regression"
      contains: "def test_ai_role_gate_grants_net"
  key_links:
    - from: "voss/harness/team.py::gate_for_role"
      to: "voss/harness/skill/scope.py::_min_mode"
      via: "reuse (import, not re-implement)"
      pattern: "from .skill.scope import _min_mode"
    - from: "voss/harness/team.py::gate_for_role"
      to: "voss/harness/permissions.py::PermissionGate"
      via: "constructor with allow_net override"
      pattern: "PermissionGate\\("
    - from: "voss/harness/team.py::filter_toolset_for_role"
      to: "voss/harness/tools.py::ToolEntry"
      via: "dict comprehension over base toolset"
      pattern: "ToolEntry"
---

<objective>
Close the **per-role authorization** loop: take an enriched `SubagentSpec` (from O2-02) plus a base `PermissionGate` and produce a per-role `PermissionGate` + filtered toolset. This is what O3/O5 will use at dispatch time to enforce "specialist X can only do Y".

**Purpose:**
- OTEAM-07 — `gate_for_role` exists, reuses `scoped_gate` shape, caps mode (cap-not-expand), preserves project policy.
- OTEAM-03 (net portion) — AI role's gate has `allow_net=True`; engineer roles' gates have `allow_net=False` even when process-level allow_net is set.
- Reuse over re-implementation — `_min_mode` from `voss/harness/skill/scope.py:74-79` is the shared primitive; we IMPORT it.

**Output:**
- `PermissionGate` extended with `allow_net: bool | None = None`; check path honours the override (Research §3 R3, OQ-A8).
- `voss/harness/team.py::gate_for_role` + `filter_toolset_for_role` helpers + tests.
- ~15 new tests, all green; existing net tests unchanged.

**Scope fence:** This plan compiles a per-role gate **as a value**. It does NOT wire `gate_for_role` into `run_subagent`'s dispatch (that's O5 — the EM picks a role then constructs the child gate). It does NOT change `make_toolset` (that stays the source of truth for tool descriptors). The filter is a post-construction subset operation.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/ORCHESTRATION-PLAN.md
@.planning/phases/O2-voss-team-spec-roster/O2-CONTEXT.md
@.planning/phases/O2-voss-team-spec-roster/O2-RESEARCH.md
@.planning/phases/O2-voss-team-spec-roster/O2-01-SUMMARY.md
@.planning/phases/O2-voss-team-spec-roster/O2-02-SUMMARY.md
@voss/harness/permissions.py
@voss/harness/skill/scope.py
@voss/harness/tools.py
@voss/harness/team.py
@voss/harness/subagents.py
@tests/harness/test_allow_net.py

<interfaces>
<!-- Patterns to MIRROR (skill/scope.py is the template). -->
<!-- Patterns to EXTEND (permissions.py is the integration point). -->

Template — `voss/harness/skill/scope.py:74-95`:
```python
def _min_mode(m1: Mode, m2: Mode) -> Mode:
    order = {"plan": 0, "edit": 1, "auto": 2}
    v1 = order.get(m1, 0)
    v2 = order.get(m2, 0)
    return m1 if v1 <= v2 else m2

def scoped_gate(spec: ScopeSpec, base_gate: PermissionGate) -> PermissionGate:
    effective_mode = _min_mode(base_gate.mode, scope_to_mode(spec.tools))
    return PermissionGate(
        mode=effective_mode,
        auto_yes=True,
        store=None,
        project_policy=base_gate.project_policy,
    )
```

Current `PermissionGate` — `voss/harness/permissions.py:146-153`:
```python
@dataclass
class PermissionGate:
    mode: Mode = "edit"
    store: PermissionStore | None = None
    auto_yes: bool = False
    prompt_fn: Optional[Callable] = None
    edit_scope: Optional["EditScope"] = None
    scope_prompt_fn: Optional[Callable] = None
    project_policy: Optional[PermissionsConfig] = None
```

Current net gate (the override target) — `voss/harness/permissions.py:226-233`:
```python
if is_network:
    from voss_runtime._config import get_config
    if not get_config().allow_net:
        return False, (
            "net disabled: set tools.allow_net = true in "
            "harness.toml or pass --allow-net"
        )
```

`ToolEntry` shape — `voss/harness/tools.py:24-38`:
```python
@dataclass(frozen=True)
class ToolEntry:
    descriptor: ToolDescriptor
    is_mutating: bool
    is_network: bool = False
```

`web_fetch`/`web_search` are the canonical `is_network=True` entries — `tools.py:577-580`. Filtering on tool name = `web_fetch`, `web_search` is the operative subset rule for net.

Network-aware specs come from O2-02 — `voss/harness/subagents.py::SubagentSpec.tools: Optional[FrozenSet[str]]` and `.net: bool`. The convention (from O2-02 Task 2): `"net" in spec.tools` ⟺ `spec.net is True`. We trust both fields (they're constructed together).
</interfaces>
</context>

<open-question id="OQ-03-A" requirement="OTEAM-03">
**Resolve before Task 1.** Tool-name surface for `spec.tools` (Research Open Q #4 + new):

`spec.tools` is `FrozenSet[str]`. What strings count?

- (a) **Strawman shorthand** — `["fs","test","net"]`: `"fs"` = all fs_*, `"test"` = no concrete `test_*` tool exists today (closest: `shell_run` with a `pytest` invocation). `"net"` = `web_fetch` + `web_search`. Needs a mapping table.
- (b) **Exact tool names** — `["fs_read","fs_write","fs_glob","fs_grep","shell_run","web_fetch","web_search"]`. Verbose, but precise — filters by the exact key of `make_toolset()`.
- (c) **Hybrid** — mapping for the shorthand, exact names also accepted.

**Recommendation:** (c). Define `TOOL_GROUP_ALIASES = {"fs": {"fs_read","fs_write","fs_edit","fs_glob","fs_grep"}, "test": {"shell_run"}, "shell": SHELL set from permissions.py:46, "net": {"web_fetch","web_search"}, "git": {"git_status","git_diff"}}`. `filter_toolset_for_role` expands aliases first, then filters.

If unresolved at exec time: surface as `checkpoint:decision`. Implementation impact is one helper function.
</open-question>

<open-question id="OQ-03-B" requirement="OTEAM-07">
**Resolve before Task 2.** Where does `gate_for_role` set `allow_net`?

The two competing models from Research §3 R3:

- (a) **Per-gate override field** (Research recommendation A8): add `PermissionGate.allow_net: bool | None`. Gate's `_check_impl` honours the override when set; falls back to process config when `None`.
- (b) **Subagent-scoped config fork**: construct a child `_Config` with `allow_net=True` for the AI subagent's run; restore on exit. Cross-cuts `voss_runtime._config`.

**Recommendation:** (a). Stays inside the gate boundary; no global mutation; existing `tests/harness/test_allow_net.py` continues to work because the field defaults to `None` (existing behaviour). The "process-wide allow_net" toggle remains the default; per-gate overrides are additive.

If unresolved at exec time: surface as `checkpoint:decision`. Implementation impact is bigger if (b) is chosen — touches `voss_runtime`.
</open-question>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add per-gate allow_net override to PermissionGate</name>
  <files>voss/harness/permissions.py, tests/harness/test_allow_net.py</files>
  <behavior>
    - `PermissionGate(allow_net=None)` (default) behaves exactly as today — defers to `voss_runtime._config.get_config().allow_net`.
    - `PermissionGate(allow_net=True)` grants net regardless of process config (subject to project-policy deny, which still wins per `permissions.py:0-26` docstring).
    - `PermissionGate(allow_net=False)` denies net regardless of process config — this is the AI-vs-engineer differentiation we need.
    - The check ordering in `_check_impl` preserves: project-policy deny → net gate → mode tier → write-scope → prompt/auto. (Per the docstring at `permissions.py:213-230`.)
    - All existing tests in `tests/harness/test_allow_net.py` continue to pass — the override is fully additive.
  </behavior>
  <action>
    1. **Edit `voss/harness/permissions.py`:**

       a. Add field to `PermissionGate` (line 146-153):
          ```python
          @dataclass
          class PermissionGate:
              mode: Mode = "edit"
              store: PermissionStore | None = None
              auto_yes: bool = False
              prompt_fn: Optional[Callable] = None
              edit_scope: Optional["EditScope"] = None
              scope_prompt_fn: Optional[Callable] = None
              project_policy: Optional[PermissionsConfig] = None
              allow_net: Optional[bool] = None  # O2-03: per-gate override; None = defer to process config
          ```

       b. Modify `_check_impl` net branch (currently `permissions.py:226-233`):
          ```python
          if is_network:
              if self.allow_net is True:
                  # per-gate override: net allowed regardless of process config
                  pass  # falls through to mode-tier check
              elif self.allow_net is False:
                  return False, (
                      "net disabled for this role (per-gate override)"
                  )
              else:
                  # None: existing behaviour — defer to process config
                  from voss_runtime._config import get_config
                  if not get_config().allow_net:
                      return False, (
                          "net disabled: set tools.allow_net = true in "
                          "harness.toml or pass --allow-net"
                      )
          ```
          NOTE: Project-policy deny (at `_check_impl` lines 219-224) ALREADY runs before the net branch — preserve that ordering. A project-policy deny still wins over `allow_net=True`. Update the docstring at `permissions.py:213-230` to record the new override semantics.

    2. **Edit `tests/harness/test_allow_net.py`** (do NOT delete existing tests):
       - Read existing tests first; preserve all of them (they cover the `allow_net=None` default-deferred path).
       - Add new tests at the end of the file:
         - `test_per_gate_allow_net_true_overrides_process_false` — process config `allow_net=False`, gate constructed with `allow_net=True`, `gate.check("web_fetch", ..., is_network=True)` returns `(True, ...)`.
         - `test_per_gate_allow_net_false_overrides_process_true` — process config `allow_net=True`, gate constructed with `allow_net=False`, `gate.check("web_fetch", ..., is_network=True)` returns `(False, "net disabled for this role (per-gate override)")`.
         - `test_per_gate_allow_net_none_defers_to_process` — gate constructed with `allow_net=None`; behaviour matches process config (both True paths and False paths).
         - `test_project_policy_deny_wins_over_per_gate_allow_net_true` — gate `allow_net=True` + project policy denies `web_fetch` → deny wins. (Mirrors the docstring rule.)
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -nE 'allow_net: Optional\[bool\] = None' voss/harness/permissions.py</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/test_allow_net.py -v</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "
from voss.harness.permissions import PermissionGate
g = PermissionGate(allow_net=True)
assert g.allow_net is True
g2 = PermissionGate()
assert g2.allow_net is None
print('field OK')"</automated>
  </verify>
  <done>
    - `PermissionGate.allow_net` field exists with `Optional[bool] = None` default.
    - `_check_impl` honours the override per the truth table in the action.
    - All existing `tests/harness/test_allow_net.py` tests pass (regression gate).
    - 4 new tests added, all pass.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement gate_for_role + filter_toolset_for_role</name>
  <files>voss/harness/team.py, tests/harness/test_team_gate_compile.py, tests/harness/test_team_tool_filter.py</files>
  <behavior>
    - `gate_for_role(spec: SubagentSpec, base_gate: PermissionGate) -> PermissionGate`:
      - Imports and uses `_min_mode` from `voss/harness/skill/scope.py` (no re-implementation).
      - `effective_mode = _min_mode(base_gate.mode, spec.mode or base_gate.mode)`. If `spec.mode is None`, the role inherits the base gate's mode (no cap).
      - `allow_net = True if spec.net else False`. Both branches are explicit — non-net roles get `allow_net=False`, NOT `None`. This is what makes "AI role gets net; engineer doesn't" structural even when the process has `--allow-net` set.
      - `auto_yes=True` always (subagents must not prompt — Research §1.5).
      - `store=None` (no always-allow persistence for subagent sessions — mirrors `skill/scope.py:scoped_gate`).
      - `project_policy=base_gate.project_policy` (preserved — deny ALWAYS wins).
      - `edit_scope=None` (subagent role scopes are NOT EditScope-shaped; per-role write paths are TBD by O5; for O2 the gate's structural mode-cap is sufficient. Document this in docstring.)
    - `filter_toolset_for_role(spec: SubagentSpec, base_toolset: dict[str, ToolEntry]) -> dict[str, ToolEntry]`:
      - If `spec.tools is None`: return `dict(base_toolset)` (copy, no filter).
      - Else: expand aliases (per OQ-03-A resolution: `fs`, `test`, `shell`, `net`, `git`); filter `base_toolset` to entries whose key is in the expanded set.
      - If `"net"` not in expanded set: explicitly DROP `web_fetch` and `web_search` from the result.
      - Returns a new dict; does NOT mutate `base_toolset`.
    - Helper `TOOL_GROUP_ALIASES: Mapping[str, frozenset[str]]` lives in `voss/harness/team.py` as a module-level constant.
  </behavior>
  <action>
    1. **Edit `voss/harness/team.py`:**

       a. Add imports: `from .permissions import PermissionGate, Mode`; `from .skill.scope import _min_mode`; `from .tools import ToolEntry`. The first two are already-public; `_min_mode` is module-private but reused here — add a `# Public-for-team-compile reuse; see voss/harness/skill/scope.py:74` comment if linter complains.

       b. Add `TOOL_GROUP_ALIASES` constant per OQ-03-A resolution:
          ```python
          TOOL_GROUP_ALIASES: dict[str, frozenset[str]] = {
              "fs": frozenset({"fs_read", "fs_write", "fs_edit", "fs_glob", "fs_grep"}),
              "test": frozenset({"shell_run"}),
              "shell": frozenset({"shell_run", "shell_run_background", "shell_monitor", "shell_signal"}),
              "net": frozenset({"web_fetch", "web_search"}),
              "git": frozenset({"git_status", "git_diff"}),
          }
          ```
          (Mirror the canonical sets at `voss/harness/permissions.py:44-46`: READ_ONLY, WRITE, SHELL — but the team aliases are a separate convention because they're declared by `.voss` authors, not by mode-tier.)

       c. Implement `gate_for_role`:
          ```python
          def gate_for_role(spec: SubagentSpec, base_gate: PermissionGate) -> PermissionGate:
              """Compile a per-role PermissionGate from a SubagentSpec.

              Cap-not-expand: spec.mode caps base_gate.mode; never widens.
              Cage: AI role's spec.net=True grants allow_net=True; non-net specs
              get allow_net=False explicitly (NOT None — must override the
              process-level toggle to keep specialist roles structurally
              netless even when --allow-net is set).
              """
              if spec.mode is None:
                  effective_mode = base_gate.mode
              else:
                  effective_mode = _min_mode(base_gate.mode, spec.mode)
              return PermissionGate(
                  mode=effective_mode,
                  store=None,
                  auto_yes=True,
                  prompt_fn=None,
                  edit_scope=None,
                  scope_prompt_fn=None,
                  project_policy=base_gate.project_policy,
                  allow_net=True if spec.net else False,
              )
          ```

       d. Implement `filter_toolset_for_role`:
          ```python
          def filter_toolset_for_role(
              spec: SubagentSpec,
              base_toolset: Mapping[str, ToolEntry],
          ) -> dict[str, ToolEntry]:
              """Return a subset of base_toolset based on spec.tools.

              If spec.tools is None: full copy (no filter).
              Else: expand TOOL_GROUP_ALIASES, intersect with base_toolset.
              Network tools (`web_fetch`, `web_search`) are included only if
              `"net"` is in spec.tools — even when process allow_net is True.
              """
              if spec.tools is None:
                  return dict(base_toolset)
              expanded: set[str] = set()
              for entry in spec.tools:
                  if entry in TOOL_GROUP_ALIASES:
                      expanded |= TOOL_GROUP_ALIASES[entry]
                  else:
                      expanded.add(entry)  # exact tool name (hybrid OQ-03-A)
              return {name: te for name, te in base_toolset.items() if name in expanded}
          ```

    2. **Create `tests/harness/test_team_gate_compile.py`** — OTEAM-07 acceptance:

       a. `test_gate_for_role_caps_mode` — `spec(mode="plan")` + `base_gate(mode="edit")` → derived gate mode is `"plan"`.

       b. `test_gate_for_role_never_expands_mode` — `spec(mode="auto")` + `base_gate(mode="edit")` → derived gate mode is `"edit"` (cap-not-expand).

       c. `test_gate_for_role_inherits_base_mode_when_spec_mode_none` — `spec(mode=None)` + `base_gate(mode="edit")` → derived gate mode is `"edit"`.

       d. `test_gate_for_role_preserves_project_policy` — base has `project_policy=<some PermissionsConfig>`; derived gate's `project_policy` is the same object.

       e. `test_gate_for_role_subagent_never_prompts` — derived gate has `auto_yes=True`.

       f. `test_gate_for_role_does_not_inherit_store_or_edit_scope` — derived gate has `store=None` and `edit_scope=None` (subagent never persists always-allow; subagent scope is enforced by O5 routing, not by EditScope here).

       g. `test_gate_for_role_uses_min_mode_from_skill_scope` — Verify the reuse: monkey-patch (or just assert via call) that the function being called matches `voss.harness.skill.scope._min_mode`. Concretely: `import voss.harness.team as t; from voss.harness.skill.scope import _min_mode; assert t._min_mode is _min_mode` (asserts the import shares the symbol — no re-implementation).

       h. `test_min_mode_truth_table` — for each (m1, m2) in `[("plan","plan"), ("plan","edit"), ("plan","auto"), ("edit","plan"), ("edit","edit"), ("edit","auto"), ("auto","plan"), ("auto","edit"), ("auto","auto")]`: assert the returned mode is the more restrictive of the two. (Property table; nine cases.)

    3. **Create `tests/harness/test_team_tool_filter.py`** — toolset filter:

       a. `test_filter_none_returns_full_copy` — `filter_toolset_for_role(spec(tools=None), base)` returns a dict with the same keys as `base` and is not the same object.

       b. `test_filter_fs_alias` — `spec(tools=frozenset({"fs"}))` → result contains `fs_read`, `fs_write`, `fs_edit`, `fs_glob`, `fs_grep`; does NOT contain `shell_run`, `web_fetch`, `web_search`.

       c. `test_filter_net_alias` — `spec(tools=frozenset({"net"}))` → result contains `web_fetch`, `web_search`; does NOT contain `fs_read`.

       d. `test_filter_excludes_net_when_net_absent` — `spec(tools=frozenset({"fs","test"}))` → result does NOT contain `web_fetch` even if `base_toolset` includes it.

       e. `test_filter_exact_name_hybrid` — `spec(tools=frozenset({"fs_read"}))` → result contains only `fs_read` (the hybrid acceptance of exact names per OQ-03-A).

       f. `test_filter_unknown_alias_silently_drops` — `spec(tools=frozenset({"nonexistent_alias"}))` → result is empty dict (alias not in `TOOL_GROUP_ALIASES`, not in any base_toolset key). Document this behaviour — silent drop, not error, because OQ-03-A allows exact names; an unknown name is harmless filtering.

       g. `test_filter_does_not_mutate_base` — call filter; assert original `base_toolset` still has all its keys.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "
from voss.harness.team import gate_for_role, filter_toolset_for_role, TOOL_GROUP_ALIASES, _min_mode
from voss.harness.skill.scope import _min_mode as min_mode_from_scope
assert _min_mode is min_mode_from_scope, 'must REUSE not re-implement'
print('reuse OK')"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -nE 'from .skill.scope import _min_mode' voss/harness/team.py</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -cE 'def gate_for_role|def filter_toolset_for_role' voss/harness/team.py</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/test_team_gate_compile.py tests/harness/test_team_tool_filter.py -v</automated>
  </verify>
  <done>
    - `gate_for_role` + `filter_toolset_for_role` + `TOOL_GROUP_ALIASES` live in `voss/harness/team.py`.
    - `_min_mode` is REUSED (imported from `skill/scope.py`) — verified by identity check.
    - ≥ 8 tests in `test_team_gate_compile.py`, ≥ 7 tests in `test_team_tool_filter.py`, all pass.
    - OQ-03-A resolution (alias table) and OQ-03-B resolution (per-gate override) recorded in SUMMARY.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: End-to-end role-net cage gate — AI gets net, engineer doesn't</name>
  <files>tests/harness/test_team_per_role_net.py</files>
  <behavior>
    - With process `allow_net=True`:
      - AI role's compiled `gate_for_role` lets `web_fetch` through.
      - Backend role's compiled gate DENIES `web_fetch` with the per-gate-override message.
    - With process `allow_net=False`:
      - AI role's compiled gate STILL lets `web_fetch` through (per-gate override wins).
      - Backend role's compiled gate denies `web_fetch` (consistent).
    - This is the **cage proof** for OTEAM-03 net portion: declaration → enforcement, regardless of process config.
    - Uses the strawman fixture from O2-01 + `compile_team` from O2-02 + `gate_for_role` from O2-03 Task 2 — full pipeline integration.
  </behavior>
  <action>
    1. **Create `tests/harness/test_team_per_role_net.py`** with the following tests. Use the existing `voss_runtime._config` set/restore pattern from `tests/harness/test_allow_net.py` (read it first to copy the convention).

       Test outline:
       ```python
       import pytest
       from pathlib import Path
       from voss import parse
       from voss.harness.team import compile_team, gate_for_role, filter_toolset_for_role
       from voss.harness.permissions import PermissionGate
       from voss.harness.tools import make_toolset
       from voss.ast_nodes import TeamDecl

       STRAWMAN = Path("tests/parser/examples/team_strawman.voss")

       @pytest.fixture
       def strawman_config_and_registry():
           src = STRAWMAN.read_text()
           prog = parse(src)
           td = next(d for d in prog.body if isinstance(d, TeamDecl))
           return compile_team(td)

       def _set_process_allow_net(value: bool, monkeypatch):
           from voss_runtime import _config
           cfg = _config.get_config()
           monkeypatch.setattr(cfg, "allow_net", value)
       ```

       Tests:

       a. `test_ai_role_gate_grants_net_when_process_allows` — process `allow_net=True`; compile AI role's gate from a permissive base; `gate.check("web_fetch", {}, is_mutating=False, is_network=True)` returns `(True, ...)`.

       b. `test_ai_role_gate_grants_net_even_when_process_disallows` — process `allow_net=False`; same flow; STILL returns `(True, ...)` because the per-gate override wins. This is the proof that the AI role's net capability is declared in `.voss`, not inherited from process flags.

       c. `test_backend_role_gate_denies_net_even_when_process_allows` — process `allow_net=True`; backend role's gate; `gate.check("web_fetch", {}, is_network=True)` returns `(False, "net disabled for this role (per-gate override)")`. This is the proof that engineers cannot escalate to net by piggy-backing on `--allow-net`.

       d. `test_engineer_roles_all_lack_net` — for each of `backend`, `frontend`, `ui`: compile their gates; assert each denies `web_fetch`.

       e. `test_em_gate_inherits_base` — EM is not a specialist; its `mode` is the strawman's `"auto"` capped by base. EM's `spec.net` is False (no `net` in its tools list in the strawman). Assert EM gate also denies `web_fetch` (the EM does not have net — only the AI role does, per ORCHESTRATION-PLAN.md §5).

       f. `test_filtered_toolset_for_ai_role_includes_web_fetch` — `make_toolset(cwd=..., renderer=...)` produces a full toolset; `filter_toolset_for_role(spec_ai, base)` returns a dict including `web_fetch`.

       g. `test_filtered_toolset_for_backend_role_excludes_web_fetch` — same, but for backend; `web_fetch` is not in the result.

       h. `test_project_policy_deny_overrides_ai_role_net` — Construct a base gate with a `project_policy` that denies `web_fetch`; AI role's compiled gate inherits the policy; `gate.check("web_fetch", ...)` returns `(False, "denied by .voss/permissions.yml")`. This is the cage's "project policy ALWAYS wins" invariant from `voss/harness/permissions.py:0-26` docstring — preserved through team compilation.

    2. **No production code changes in this task.** This is an integration-test-only task that proves the cage holds end-to-end. If a test fails, the bug is in Task 1 or Task 2; fix there.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/test_team_per_role_net.py -v</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -cE 'def test_' tests/harness/test_team_per_role_net.py | awk '$1 < 7 {exit 1} {print "per-role-net tests:", $1}'</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/test_allow_net.py tests/harness/test_team_gate_compile.py tests/harness/test_team_tool_filter.py tests/harness/test_team_per_role_net.py tests/harness/test_subagent_spec_extensions.py tests/voss/ tests/parser/test_team_grammar.py -x -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/ -x -q -k "not slow"</automated>
  </verify>
  <done>
    - `tests/harness/test_team_per_role_net.py` has ≥ 7 tests, all pass.
    - The full O2 test suite (parser-grammar + spec-extensions + compile + scope-invariant + immutability + gate-compile + tool-filter + per-role-net) is green.
    - The full `tests/harness/` suite passes (regression gate for the `PermissionGate` change).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Process config (`voss_runtime._config.allow_net`) → `PermissionGate._check_impl` | Per-gate override sits between these; misimplementation would allow process flags to bypass declared cage. |
| `SubagentSpec.net` (declared in `.voss`) → `PermissionGate.allow_net` | `gate_for_role` is the bridge. Bug here = net leaks to engineer roles or AI loses net. |
| `SubagentSpec.tools` (declared) → `filter_toolset_for_role` output | Filter is the structural enforcement; if filter passes `web_fetch` through for a non-net role, the gate is the second line of defense. **Both** layers must agree to defense-in-depth. |

## STRIDE Threat Register (O2-03 scope)

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O2-03-01 | Elevation of Privilege | Engineer role's compiled gate accidentally has `allow_net=True` or `allow_net=None` (defers to `--allow-net`) | mitigate | `gate_for_role` explicitly sets `allow_net=True if spec.net else False` — never `None` for compiled roles. `test_backend_role_gate_denies_net_even_when_process_allows` is the regression gate. |
| T-O2-03-02 | Elevation of Privilege | `filter_toolset_for_role` includes `web_fetch` in a non-net role's toolset (single-layer cage bypass) | mitigate | Filter excludes `web_fetch`/`web_search` when `"net"` not in alias-expanded tools. `test_filter_excludes_net_when_net_absent` is the regression gate. Defense-in-depth: even if filter slips, the gate denies (T-O2-03-01 covers). |
| T-O2-03-03 | Tampering | Adversarial EM constructs its own `PermissionGate(allow_net=True)` to bypass the role cage | mitigate (deferred to O5) | `PermissionGate` is a public class; the EM with code-exec access can construct anything. **Mitigation lives in O5's tool surface design:** the EM does NOT get a tool that takes a `PermissionGate` argument; it gets `subagent_run(agent_id, task)` which closes over the role-compiled gate. Track as **deferred-to-O5**; surface in O2-03 SUMMARY. |
| T-O2-03-04 | Tampering | `_min_mode` is re-implemented in `voss/harness/team.py` instead of imported, drifting from `skill/scope.py` | mitigate | `test_gate_for_role_uses_min_mode_from_skill_scope` asserts identity (`t._min_mode is scope._min_mode`). Drift is caught at CI. |
| T-O2-03-05 | Information Disclosure | The per-gate-override deny message differs from the process-config deny message, leaking info about declaration vs config | accept | The two messages are intentionally distinct so audit can attribute which gate fired. The leakage is "the EM author declared this role as netless," which is public information in `.voss`. |
| T-O2-03-06 | Repudiation | A net deny on an AI role's gate (due to project-policy override) should be traceable to the policy, not appear as "AI lost its net" | mitigate | Project-policy deny message at `permissions.py:222-224` is `"denied by .voss/permissions.yml"` — distinct from the per-gate-override message. Tests `test_project_policy_deny_overrides_ai_role_net` confirms ordering and message. |
| T-O2-03-07 | DoS via alias explosion | `TOOL_GROUP_ALIASES` expansion produces exponential sets for pathological inputs | accept | Static dict, finite size (5 aliases, ~15 names total). No user-defined aliases in O2. Bounded by `make_toolset()` output cardinality. |

(Package legitimacy gate: no new package installs. No `[ASSUMED]`/`[SUS]` checkpoints required.)

**Deferred-to-O5 items recorded above:** T-O2-03-03 (EM's ability to construct arbitrary `PermissionGate`s). The mitigation is "the EM's tool surface does NOT include `PermissionGate(...)` as a callable; the only construction path is through `gate_for_role` which is owned by the harness orchestrator, not the EM's session." This is O5's responsibility to design + enforce; flag it in `O2-03-SUMMARY.md` for the O5 SPEC author.
</threat_model>

<verification>
1. **PermissionGate is back-compat with `allow_net=None`** — full `tests/harness/test_allow_net.py` suite green.
2. **`gate_for_role` reuses `_min_mode`** — identity check passes (not a re-implementation).
3. **Cap-not-expand mode** — `spec.mode="auto"` + `base.mode="edit"` → `"edit"`. 9-case truth table passes.
4. **AI role gets net structurally** — process `allow_net=False` + AI role gate → `web_fetch` allowed.
5. **Engineer roles lack net structurally** — process `allow_net=True` + backend gate → `web_fetch` denied with per-gate-override message.
6. **Project policy still wins** — even AI role's gate is denied if `.voss/permissions.yml` denies `web_fetch`.
7. **Tool filter is consistent with gate** — `filter_toolset_for_role` for a non-net role doesn't include `web_fetch`; defense-in-depth confirmed.
8. **Full O2 test surface green** — parser-grammar + spec-extensions + compile + scope-invariant + immutability + gate-compile + tool-filter + per-role-net.
9. **No regression elsewhere in `tests/harness/`** — broader test suite green.
</verification>

<success_criteria>
- [ ] `voss/harness/permissions.py::PermissionGate` has `allow_net: Optional[bool] = None`.
- [ ] `_check_impl` honours `allow_net` override with the documented truth table; project-policy deny still wins.
- [ ] `voss/harness/team.py` has `gate_for_role`, `filter_toolset_for_role`, `TOOL_GROUP_ALIASES`.
- [ ] `_min_mode` is IMPORTED from `voss/harness/skill/scope.py` (verified by `is`-identity test).
- [ ] Open questions OQ-03-A and OQ-03-B resolved + recorded in `O2-03-SUMMARY.md`.
- [ ] `tests/harness/test_allow_net.py` has ≥ 4 new tests (additive); all existing tests still pass.
- [ ] `tests/harness/test_team_gate_compile.py` has ≥ 8 tests, all pass.
- [ ] `tests/harness/test_team_tool_filter.py` has ≥ 7 tests, all pass.
- [ ] `tests/harness/test_team_per_role_net.py` has ≥ 7 tests, all pass.
- [ ] `tests/harness/` full suite passes (no regression on broader gate tests).
- [ ] No edits to `voss/harness/subagents.py`, `voss/harness/cli.py`, `voss/harness/multiagent.py` — those are O5 wiring surfaces, not O2.
- [ ] **Deferred-to-O5 note in SUMMARY:** the EM's tool surface MUST NOT include a `PermissionGate` constructor as callable (T-O2-03-03 residual).
</success_criteria>

<output>
Create `.planning/phases/O2-voss-team-spec-roster/O2-03-SUMMARY.md` when done, recording:
- Each task's outcome with `<verify>` command results.
- **OQ-03-A resolution** — `TOOL_GROUP_ALIASES` table as committed (with rationale for the alias names chosen).
- **OQ-03-B resolution** — per-gate `allow_net` override (confirmed model A from Research §3 R3).
- The signatures of `gate_for_role` and `filter_toolset_for_role`.
- The list of `is_network=True` tools that the filter excludes for non-net roles (today: `web_fetch`, `web_search`).
- The **deferred-to-O5 cage item** (T-O2-03-03): the EM must not have a `PermissionGate` constructor in its tool surface. Phrase this as an explicit hand-off note to the O5 SPEC author.
- Total O2 phase test count (sum of all `tests/voss/` + new `tests/harness/test_team_*` + `test_subagent_spec_extensions` + parser team grammar tests).
</output>
