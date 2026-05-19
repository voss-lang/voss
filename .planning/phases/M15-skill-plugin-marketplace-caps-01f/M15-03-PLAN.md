---
phase: M15-skill-plugin-marketplace-caps-01f
plan: 03
type: execute
wave: 1
depends_on: ["M15-01"]
files_modified:
  - voss/harness/skill/__init__.py
  - voss/harness/skill/scope.py
  - tests/harness/skill/test_scope.py
autonomous: true
requirements: [SKILL-04]
user_setup: []

must_haves:
  truths:
    - "A read-only-scoped skill's fs_write / shell_run is denied by the gate"
    - "A read-only-scoped skill's fs_read is permitted"
    - "A skill with no declared [scopes] runs default-deny (plan mode, read-only, no net)"
    - "Declared scopes map onto the EXISTING permissions.py mode (plan/edit/auto) + is_network axis — no new enforcement engine"
  artifacts:
    - path: "voss/harness/skill/scope.py"
      provides: "ScopeSpec + scope_to_mode + scoped_gate (declared scopes → existing PermissionGate)"
      exports: ["ScopeSpec", "scope_to_mode", "scoped_gate", "scope_spec_from_manifest"]
      min_lines: 50
    - path: "voss/harness/skill/__init__.py"
      provides: "voss.harness.skill package marker"
      min_lines: 1
  key_links:
    - from: "voss/harness/skill/scope.py"
      to: "voss.harness.permissions.PermissionGate"
      via: "scoped_gate returns a PermissionGate with mode capped to declared scope (no new axis)"
      pattern: "PermissionGate\\("
    - from: "voss/harness/skill/scope.py"
      to: "voss.harness.permissions.mode_allows"
      via: "scope_to_mode maps read-only/mutating/all → plan/edit/auto (the existing tier vocabulary)"
      pattern: "plan|edit|auto"
---

<objective>
Build the permission-scope spine: `voss/harness/skill/scope.py` — a `ScopeSpec` parsed from the manifest's `[scopes]` table and a `scoped_gate()` that returns an EXISTING `PermissionGate` capped to the declared scope. Declared scopes bind onto the existing `permissions.py` mode (`plan`/`edit`/`auto`) + `is_network` axis — a binding, NOT a second enforcement engine (SPEC constraint; CONTEXT default-deny; RESEARCH anti-pattern "extending PermissionGate with new enforcement logic"). This is the other half of the W1 hard prerequisite — scope enforcement must exist and be provable before any third-party `.voss` code runs.

Purpose: SKILL-04 — an action outside a skill's declared tool/fs/net scopes is blocked by the existing gate; an in-scope action of the same kind is permitted. Default (no `[scopes]`) = `plan` (read-only, no writes, no shell, no net) per CONTEXT default-deny.

Output: `voss/harness/skill/` package + `scope.py`; the SKILL-04 RED tests in `tests/harness/skill/test_scope.py` turn GREEN.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-SPEC.md
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md
@.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-PATTERNS.md

<interfaces>
<!-- The public surface this plan creates. The W0 RED test_scope.py asserts exactly these. -->

voss/harness/skill/scope.py public API:
```python
@dataclass(frozen=True)
class ScopeSpec:
    tools: str = "read-only"   # "read-only" | "mutating" | "all"
    fs: str = "cwd"            # "cwd" | "none"
    net: bool = False

def scope_spec_from_manifest(raw: dict) -> ScopeSpec
    # reads raw.get("scopes",{}) defensively; unknown/missing -> defaults (default-deny)

def scope_to_mode(tools_value: str) -> Mode
    # "read-only"->"plan", "mutating"->"edit", "all"->"auto", anything else->"plan"

def scoped_gate(spec: ScopeSpec, base_gate: PermissionGate) -> PermissionGate
    # returns a NEW PermissionGate(mode=min(base_gate.mode, scope_to_mode(spec.tools)),
    #   auto_yes=True, store=None)  — third-party skills never prompt, never "remember"
    # net is handled by the existing is_network axis: scoped runtime must run with
    # allow_net=spec.net so PermissionGate._check_impl's is_network branch denies net
    # when spec.net is False (Pitfall 2: never inherit an interactive/store-backed gate)
```

Reuse (existing — bind to these, do NOT add a new check axis):
From voss/harness/permissions.py:
```python
Mode = Literal["plan", "edit", "auto"]
READ_ONLY = {"fs_read","fs_glob","fs_grep","git_status","git_diff","voss_check"}
WRITE = {"fs_write","fs_edit"}
SHELL = {"shell_run","shell_run_background","shell_monitor","shell_signal"}
def mode_allows(mode, tool_name, is_mutating) -> tuple[bool,str]
  # plan: denies all mutating; edit: denies shell_run*; auto: all
@dataclass class PermissionGate:
  mode: Mode = "edit"; auto_yes: bool = False
  def check(tool_name, args, *, is_mutating=False, is_network=False) -> tuple[bool,str]
```
The `_check_impl` order (RESEARCH): project-policy → net gate (is_network) → mode-tier → scope → prompt. scoped_gate must NOT touch this order — it only constructs a PermissionGate with a capped mode + auto_yes=True + store=None.
</interfaces>

<analog>
PermissionGate construction + mode semantics: voss/harness/permissions.py:42-65 (`Mode`, `mode_allows`), 145-197 (`PermissionGate`, `check`, `_check_impl` order-of-operations).
Gate-mode test pattern: tests/skills/test_skills_smoke.py lines ~43-81 (run skill under `PermissionGate(mode="plan")` → assert zero mutation; under `PermissionGate(auto_yes=True)` → assert execution).
Manifest defensive `.get()` parse: voss/harness/plugins.py:86-134 (`_read_manifest` — `str(raw.get("scopes",{}).get("tools","read-only"))` shape, never raise).
M15-RESEARCH.md §Pattern 3 "Scope Grammar → Gate Binding" (SCOPE_TO_MODE table) + Anti-Pattern "Extending PermissionGate with new enforcement logic".
</analog>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: ScopeSpec + scope_to_mode + manifest parse (default-deny)</name>
  <read_first>
    - voss/harness/permissions.py (lines 42-65 Mode/READ_ONLY/WRITE/SHELL/mode_allows)
    - voss/harness/plugins.py (lines 86-134 `_read_manifest` defensive `.get()` shape)
    - tests/harness/skill/test_scope.py (the RED tests being satisfied — file context)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md (§Pattern 3 Scope Grammar)
  </read_first>
  <behavior>
    - scope_spec_from_manifest({}) → ScopeSpec(tools="read-only", fs="cwd", net=False)  [default-deny]
    - scope_spec_from_manifest({"scopes":{"tools":"mutating","net":True}}) → tools="mutating", net=True
    - scope_to_mode: "read-only"→"plan", "mutating"→"edit", "all"→"auto", "garbage"/missing→"plan"
    - scope_spec_from_manifest never raises on malformed input (non-dict scopes, wrong types) → defaults
  </behavior>
  <action>
    Create `voss/harness/skill/__init__.py` (package marker; one-line docstring acceptable). Create `voss/harness/skill/scope.py`. Define frozen `ScopeSpec(tools="read-only", fs="cwd", net=False)`. Implement `scope_to_mode(tools_value) -> Mode` with the exact `read-only→plan / mutating→edit / all→auto` mapping (RESEARCH §Pattern 3 SCOPE_TO_MODE); any unrecognized value falls back to `"plan"` (default-deny). Implement `scope_spec_from_manifest(raw: dict) -> ScopeSpec` using the defensive `raw.get("scopes",{})` shape from `_read_manifest` (coerce types, wrong-type → default; never raise). Import `Mode` from `voss.harness.permissions`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -c "from voss.harness.skill.scope import ScopeSpec, scope_to_mode, scope_spec_from_manifest as f; assert scope_to_mode('read-only')=='plan'; assert scope_to_mode('mutating')=='edit'; assert scope_to_mode('all')=='auto'; assert scope_to_mode('x')=='plan'; assert f({}).tools=='read-only' and f({}).net is False; assert f({'scopes':{'tools':'mutating','net':True}}).net is True; assert f({'scopes':'bogus'}).tools=='read-only'; print('SCOPE OK')"</automated>
  </verify>
  <acceptance_criteria>
    - The inline assertion prints `SCOPE OK` (default-deny + mapping + malformed-safe all hold)
    - `scope_to_mode` returns only `"plan"|"edit"|"auto"` (the existing tier vocabulary — no new tier names)
    - `scope_spec_from_manifest` never raises (test passes a non-dict `scopes`)
    - `grep -n "from voss.harness.permissions import" voss/harness/skill/scope.py` shows Mode is reused, not redefined
  </acceptance_criteria>
  <done>Manifest scopes parse to a default-deny ScopeSpec mapped onto the existing plan/edit/auto vocabulary.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: scoped_gate — cap an existing PermissionGate to declared scope</name>
  <read_first>
    - voss/harness/skill/scope.py (the module from Task 1 — file being modified)
    - voss/harness/permissions.py (lines 145-197 PermissionGate / check / _check_impl order; lines 49-65 mode_allows)
    - tests/harness/skill/test_scope.py (`test_out_of_scope_blocked`, `test_in_scope_allowed` — RED tests being turned green)
    - .planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-RESEARCH.md (§Pattern 3 scoped_gate + Pitfall 2 no interactive/store gate)
  </read_first>
  <behavior>
    - scoped_gate(ScopeSpec(tools="read-only"), base=PermissionGate(mode="auto")).check("fs_write",{...},is_mutating=True) → (False, "denied by mode plan")
    - same scoped gate .check("fs_read",{...}) → (True, ...)
    - scoped_gate(ScopeSpec(tools="mutating"), base).check("shell_run",{...}) → (False, "denied by mode edit")
    - effective mode = min(base_gate.mode, scope_to_mode(spec.tools)) — a tighter base is never widened by the scope
    - returned gate has auto_yes=True and store=None (never prompts, never "always remember" — Pitfall 2)
  </behavior>
  <action>
    Add `scoped_gate(spec: ScopeSpec, base_gate: PermissionGate) -> PermissionGate` to scope.py. Compute `effective = _min_mode(base_gate.mode, scope_to_mode(spec.tools))` where `_min_mode` orders `plan < edit < auto` and returns the tighter of the two (a skill can never escalate beyond its declared scope OR beyond the base gate). Return `PermissionGate(mode=effective, auto_yes=True, store=None)`. Do NOT add any new check method or axis to PermissionGate — enforcement is the existing `check`/`mode_allows` path (RESEARCH anti-pattern). Document in a module docstring: net confinement is delivered by running the skill subprocess with `allow_net=spec.net` so the existing `_check_impl` `is_network` branch denies net tools when `spec.net` is False (the actual subprocess net wiring lands in M15-05's adapter; scope.py only provides the ScopeSpec.net value and the docstring contract).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -m pytest tests/harness/skill/test_scope.py -x -q 2>&1 | tail -3 && python3 -c "from voss.harness.skill.scope import scoped_gate, ScopeSpec; from voss.harness.permissions import PermissionGate; g=scoped_gate(ScopeSpec(tools='read-only'), PermissionGate(mode='auto')); a,_=g.check('fs_write',{'path':'x','content':'y'},is_mutating=True); b,_=g.check('fs_read',{'path':'x'}); print('BLOCK',not a,'ALLOW',b,'AUTOYES',g.auto_yes,'STORE',g.store is None)"</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/skill/test_scope.py -x` — both SKILL-04 tests PASS (were RED in W0)
    - The inline check prints `BLOCK True ALLOW True AUTOYES True STORE True`
    - `grep -n "class PermissionGate\|def check\|def _check_impl" voss/harness/skill/scope.py` returns NOTHING (no new enforcement engine — scope.py only constructs/returns an existing PermissionGate)
    - `_min_mode` makes the result the tighter of base vs declared (test asserts a `plan` base + `all` scope still yields `plan`)
  </acceptance_criteria>
  <done>scoped_gate caps an existing PermissionGate by declared scope using only the existing mode axis; SKILL-04 RED suite is GREEN; no second enforcement engine introduced.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| third-party skill → tool gate | A third-party `.voss` skill's tool calls cross into the harness gate; the scoped gate is the confinement |
| manifest [scopes] → runtime authority | Declared scopes are attacker-influenced data; they may only ever REDUCE authority, never grant it |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M15-03-01 | Elevation of Privilege | Scope escalation via manifest | mitigate | `scoped_gate` uses `min(base, declared)` — a manifest can only narrow authority; never widens base_gate.mode; test asserts `plan` base + `all` scope ⇒ `plan` |
| T-M15-03-02 | Elevation of Privilege | Missing/garbage [scopes] grants broad access | mitigate | `scope_spec_from_manifest`/`scope_to_mode` default-deny to `plan` (read-only) on missing/unrecognized values (CONTEXT default-deny) |
| T-M15-03-03 | Elevation of Privilege | Parallel enforcement engine drift | mitigate | scope.py contains NO check/_check_impl logic (acceptance grep); binds to existing `permissions.py` only — single enforcement path, no drift surface |
| T-M15-03-04 | Tampering | Interactive/store-backed gate inheritance | mitigate | scoped_gate forces `auto_yes=True, store=None` (Pitfall 2) — third-party skill can never prompt-bypass or persist an "always allow" |
| T-M15-03-05 | Elevation of Privilege | Direct Python `open()`/`urllib` bypasses gate | accept | DOCUMENTED limitation (SPEC-accepted, OS sandbox deferred); module docstring + M15-06 README/`voss doctor` state it; gate confines harness tool calls only |
</threat_model>

<verification>
- `pytest tests/harness/skill/test_scope.py -x -q` — 2/2 SKILL-04 tests GREEN
- scoped_gate result is always the tighter of base vs declared mode; never escalates
- scope.py introduces no new check/_check_impl axis (grep returns nothing)
- Returned gate is non-interactive (auto_yes=True) and non-persistent (store=None)
- `pytest tests/harness/skill/ -q` shows only still-unimplemented (install/registry/lifecycle) tests RED — no regression; M15-02 trust tests unaffected (file-disjoint)
</verification>

<success_criteria>
SKILL-04 satisfied: out-of-scope tool/fs/net actions blocked by the existing gate, in-scope actions permitted, default-deny when undeclared; enforcement reuses permissions.py with zero new engine; the documented direct-Python-call limitation is recorded.
</success_criteria>

<output>
Create `.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-03-SUMMARY.md` when done
</output>
