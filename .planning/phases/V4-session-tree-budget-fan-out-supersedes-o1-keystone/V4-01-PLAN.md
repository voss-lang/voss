---
phase: V4-session-tree-budget-fan-out-supersedes-o1-keystone
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/session_tree.py
  - voss/harness/session.py
  - tests/harness/test_session_tree.py
autonomous: true
requirements: [VTREE-01, VTREE-08, VTREE-05, VTREE-06]
must_haves:
  truths:
    - "SessionTreeNode carries scope + role fields; populated when known at spawn, null otherwise"
    - "Pre-V4 node files (no scope/role keys) still hydrate, with scope=role=None"
    - "allocate_child can persist a known scope/role atomically with the node file"
    - "EXIT_REASONS accepts 'error' so exception-path finalize is well-formed"
    - "No field added/removed on SessionRecord, RunRecord, or BudgetScope (frozen)"
    - "tests/harness/test_session_redaction.py passes UNMODIFIED"
  artifacts:
    - path: "voss/harness/session_tree.py"
      provides: "SessionTreeNode.scope + SessionTreeNode.role nullable fields; allocate_child scope/role kwargs; _hydrate_node back-compat"
      contains: "scope: Optional[str] = None"
    - path: "voss/harness/session.py"
      provides: "'error' added to EXIT_REASONS frozenset (additive; no RunRecord field change)"
      contains: "\"error\""
    - path: "tests/harness/test_session_tree.py"
      provides: "Updated _NODE_JSON_KEYS + TestSchemaExtension class"
      contains: "TestSchemaExtension"
  key_links:
    - from: "voss/harness/session_tree.py::_hydrate_node"
      to: "SessionTreeNode(scope, role)"
      via: "setdefault(scope, None) / setdefault(role, None)"
      pattern: "setdefault\\(\"(scope|role)\""
    - from: "voss/harness/session_tree.py::SessionTreeManager.allocate_child"
      to: "_write_node_file"
      via: "scope/role passed into constructor inside the asyncio.Lock block"
      pattern: "scope=scope"
---

<objective>
Extend the session-tree substrate additively: add nullable `scope` + `role` fields to `SessionTreeNode`, wire `allocate_child` to persist them at spawn, keep `_hydrate_node` back-compatible with pre-V4 files, and add the `"error"` exit reason to `EXIT_REASONS` (the foundational schema decision the keystone finalize-wiring plan, V4-02, depends on).

Purpose: VTREE-08 is the schema foundation V4-02 (guard/finalize) and V4-03 (export/CLI) both build on — the export must carry scope/role, and the exception-path finalize needs a valid `exit_reason`. This plan also verifies the shipped VTREE-05/06 surface (cap-raise reject + rejected-raise audit) regresses green.

Output: extended `SessionTreeNode`, additive `EXIT_REASONS`, updated schema-lock test, new `TestSchemaExtension` class — all under the frozen-schema invariant.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-SPEC.md
@.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-RESEARCH.md
@.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-PATTERNS.md

<interfaces>
<!-- Current SessionTreeNode field order (session_tree.py lines 47-61). scope/role
     go between retry_notes and _budget; both need = None defaults (fields with
     defaults must follow fields without). -->

From voss/harness/session_tree.py:
- SessionTreeNode dataclass: id, root_id, parent_run_id, envelope, terminal_state,
  created_at, ended_at, rejected_raises=[], transitions=[], retry_notes=[],
  _budget(init=False), _finalized(init=False)
- _NODE_FIELDS = {f.name for f in dataclasses.fields(SessionTreeNode)}  # auto-rebuilds
- _hydrate_node(data): keeps _NODE_FIELDS keys, setdefault for rejected_raises/transitions/retry_notes
- SessionTreeManager.allocate_child(self, limit) -> SessionTreeNode  # builds child inside `async with self._lock`

From voss/harness/session.py:
- EXIT_REASONS = frozenset({"done","max-iter","budget","interrupt","batch-invariant","timeout","killed"})
  # additive frozenset — NOT a RunRecord field; adding "error" does NOT change RunRecord's 24-field count

From tests/harness/test_session_tree.py:
- _NODE_JSON_KEYS frozenset (lines 26-40): id, root_id, parent_run_id, envelope,
  terminal_state, created_at, ended_at, rejected_raises, transitions, retry_notes
- TestSchemaIsolation::test_node_keys_exact asserts set(root.to_dict().keys()) == _NODE_JSON_KEYS
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add scope/role to SessionTreeNode + back-compat hydrate + allocate_child kwargs</name>
  <read_first>
    - voss/harness/session_tree.py (the file being modified — full read; lines 47-94 dataclass+hydrate, 165-192 allocate_child)
    - .planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-PATTERNS.md (sections 1-3, 6 under session_tree.py — exact insertion points)
    - tests/harness/test_session_tree.py (lines 60-96 TestTreePersistence async pattern; lines 123-149 sync TestCapRaiseGuard pattern)
  </read_first>
  <behavior>
    - A SessionTreeNode constructed without scope/role has scope is None and role is None.
    - SessionTreeManager.allocate_child(limit, scope="review", role="worker") persists a node whose on-disk JSON has scope="review" and role="worker".
    - SessionTreeManager.allocate_child(limit) (no kwargs) persists a node with scope=null and role=null on disk.
    - A node dict WITHOUT "scope"/"role" keys (simulating a pre-V4 file) passed to _hydrate_node yields a SessionTreeNode with scope=None, role=None (back-compat).
    - SessionTreeNode.to_dict() includes "scope" and "role" keys.
  </behavior>
  <action>
    In voss/harness/session_tree.py: add two fields to the SessionTreeNode dataclass between `retry_notes` and `_budget` — `scope: Optional[str] = None` and `role: Optional[str] = None` (both default None, NOT field(default_factory)). `_NODE_FIELDS` auto-rebuilds from dataclasses.fields so no manual edit there. In `_hydrate_node`, append two lines after the existing setdefault calls: `kept.setdefault("scope", None)` and `kept.setdefault("role", None)` (mirrors the transitions/retry_notes back-compat pattern). In `SessionTreeManager.allocate_child`, add keyword-only params `*, scope: str | None = None, role: str | None = None` to the signature and pass `scope=scope, role=role` into the `SessionTreeNode(...)` constructor INSIDE the existing `async with self._lock:` block (do not widen the lock scope — constructor + _write_node_file are already inside it). Leave `create_root` unchanged (root scope/role default to None). Do NOT modify to_dict (asdict picks up the new fields automatically).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestSchemaExtension -x -q</automated>
  </verify>
  <acceptance_criteria>
    - Source assertion: `grep -n "scope: Optional\[str\] = None" voss/harness/session_tree.py` returns the dataclass field line.
    - Source assertion: `grep -c "setdefault(\"scope\", None)\|setdefault(\"role\", None)" voss/harness/session_tree.py` returns 2.
    - Source assertion: `grep -n "scope=scope" voss/harness/session_tree.py` shows the allocate_child constructor passes scope through.
    - Behavior: `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestSchemaExtension -x -q` passes (this test class is authored in Task 3).
  </acceptance_criteria>
  <done>SessionTreeNode carries nullable scope/role; allocate_child persists them; _hydrate_node back-compat preserved; pre-V4 files hydrate with null scope/role.</done>
</task>

<task type="auto">
  <name>Task 2: Add "error" to EXIT_REASONS (additive, schema-freeze-safe)</name>
  <read_first>
    - voss/harness/session.py (lines 74-79 — the EXIT_REASONS frozenset + additive-history comments)
    - tests/harness/test_session_redaction.py (lines 90-124 — TestRunRecordRedaction; confirms EXIT_REASONS is NOT a RunRecord field, so adding to it does not break the 24-field count)
  </read_first>
  <action>
    DECISION RECORDED (resolves RESEARCH Open Question 1 / Assumption A4): add `"error"` to the `EXIT_REASONS` frozenset in voss/harness/session.py rather than overloading `"interrupt"`. Rationale: (a) the SPEC and CONTEXT name "error" as a distinct V4-era termination path (error/timeout/budget); (b) `EXIT_REASONS` is a frozenset constant, NOT a field on SessionRecord/RunRecord/BudgetScope, so adding a member is additive and does not violate the schema freeze — the redaction test's RunRecord 24-field count and key-set assertions are untouched; (c) it follows the established additive-member precedent ("timeout" added in O3, "killed" in O5, each with a trailing comment). Add `"error"` to the set literal and append a comment line `# V4 VTREE-07: "error" added for exception-path subagent finalize (additive).`. Do NOT touch RunRecord, SessionRecord, or any dataclass field.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - Source assertion: `.venv/bin/python -c "from voss.harness.session import EXIT_REASONS; assert 'error' in EXIT_REASONS; print('ok')"` prints `ok`.
    - Schema-freeze: `.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x -q` passes UNMODIFIED (RunRecord still 24 fields; key set unchanged).
    - Schema-freeze: `git diff -- voss/harness/session.py | grep -E "^[+-]" | grep -vE "EXIT_REASONS|\"error\"|^[+-]{3}|# V4 VTREE-07"` returns no lines (only the EXIT_REASONS member + comment changed; no field edits).
  </acceptance_criteria>
  <done>EXIT_REASONS contains "error"; finalize_node will accept exit_reason="error"; redaction test unmodified and green; no frozen-schema field touched.</done>
</task>

<task type="auto">
  <name>Task 3: Update _NODE_JSON_KEYS + author TestSchemaExtension; verify VTREE-05/06 regression</name>
  <read_first>
    - tests/harness/test_session_tree.py (full read — lines 1-40 imports + _NODE_JSON_KEYS; 123-149 TestCapRaiseGuard; 163-187 TestSchemaIsolation; for the class/method conventions to mirror)
    - .planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-PATTERNS.md (test patterns section — sync vs async class style, _NODE_JSON_KEYS update note)
    - voss/harness/session_tree.py (the scope/role fields + allocate_child kwargs from Task 1)
  </read_first>
  <behavior>
    - test_node_keys_exact (existing) passes with scope/role now in the key set.
    - TestSchemaExtension::test_default_scope_role_null — create_root then a node has scope is None, role is None.
    - TestSchemaExtension::test_scope_role_spawn — allocate_child(limit, scope="review", role="worker") persists scope/role to disk (read the node JSON, assert values).
    - TestSchemaExtension::test_spawn_without_scope_role_null — allocate_child(limit) persists scope=null, role=null on disk.
    - TestSchemaExtension::test_pre_v4_file_hydrates_null — a dict missing "scope"/"role" keys passed to _hydrate_node yields scope=None, role=None.
  </behavior>
  <action>
    INTENTIONAL SCHEMA-LOCK UPDATE (call this out in the SUMMARY so the checker does not flag it as a redaction-freeze violation): add `"scope"` and `"role"` to the `_NODE_JSON_KEYS` frozenset at the top of tests/harness/test_session_tree.py. This is a deliberate additive SessionTreeNode extension — `_NODE_JSON_KEYS` is the SessionTreeNode schema-lock guard (DISTINCT from the frozen SessionRecord/RunRecord/BudgetScope schemas, which are NOT touched). The existing `TestSchemaIsolation::test_node_keys_exact` body does not change; only the key set grows. Then author a new `TestSchemaExtension` class (sync where no await needed, async `async def` where allocate_child is awaited — follow the existing TestCapRaiseGuard sync and TestTreePersistence async conventions; no @pytest.mark.asyncio decorator, asyncio_mode=auto handles it) implementing the five behaviors above. Import `_hydrate_node` from voss.harness.session_tree for the back-compat test. Use the `tmp_path` fixture and the existing `_load_nodes_from_disk` / `_node_path` helpers to read persisted JSON. Do NOT modify any other existing test class. Confirm VTREE-05/06 regression by running TestCapRaiseGuard unchanged.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_session_tree.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - Source assertion: `grep -c "\"scope\"\|\"role\"" tests/harness/test_session_tree.py` shows scope/role added to _NODE_JSON_KEYS (and used in the new class).
    - Behavior: `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestSchemaExtension -x -q` passes (all 5 tests).
    - Regression (VTREE-05/06): `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestCapRaiseGuard -x -q` passes unchanged.
    - Regression (VTREE-01/02/03): `.venv/bin/python -m pytest tests/harness/test_session_tree.py -x -q` — full file green including TestSchemaIsolation::test_node_keys_exact.
  </acceptance_criteria>
  <done>_NODE_JSON_KEYS includes scope/role; TestSchemaExtension proves spawn/hydrate behavior; shipped cap-raise + rejected-raise audit regress green; whole test_session_tree.py file passes.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| node JSON file ↔ in-memory SessionTreeNode | persisted envelope/scope/role is the security record of a child's budget cage; corruption or schema drift weakens the cage |
| frozen schemas (SessionRecord/RunRecord/BudgetScope) ↔ V4 additions | the redaction invariant depends on these schemas being unchanged |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V4-01 | Tampering | EXIT_REASONS / frozen schemas | mitigate | Add "error" ONLY to the EXIT_REASONS frozenset (not a RunRecord field); acceptance criteria assert redaction test passes unmodified + git diff shows no field edits |
| T-V4-02 | Spoofing | scope/role node metadata | accept | scope/role are descriptive (V4 populates only what's available at spawn; full EM-dispatch population is V7). Null when unknown; no auth decision is made on these fields in V4 — low value to spoof |
| T-V4-03 | Information Disclosure | node JSON file (scope/role added) | mitigate | scope/role are non-secret labels; existing `chmod(0o600)` on _write_node_file is unchanged and continues to protect node files |
| T-V4-04 | Tampering | _hydrate_node back-compat | mitigate | setdefault(scope/role, None) ensures pre-V4 files load deterministically; test_pre_v4_file_hydrates_null proves no crash/garbage on legacy files |
| T-V4-SC | Tampering | npm/pip/cargo installs | n/a | V4 installs ZERO third-party packages (RESEARCH: all stdlib + existing deps). No package-legitimacy checkpoint required |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_session_tree.py -x -q` — full file green.
- `.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x -q` — UNMODIFIED, green (schema freeze).
- `git diff -- voss/harness/session.py voss/harness/session_tree.py` — only additive scope/role fields, hydrate setdefaults, allocate_child kwargs, and the EXIT_REASONS "error" member; no field removed/changed on any frozen record.
</verification>

<success_criteria>
- SessionTreeNode carries nullable scope + role; allocate_child persists them when supplied, null otherwise; pre-V4 files hydrate with null (VTREE-01, VTREE-08).
- EXIT_REASONS accepts "error" (additive; foundation for V4-02 exception-path finalize).
- _NODE_JSON_KEYS intentionally extended; TestSchemaExtension green.
- VTREE-05 (cap-raise reject) and VTREE-06 (rejected-raise audit) regress green.
- test_session_redaction.py passes unmodified; zero field changes on SessionRecord/RunRecord/BudgetScope.
</success_criteria>

<output>
Create `.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-01-SUMMARY.md` when done. Call out the intentional `_NODE_JSON_KEYS` extension and the EXIT_REASONS "error" decision explicitly so downstream checker does not flag them as freeze violations.
</output>
