---
phase: BOS4-decision-ledger-schema
plan: BOS4-04
type: execute
wave: 2
depends_on: [BOS4-03]
files_modified:
  - voss/harness/swarm_runtime.py
  - tests/harness/test_bos_decision_swarm_emit.py
autonomous: true
requirements: [BOS-DATA-02]

must_haves:
  truths:
    - "When the swarm assigns a task to a role, a task_to_agent decision record is appended to .voss/bos/decisions.jsonl"
    - "The emitted record carries the goal, roster, available_models, and cwd captured at assignment time"
    - "The record's as_of points at the BOS3 event ledger tail at assignment time"
    - "The emitted record validates against contracts/decision-ledger.schema.json"
  artifacts:
    - path: "voss/harness/swarm_runtime.py"
      provides: "task_to_agent emission at the assignment seam"
      contains: "build_task_to_agent_record"
    - path: "tests/harness/test_bos_decision_swarm_emit.py"
      provides: "assignment-seam emission test"
      contains: "decisions.jsonl"
  key_links:
    - from: "voss/harness/swarm_runtime.py"
      to: "voss/harness/bos_decisions.py"
      via: "build_task_to_agent_record + append_decision after mark_assigned"
      pattern: "build_task_to_agent_record|append_decision"
---

<objective>
Wire the FIRST real decision producer: the swarm assignment seam. Immediately
after `store.mark_assigned(swarm_id, task.id)` in `run_cli_member`
(swarm_runtime.py line 165), emit a `task_to_agent` decision record using the
builders from BOS4-03. This is inline emission at decision time (D-R01): the
record freezes the exact assignment context (goal, roster, models, cwd) and the
BOS3 event-ledger tail as `as_of`.

Per D-R02 this is one of exactly two live producers in this phase. No stubs for
the other decision types.

Purpose: Delivers the task_to_agent half of BOS-DATA-02's runtime coverage.
Output: emission call in `swarm_runtime.py`, new emission test.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md
@.planning/phases/BOS4-decision-ledger-schema/BOS4-PATTERNS.md
@contracts/decision-ledger.schema.json
@voss/harness/swarm_runtime.py
@voss/harness/swarm_store.py

<interfaces>
<!-- From BOS4-03 (voss/harness/bos_decisions.py): -->
- build_task_to_agent_record(*, decision_id, task_id, chosen_agent_id,
    candidate_agents, feature_snapshot, entity_ref, as_of, rationale,
    autonomy_band="") -> dict
- build_as_of(events_path: Path) -> dict   (reads BOS3 events.jsonl tail)
- decisions_ledger_path(cwd) -> Path
- append_decision(cwd, record) -> bool

<!-- From voss/harness/swarm_runtime.py run_cli_member (lines 117-167): -->
- params in scope at the seam (line 165): store (SwarmStore), repo_root (Path),
  swarm_id (str), role (Role: .name, .agent, .model), task (Task: .id, .goal)
- store.get(swarm_id) -> Swarm | None  (Swarm.roster: list[Role])
- store.mark_assigned(swarm_id, task.id)  <-- emit IMMEDIATELY after this

<!-- Role fields: name:str, agent:str (default "voss"), model:str (default "default") -->
<!-- BOS3 events ledger path: repo_root/".voss"/"bos"/"events.jsonl" -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Emit task_to_agent record after mark_assigned</name>
  <files>voss/harness/swarm_runtime.py</files>
  <read_first>
    - voss/harness/swarm_runtime.py (lines 117-200 — run_cli_member; emit AFTER line 165 `store.mark_assigned`, BEFORE `resolve_agent_argv`)
    - voss/harness/swarm_store.py (lines 64-95 Role/Task/Swarm shapes; line 262 store.get)
    - voss/harness/bos_decisions.py (builders + append_decision — from BOS4-03)
    - .planning/phases/BOS4-decision-ledger-schema/BOS4-PATTERNS.md (lines 246-278 — exact seam + field mapping)
  </read_first>
  <action>
    In voss/harness/swarm_runtime.py, import build_task_to_agent_record,
    build_as_of, decisions_ledger_path, append_decision from
    voss.harness.bos_decisions. Immediately after `store.mark_assigned(swarm_id,
    task.id)` (line 165) and before `resolve_agent_argv`, emit a task_to_agent
    decision record:
      - swarm = store.get(swarm_id); roster = swarm.roster if swarm else [role]
      - feature_snapshot (D-R06): {"goal": task.goal,
        "roster": [r.name for r in roster],
        "available_models": [r.model for r in roster],
        "cwd": str(repo_root)}
      - entity_ref: {"task_id": task.id, "swarm_id": swarm_id, "agent_id": role.agent}
      - as_of: build_as_of(repo_root / ".voss" / "bos" / "events.jsonl")
      - decision_id: stable per assignment, e.g. f"dec-{swarm_id}-{task.id}"
        (so a re-run dedups to one record per assignment)
      - candidate_agents: [role.agent]; chosen_agent_id: role.agent
      - rationale: prose naming the gate, e.g.
        f"swarm assignment: task {task.id} -> role {role.name} (agent {role.agent})"
      - autonomy_band: "" (no band producer pre-BOS9, D-R03)
    Append via append_decision(repo_root, record). Add a short comment marking
    this as inline emission at the assignment seam (D-R01/D-R02). Wrap the emit in
    a best-effort guard so a ledger write failure does NOT crash the swarm run
    (mirror the best-effort posture of _render_diff_preview): catch and swallow
    OSError/ValueError from the emit, never the whole flow. Do NOT capture any
    outcome/result data here (no-leakage, schema D-04) — assignment time only.
  </action>
  <verify>
    <automated>grep -n "build_task_to_agent_record\|append_decision" voss/harness/swarm_runtime.py | grep -v '^#'</automated>
  </verify>
  <acceptance_criteria>
    - build_task_to_agent_record + append_decision are called after mark_assigned
    - feature_snapshot contains exactly goal, roster, available_models, cwd (D-R06)
    - emit is best-effort guarded (swarm run does not crash on ledger write error)
    - no outcome/result fields captured at assignment time
    - .venv/bin/python -c "import voss.harness.swarm_runtime" succeeds
  </acceptance_criteria>
  <done>Assignment seam emits a schema-valid task_to_agent record at decision time.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Test the assignment-seam emission</name>
  <files>tests/harness/test_bos_decision_swarm_emit.py</files>
  <read_first>
    - tests/harness/test_bos_event_ledger.py (validator fixture + tmp_path ledger style)
    - voss/harness/swarm_runtime.py (run_cli_member — drive it with a stub spawn_fn, or call the emit path directly)
    - voss/harness/swarm_store.py (SwarmStore, create swarm + task to set up the seam)
    - contracts/decision-ledger.schema.json
  </read_first>
  <behavior>
    - Set up a SwarmStore in tmp_path, create a swarm with a roster and one task.
    - Drive the assignment seam (call run_cli_member with an injected stub
      spawn_fn that returns a no-op handle, OR factor the emit into a small helper
      and call it directly — prefer driving run_cli_member for fidelity).
    - Assert .voss/bos/decisions.jsonl exists under repo_root and contains exactly
      one record with decision_type=="task_to_agent".
    - Assert the record validates against contracts/decision-ledger.schema.json.
    - Assert feature_snapshot has keys goal, roster, available_models, cwd.
    - Assert entity_ref.task_id == task.id and entity_ref.swarm_id == swarm_id.
    - Assert re-running the same assignment is a dedup no-op (still one record).
  </behavior>
  <action>
    Create tests/harness/test_bos_decision_swarm_emit.py. Reuse the module-scope
    jsonschema validator fixture pointed at contracts/decision-ledger.schema.json.
    Build the swarm/task fixtures via SwarmStore, drive run_cli_member with a stub
    spawn_fn (and stub the worktree/result helpers as needed — mirror existing
    swarm_runtime tests if present under tests/harness/), then assert the
    behaviors above. If driving the full run_cli_member requires heavy stubbing,
    it is acceptable to test the emission by invoking the same builder+append call
    path the seam uses with the identical in-scope values, but the seam itself
    must remain covered by at least the grep-level acceptance from Task 1.
  </action>
  <verify>
    <automated>.venv/bin/pytest tests/harness/test_bos_decision_swarm_emit.py -x 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - tests/harness/test_bos_decision_swarm_emit.py exits 0
    - Test asserts a task_to_agent record is written and schema-valid
    - Test asserts dedup no-op on repeat assignment
  </acceptance_criteria>
  <done>Assignment-seam emission is covered by a green schema-validating test.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| swarm assignment → decisions.jsonl | task goal, role/agent identity, repo path captured into the ledger |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-BOS4-04-01 | Information Disclosure | feature_snapshot capturing task.goal (may contain sensitive prompt text) | accept | goal is already persisted in the BOS3 event ledger + file-bus task file; capturing it here is consistent with existing exposure. No NEW surface; record is 0o600 local. |
| T-BOS4-04-02 | Denial of Service | a ledger write error aborting the swarm run | mitigate | Emit wrapped in best-effort guard (catch OSError/ValueError); swarm assignment proceeds regardless. |
| T-BOS4-04-03 | Tampering | duplicate records on re-run inflating the ledger | mitigate | Stable decision_id per (swarm_id, task_id) → dedup-by-decision_id makes re-emit a no-op. |
| T-BOS4-04-SC | Tampering | new package installs | mitigate | None — no new dependency; reuses BOS4-03 module + existing swarm runtime. No install task. |
</threat_model>

<verification>
- .venv/bin/pytest tests/harness/test_bos_decision_swarm_emit.py exits 0
- .venv/bin/python -c "import voss.harness.swarm_runtime" succeeds
- Emitted record validates against contracts/decision-ledger.schema.json
- No regression: .venv/bin/pytest tests/harness/test_bos_decision_ledger.py still exits 0
</verification>

<success_criteria>
- task_to_agent record emitted inline at the mark_assigned seam (D-R01/D-R02)
- feature_snapshot = {goal, roster, available_models, cwd} (D-R06)
- as_of resolved from BOS3 event-ledger tail (D-R05)
- emission best-effort guarded; dedups per assignment; schema-valid
</success_criteria>

<output>
Create `.planning/phases/BOS4-decision-ledger-schema/BOS4-04-SUMMARY.md` when done.
</output>
