---
phase: V25-server-native-swarm-runtime
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/swarm_store.py
  - voss/harness/swarm/__init__.py
  - voss/harness/swarm/events.py
  - voss/harness/swarm/prompts/coordinator.md
  - voss/harness/swarm/prompts/builder.md
  - voss/harness/swarm/prompts/reviewer.md
  - tests/harness/test_swarm_store.py
autonomous: true
requirements: [VSWARM-01, VSWARM-06, VSWARM-07, VSWARM-09, VSWARM-11]
must_haves:
  truths:
    - "Creating a swarm + 2 tasks then replaying events/*.jsonl alone reconstructs identical state"
    - "The JSONL event log is append-only — no event file is ever rewritten in place"
    - "Two concurrent tasks owning the same file are rejected; the same two ordered by dependsOn are accepted"
    - "A scoped-recall helper returns only hits whose locator path is in the task's ownedFiles"
    - "SwarmStore indexes each agent session by swarm_id/role/owned_files and lists a swarm's agents by swarm_id"
    - "A default 2-builder roster contains no scout agent"
  artifacts:
    - path: "voss/harness/swarm_store.py"
      provides: "SwarmStore, Swarm/Task/Role models, overlap validation, session index, ownership-policy builder, scoped-recall helper"
      min_lines: 200
    - path: "voss/harness/swarm/events.py"
      provides: "Append-only JSONL SwarmEventLog writer + replay reader"
      min_lines: 60
    - path: "voss/harness/swarm/prompts/coordinator.md"
      provides: "Coordinator role-prompt template (authored from A13 coordinator flow)"
      min_lines: 20
  key_links:
    - from: "voss/harness/swarm_store.py"
      to: "voss/harness/swarm/events.py"
      via: "every SwarmStore mutation appends an event"
      pattern: "events\\.(append|log|write)"
    - from: "SwarmStore.replay"
      to: ".voss/swarm/<id>/events/events.jsonl"
      via: "rebuild state from event log alone"
      pattern: "replay|from_events"
---

<objective>
Build `swarm_store.py` — the server-side single source of truth for swarm state — plus the append-only JSONL event log that mirrors every mutation, the three git-tracked role-prompt templates, overlap validation, the per-session swarm index, the ownership-policy builder, and the scoped-recall helper. This is the Wave-1 foundation every other V25 plan imports.

Purpose: All 11 requirements flow through SwarmStore. State must be rebuildable purely by replaying `events/*.jsonl` (VSWARM-01/11), and the store is where overlap validation (VSWARM-06), the session index (VSWARM-09 headless boundary), scoped recall (VSWARM-07), and the ownership-deny policy (consumed by V25-05) live as pure Python — keeping `app.py` edits minimal and serialized.

Output: `voss/harness/swarm_store.py`, `voss/harness/swarm/{__init__,events}.py`, `voss/harness/swarm/prompts/{coordinator,builder,reviewer}.md`, `tests/harness/test_swarm_store.py`.
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
<!-- Reuse these existing harness symbols — do not rebuild. Verified against source. -->

PermissionsConfig (voss/harness/cognition_schemas.py:56-66) — model_config = STRICT (extra=forbid).
Construct with DECLARED fields ONLY. The `rules: dict[str, Any]` field accepts
`{tool_name: {path_pattern: "allow"|"deny"}}` sub-maps. Within a sub-map last-match-wins
(list "*" first). Do NOT pass undeclared kwargs — STRICT raises ValidationError.

match_permission_rules path arg (voss/harness/permissions.py:58-64): for fs_write/fs_edit
the matched arg_str is `str(args.get("path",""))` — the RAW path the agent passes. WRITE set
(permissions.py:54) is `{"fs_write","fs_edit"}` and does NOT include "fs_edit_many"; for
fs_edit_many the rules key is matched by tool-name directly, so the ownership policy must list
all three tool keys ("fs_write","fs_edit","fs_edit_many").

MemoryStore.recall (voss/harness/memory_store.py:605-611):
`def recall(self, query, *, top_k=5, source=None) -> list[Hit]` — NO scope param today.
Hit (memory_store.py:43-45) carries `.locator`; code-chunk hits use a `code:<filepath>:<seq>`
locator form (V19). Scoped recall is a POST-FILTER wrapper, not a signature change.

memory_store JSONL append discipline (memory_store.py write_turn pattern): portalocker advisory
lock + `open(path, "a")` + `json.dumps(evt) + "\n"`. Mirror this for the swarm event log.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: SwarmStore models + append-only JSONL event log + replay</name>
  <read_first>
    - voss/harness/memory_store.py (lines 600-640 recall, the write_turn append+portalocker pattern, Hit dataclass at :43-45)
    - voss/harness/session.py (SessionRecord.new id form `uuid4().hex[:12]`, `.voss/` save discipline)
    - .planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md (Pattern 5 JSONL event log, event envelope schema, replay algorithm; Pitfall — never rewrite JSONL in place)
    - .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-SPEC.md (`.voss/swarm/<id>/` directory schema retained as audit format)
  </read_first>
  <behavior>
    - Test: `SwarmStore.create(goal=...)` then `add_task` x2 then `SwarmStore.replay(swarm_id)` from events.jsonl ALONE reconstructs identical Swarm (same tasks, same roster, same goal) — `test_replay_reconstructs_state`.
    - Test: writing N events produces a single append-only `events/events.jsonl`; the file's first-N lines are never rewritten after a later append (assert byte-prefix stability) — `test_event_log_append_only`.
    - Test: replaying a swarm whose tasks went open→assigned→done yields each task's full ordered transition list with no gaps — `test_audit_replay_full_timeline`.
  </behavior>
  <action>
    Create `voss/harness/swarm/__init__.py` (empty package marker) and `voss/harness/swarm/events.py` with a `SwarmEventLog` writer: `append(swarm_id, event_dict)` opens `.voss/swarm/<swarm_id>/events/events.jsonl` with portalocker advisory lock and `open("a")`, writing `json.dumps(evt) + "\n"` — mirror `memory_store.py` write_turn discipline; NEVER use `path.write_text` on an events file (research Anti-Patterns). Provide `read_events(swarm_id) -> list[dict]` that reads all lines in order. Event envelope per RESEARCH §Pattern 5: `{v:1, id:<8-hex>, type, swarm_id, ts:<UTC ISO>, actor, payload:{...}}`.
    Create `voss/harness/swarm_store.py` with pydantic v2 models `Role{name, model, auth_pref}`, `Task{id, goal, owned_files:list[str], depends_on:list[str], state}` (state in open|assigned|done), `Swarm{id, goal, cwd, roster:list[Role], tasks:list[Task]}` using `model_config = ConfigDict(extra="ignore")` to match the `_Base` convention. `SwarmStore` is app-scoped (NOT a module global — research Anti-Pattern: module globals leak across TestClient instances). `create(goal, cwd)` mints a swarm id (`uuid4().hex[:12]`), appends a `swarm.create` event, returns the Swarm. `add_task(...)` appends the task and a `swarm.task` event. `mark_assigned`/`mark_done` append `swarm.assign`/`swarm.worker_done` and mutate task state. `replay(swarm_id)` rebuilds a Swarm purely from `read_events` by applying each event as a state transition (swarm.create→new Swarm, swarm.task→add open task, swarm.assign→open→assigned, swarm.worker_done→assigned→done). Normalize every stored `owned_files` path at task-creation time via `str(Path(p))` (strips `./`) per RESEARCH Pitfall 1 (path normalization at WRITE time, not check time).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_swarm_store.py::test_replay_reconstructs_state tests/harness/test_swarm_store.py::test_event_log_append_only tests/harness/test_swarm_store.py::test_audit_replay_full_timeline -x</automated>
  </verify>
  <acceptance_criteria>
    Replay from `events/events.jsonl` alone yields a Swarm byte-equal to the live one (VSWARM-01); the events file is append-only with stable byte-prefix across appends (VSWARM-01); a completed swarm's replay shows every task open→assigned→done in order with no gaps (VSWARM-11). All three pytest node ids PASS.
  </acceptance_criteria>
  <done>SwarmStore + SwarmEventLog exist; the three replay/append-only tests pass deterministically.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Overlap validation + session index + ownership-policy builder + scoped-recall helper</name>
  <read_first>
    - voss/harness/swarm_store.py (the models created in Task 1 — same file)
    - voss/harness/cognition_schemas.py (lines 44-66: ToolPolicy, PermissionsConfig, STRICT — declared fields only)
    - voss/harness/permissions.py (lines 54-100: WRITE set, _rule_command_arg path arg, match_permission_rules last-match-wins, _decision_for fnmatch)
    - voss/harness/memory_store.py (lines 605-631 recall signature + Hit.locator)
    - .planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md (Pattern 4 ownership construction, VSWARM-07 post-filter approach, VSWARM-09 Python-side index Open-Q2, Pitfall 1 path normalization)
  </read_first>
  <behavior>
    - Test: `add_task` with owned_files overlapping an existing active task's owned_files raises an overlap error; the same two tasks where one declares the other in depends_on succeeds — `test_overlap_rejected_unless_dependson` (route-level 4xx is V25-04; here assert the store raises).
    - Test: `build_ownership_policy(["src/a.py"])` returns a PermissionsConfig whose rules deny fs_write/fs_edit/fs_edit_many to a non-owned path and allow them to "src/a.py" when evaluated through `match_permission_rules` — `test_ownership_policy_denies_non_owned`.
    - Test: `scoped_recall(store, query, owned_files=["src/a.py"])` returns only Hits whose locator path is in owned_files — `test_recall_scoped_to_owned_files`.
    - Test: `default_roster(builders=2)` contains coordinator + 2 builders + reviewer and NO scout — `test_default_roster_no_scout`.
  </behavior>
  <action>
    In `swarm_store.py` add `register_agent(swarm_id, session_id, role, owned_files)` and `list_agents_by_swarm(swarm_id)` maintaining an in-memory `dict[session_id -> {swarm_id, role, owned_files}]` — this is the headless VSWARM-09 acceptance boundary per RESEARCH Open-Q2 (the Rust SQLite column-add is V25-03, a separate cargo concern). Add `validate_no_overlap(new_task, active_tasks)` rejecting any task whose normalized owned_files intersect another active task's owned_files UNLESS the two are ordered via depends_on; raise a typed `OwnershipOverlapError`. Add `build_ownership_policy(owned_files) -> PermissionsConfig` constructing `PermissionsConfig(rules={tool: {"*":"deny", **{f:"allow" for f in owned_files}} for tool in ("fs_write","fs_edit","fs_edit_many")})` — DECLARED fields only (STRICT), "*" listed first so last-match-wins lets owned paths override the deny (RESEARCH Pattern 4). Add `scoped_recall(store, query, owned_files, top_k=5)` that calls `MemoryStore.recall(query, top_k=top_k*3)` then post-filters hits whose locator path component is in normalized owned_files (RESEARCH VSWARM-07 — wrapper, not a recall signature change). Add `default_roster(builders=2)` returning coordinator+builders+reviewer with NO scout (RESEARCH VSWARM-07: scout folded into chroma, never a default roster member).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_swarm_store.py::test_overlap_rejected_unless_dependson tests/harness/test_swarm_store.py::test_ownership_policy_denies_non_owned tests/harness/test_swarm_store.py::test_recall_scoped_to_owned_files tests/harness/test_swarm_store.py::test_default_roster_no_scout -x</automated>
  </verify>
  <acceptance_criteria>
    Overlap rejected unless depends_on-ordered (VSWARM-06 store layer); ownership policy denies non-owned write and allows owned write through `match_permission_rules` (VSWARM-05 policy builder); scoped recall returns only owned-file hits and default roster has no scout (VSWARM-07); session index lists agents by swarm_id (VSWARM-09 headless). All four pytest node ids PASS.
  </acceptance_criteria>
  <done>Overlap validation, session index, ownership-policy builder, and scoped-recall helper exist and pass their tests.</done>
</task>

<task type="auto">
  <name>Task 3: Author the three role-prompt templates</name>
  <read_first>
    - .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-CONTEXT.md (Coordinator Flow section — the behavioral spec the coordinator prompt is authored FROM)
    - .planning/phases/V25-server-native-swarm-runtime/V25-CONTEXT.md (D-05 versioned templates; D-01 coordinator is a full ServerSession that seeds tasks + emits swarm.assign)
    - .planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md (Open Question 1: BridgeSwarm playbook ABSENT on disk — author fresh, do NOT plan a "copy recovered playbook" step)
  </read_first>
  <action>
    Author `voss/harness/swarm/prompts/coordinator.md` FROM SCRATCH using A13-CONTEXT.md's Coordinator Flow as the behavioral spec (the BridgeSwarm playbook is confirmed ABSENT from disk per RESEARCH Open-Q1 — do not attempt to copy it). The coordinator prompt directs: decompose the goal into disjoint-file tasks, call `POST /swarm/{id}/task` per task, emit `swarm.assign` per builder, gate/reject reviewer outcomes, re-plan mid-run as a full ServerSession (per D-01). Author `builder.md` (work only within ownedFiles; a write outside is denied at the gate and escalates to operator) and `reviewer.md` (approve/reject with a recorded decision + confidence). Use Jinja-style `{{ }}` placeholders for per-run task context (goal, owned_files, task list). Keep each focused; mark coordinator decomposition QUALITY as out-of-scope-here (validated separately per SPEC). Do NOT inline any decomposition-quality eval.
  </action>
  <verify>
    <automated>test -f voss/harness/swarm/prompts/coordinator.md && test -f voss/harness/swarm/prompts/builder.md && test -f voss/harness/swarm/prompts/reviewer.md && grep -qi 'swarm.assign\|owned' voss/harness/swarm/prompts/coordinator.md</automated>
  </verify>
  <acceptance_criteria>
    Three git-tracked prompt templates exist under `voss/harness/swarm/prompts/`; coordinator.md references the assign/ownership flow; none claims to be copied from a recovered playbook (authored fresh per RESEARCH Open-Q1). Satisfies D-05.
  </acceptance_criteria>
  <done>coordinator.md, builder.md, reviewer.md exist with task-context placeholders, authored from the A13 coordinator flow.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| disk → SwarmStore (replay) | event-log JSONL is parsed back into runtime state; malformed/forged lines cross here |
| LLM tool-call → ownership policy | builder-supplied file paths are matched against the deny policy this plan builds |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V25-01-01 | Tampering | events.jsonl rewritten in place | mitigate | Append-only via portalocker + open("a"); never path.write_text on an events file; replay tolerates trailing partial line |
| T-V25-01-02 | Tampering | JSONL injection via crafted goal/task text | mitigate | Serialize via `json.dumps` only (no string formatting); no f-string-built JSON lines (RESEARCH Security Domain) |
| T-V25-01-03 | Elevation of privilege | ownership policy fails to deny `./src/x.py` form | mitigate | Normalize owned_files with `str(Path(p))` at task-creation (write time) per Pitfall 1; deny "*" listed first, owned last (last-match-wins) |
| T-V25-01-04 | Tampering | PermissionsConfig constructed with extra fields silently dropped | mitigate | STRICT model_config: declared fields only (`rules`); test asserts deny fires through real `match_permission_rules` |
| T-V25-01-SC | Tampering | npm/pip installs | accept | No new packages this phase (RESEARCH Package Legitimacy Audit empty); all deps already in venv |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_swarm_store.py -x` all green
- `git diff --check` clean (no whitespace errors)
- `swarm_store.py` imports cleanly: `.venv/bin/python -c "from voss.harness.swarm_store import SwarmStore"`
</verification>

<success_criteria>
- SwarmStore reconstructs identically from events/*.jsonl alone (VSWARM-01)
- Event log is append-only (VSWARM-01); replay yields full ordered timeline (VSWARM-11)
- Overlap rejected unless depends_on-ordered (VSWARM-06 store layer)
- Ownership-policy builder denies non-owned writes (feeds VSWARM-05)
- Scoped-recall helper filters to ownedFiles; default roster has no scout (VSWARM-07)
- Session index lists agents by swarm_id (VSWARM-09 headless boundary)
- Three role-prompt templates authored fresh (D-05)
</success_criteria>

<output>
Create `.planning/phases/V25-server-native-swarm-runtime/V25-01-SUMMARY.md` when done
</output>
