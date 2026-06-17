---
phase: V25-server-native-swarm-runtime
plan: 05
type: execute
wave: 3
depends_on: [V25-01, V25-04]
files_modified:
  - voss/harness/server/app.py
  - voss/harness/swarm_store.py
  - tests/harness/server/test_swarm_routes.py
autonomous: true
requirements: [VSWARM-05, VSWARM-07, VSWARM-10]
must_haves:
  truths:
    - "A builder whose task owns a.py is allowed to edit a.py and denied editing b.py — the gate returns deny, the edit does not occur"
    - "On an ownership denial, swarm.needs_operator is emitted and is answerable via the existing POST /session/{id}/permission endpoint"
    - "Each swarm builder turn's assembled prompt contains recall hits filtered to the task's ownedFiles scope"
    - "A reviewer reject writes a .voss/decisions/*.md with populated confidence + related_session frontmatter"
  artifacts:
    - path: "voss/harness/server/app.py"
      provides: "ownership policy attached to the per-turn gate, swarm.needs_operator emit on denial, scoped-recall injection into _run_turn"
      contains: "swarm_policy"
    - path: "voss/harness/swarm_store.py"
      provides: "record_gate_decision writing .voss/decisions/*.md"
      contains: "decisions"
  key_links:
    - from: "_run_turn gate construction"
      to: "session.swarm_policy"
      via: "project_policy=session.swarm_policy injected into PermissionGate"
      pattern: "project_policy"
    - from: "ownership denial"
      to: "swarm.needs_operator + /session/{id}/permission"
      via: "deny intercepted → emit → existing permission Future bridge"
      pattern: "needs_operator"
---

<objective>
Close the enforcement + human-in-the-loop loop: inject each builder's `swarm_policy` (the ownership-deny PermissionsConfig from V25-01) into the per-turn `PermissionGate`, intercept ownership denials to emit `swarm.needs_operator` answerable via the existing `/permission` endpoint, inject task-scoped recall into the swarm turn prompt, and write `.voss/decisions/*.md` on reviewer/gate outcomes. This is the SECOND `app.py`-touching plan — serialized after V25-04 so the two never edit `app.py` in the same wave.

Purpose: VSWARM-05 (server-enforced ownership at the gate), VSWARM-07 (memory-scoped recall per turn), and VSWARM-10 (operator escalation + decision recording) are the remaining `_run_turn` augmentations. They reuse the deny-wins project-policy layer, the existing permission Future bridge, and `MemoryStore.recall` — no new mechanisms (SPEC reuse constraint).

Output: ownership injection + escalation emit + scoped-recall injection in `app.py`; `record_gate_decision` in `swarm_store.py`; tests in `tests/harness/server/test_swarm_routes.py`.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V25-server-native-swarm-runtime/V25-SPEC.md
@.planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md
@.planning/phases/V25-server-native-swarm-runtime/V25-VALIDATION.md

<interfaces>
<!-- Verified against source -->
PermissionGate (permissions.py:200-258): dataclass with `project_policy: PermissionsConfig|None`
(:207) — the deny-wins layer. _check_impl (:260-309) evaluates project_policy FIRST: tool_policy.deny
(:289-290) then match_permission_rules(rules,...)=="deny" (:291-295) → returns (False, "denied by permission rule").
This fires BEFORE mode/auto_yes/safety (:297+), so ownership deny cannot be bypassed by auto_yes.
WRITE = {"fs_write","fs_edit"} (permissions.py:54); the rules dict also keys "fs_edit_many" by tool name.

_run_turn (app.py:179-272): gate built at :202-207 `PermissionGate(mode=, store=, auto_yes=False)`;
_install_server_permissions(gate, session, renderer) at :207 wires prompt_fn/scope_prompt_fn to the
PermissionUpdated event + /session/{id}/permission Future bridge (app.py:137-171, 470-477).
Recall injection at :221-232 sets code_recall_text via cli._render_code_recall_text; passed to run_turn at :246.

<!-- From V25-01 -->
SwarmStore.build_ownership_policy(owned_files)->PermissionsConfig; SwarmStore.scoped_recall(store, query, owned_files, top_k).

<!-- Existing decision file format (.voss/decisions/*.md) — verified -->
Frontmatter: id, status, related_session, confidence, created_at. Body: "# <Title>" + prose.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Inject ownership policy into the gate + emit swarm.needs_operator on denial</name>
  <read_first>
    - voss/harness/server/app.py (_run_turn gate build :202-207, _install_server_permissions :137-171, recall injection :221-232; /session/{id}/permission route :470-477)
    - voss/harness/permissions.py (PermissionGate.project_policy :207, _check_impl deny-wins layer :288-295, WRITE :54)
    - voss/harness/swarm_store.py (build_ownership_policy from V25-01)
    - .planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md (Pattern 4 ownership injection, VSWARM-10 escalation reuse, Pitfall 1 path normalization)
  </read_first>
  <behavior>
    - Test: a swarm builder session whose swarm_policy owns "a.py" is ALLOWED `fs_edit(path="a.py")` and DENIED `fs_edit(path="b.py")` — the gate returns (False, ...) and the edit does not occur; also denied for `path="./a.py"`-vs-`b.py` normalization — `test_ownership_denies_non_owned_write`.
    - Test: on the denial, `swarm.needs_operator` is emitted and a subsequent POST /session/{id}/permission with the matching id resolves the pending Future (the escalation is answerable) — `test_operator_escalation`.
  </behavior>
  <action>
    In `_run_turn` (app.py:202-207), change the gate construction to pass `project_policy=session.swarm_policy` when the session is a swarm builder (ungated sessions keep `project_policy=None` → byte-identical behavior). The builder's `swarm_policy` is set at spawn from `SwarmStore.build_ownership_policy(task.owned_files)` (V25-01) — this rides the deny-wins layer (permissions.py:288-295) which fires before mode/auto_yes (RESEARCH Pattern 4; T-V25-05 gate-bypass mitigation). To emit `swarm.needs_operator` on denial without subclassing the gate, wrap `gate.check` in a closure (RESEARCH §VSWARM-05 option b): call the original check, and on `(False, ...)` for a WRITE tool, `renderer.emit(SwarmNeedsOperator(swarm_id, task_id, session_id, tool_name, path))` then route the operator answer through the EXISTING `_install_server_permissions` Future bridge so `POST /session/{id}/permission` (app.py:470-477) resolves it (VSWARM-10 reuse). Ensure stored owned_files are normalized (`str(Path(p))`) so `./a.py` and `a.py` both match (Pitfall 1).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/server/test_swarm_routes.py::test_ownership_denies_non_owned_write tests/harness/server/test_swarm_routes.py::test_operator_escalation -x</automated>
  </verify>
  <acceptance_criteria>
    A builder is allowed to edit its owned file and denied (gate deny, no write) editing a non-owned file including the `./` form (VSWARM-05); the denial emits swarm.needs_operator answerable via the existing /permission endpoint (VSWARM-10 escalation). Both pytest node ids PASS.
  </acceptance_criteria>
  <done>Ownership policy enforced at the gate for swarm builders; denials escalate through the existing permission bridge.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Scoped-recall injection per swarm turn + reviewer-reject decision recording</name>
  <read_first>
    - voss/harness/server/app.py (recall injection block :221-232 — _render_code_recall_text → code_recall_text → run_turn at :246)
    - voss/harness/swarm_store.py (scoped_recall + add record_gate_decision in this task)
    - voss/harness/cli.py (lines ~1015-1052 _render_code_recall_text shape, referenced by RESEARCH)
    - one existing .voss/decisions/*.md for the frontmatter format (id/status/related_session/confidence/created_at)
    - .planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md (VSWARM-07 scoped injection, VSWARM-10 decision markdown)
  </read_first>
  <behavior>
    - Test: a swarm builder turn's assembled `code_recall_text` contains only recall hits scoped to the task's ownedFiles (a hit for a non-owned file is absent) — `test_recall_scoped_injected_into_turn`.
    - Test: `SwarmStore.record_gate_decision(swarm_id, task_id, session_id, gate_type="reviewer_reject", confidence=0.8, detail=...)` writes a `.voss/decisions/*.md` whose frontmatter has populated `confidence` and `related_session` — `test_reviewer_reject_writes_decision`.
  </behavior>
  <action>
    In `_run_turn` (app.py:221-232), when the session is a swarm builder (has swarm_owned_files), replace/augment the `code_recall_text` assignment to use `SwarmStore.scoped_recall(store, text, session.swarm_owned_files)` (V25-01) so the injected recall is filtered to the task's ownedFiles (RESEARCH VSWARM-07); non-swarm sessions keep the existing `_render_code_recall_text` path unchanged. In `swarm_store.py` add `record_gate_decision(swarm_id, task_id, session_id, gate_type, confidence, detail)` writing `.voss/decisions/<date>-<slug>.md` with frontmatter `{id, status:"active", related_session:<session_id>, confidence:<float>, created_at:<UTC ISO>, swarm_id, task_id, gate_type}` and a `# Swarm Gate Decision` body (matches the existing decision file format; RESEARCH VSWARM-10). Call it on reviewer reject and on resolved ownership gates. Use create-exclusive write discipline (no overwrite of an existing decision file).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/server/test_swarm_routes.py::test_recall_scoped_injected_into_turn tests/harness/server/test_swarm_routes.py::test_reviewer_reject_writes_decision -x</automated>
  </verify>
  <acceptance_criteria>
    A swarm builder turn's prompt contains only ownedFiles-scoped recall hits (VSWARM-07); a reviewer reject writes a decision markdown with populated confidence + related_session frontmatter (VSWARM-10). Both pytest node ids PASS.
  </acceptance_criteria>
  <done>Per-turn recall is scoped to ownedFiles for swarm builders; reviewer rejects record a decision .md.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| LLM tool-call → PermissionGate | builder-supplied write paths checked against the ownership deny policy |
| operator → /permission | human answer to an escalated denial crosses back into the turn |
| swarm → .voss/decisions/ | gate outcomes written to disk as audit artifacts |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V25-05-01 | Elevation of privilege | builder writes outside ownedFiles | mitigate | swarm_policy injected at project_policy layer (permissions.py:288-295) which fires BEFORE mode/auto_yes — auto_yes cannot bypass (RESEARCH Security Domain) |
| T-V25-05-02 | Elevation of privilege | `./a.py` vs `a.py` bypasses fnmatch deny | mitigate | owned_files normalized `str(Path(p))` at write time (Pitfall 1); test asserts the `./` form is denied |
| T-V25-05-03 | Spoofing | forged operator answer resolves a denial | mitigate | Answer routes through the existing per-session pending-Future registry keyed by req id under bearer auth (reuse of _install_server_permissions) |
| T-V25-05-04 | Information disclosure | scoped recall leaks non-owned file context | mitigate | scoped_recall post-filters hits to ownedFiles locators; test asserts non-owned hit absent |
| T-V25-05-05 | Tampering | decision .md overwrites an existing audit file | mitigate | Create-exclusive write; unique date-slug filename; never rewrite an existing decision |
| T-V25-05-SC | Tampering | npm/pip installs | accept | No new packages (RESEARCH audit empty) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/server/test_swarm_routes.py -x` green
- Non-swarm turn parity: `.venv/bin/python -m pytest tests/harness/test_server_app.py tests/harness/test_permissions*.py -x`
- `git diff --check` clean
</verification>

<success_criteria>
- Builder allowed owned write, denied non-owned write incl. `./` form (VSWARM-05)
- Denial emits swarm.needs_operator answerable via /permission (VSWARM-10 escalation)
- Per-turn recall scoped to ownedFiles (VSWARM-07)
- Reviewer reject writes decision .md with confidence + related_session (VSWARM-10)
</success_criteria>

<output>
Create `.planning/phases/V25-server-native-swarm-runtime/V25-05-SUMMARY.md` when done
</output>
