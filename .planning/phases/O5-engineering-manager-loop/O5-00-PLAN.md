---
phase: O5-engineering-manager-loop
plan: 00
type: execute
wave: 0
depends_on: []
files_modified:
  - .planning/phases/O5-engineering-manager-loop/O5-00-SUMMARY.md
autonomous: false
requirements: []
must_haves:
  truths:
    - "O1 substrate (session_tree.py / subagents.py / session.py) is shipped and import-stable"
    - "O2 substrate (team.py: TeamConfig, SubagentRegistry, gate_for_role, filter_toolset_for_role) is shipped and import-stable"
    - "O3-SPEC.md frozen Card / Reviewer / ReviewerVerdict interface has not drifted from O5-RESEARCH.md assumptions"
    - "O4-CONTEXT.md Reviewer-A / Reviewer-B protocol surface matches O5 dispatch assumptions"
    - "O3 / O4 are still planned-only (not yet executed) — W2 / W4 MUST use Protocol-typed mocks, not real imports"
    - "Card↔Ticket field gap (RESEARCH key finding #3) is documented and the wrapper resolution is locked"
    - "EXIT_REASONS extension paths for both 'timeout' (O3) and 'killed' (O5) are confirmed additive and non-conflicting"
  artifacts:
    - path: ".planning/phases/O5-engineering-manager-loop/O5-00-SUMMARY.md"
      provides: "Substrate gate findings + frozen-interface snapshot + cross-phase coordination flags"
      contains: "EM_SUBSTRATE_READY"
  key_links:
    - from: ".planning/phases/O5-engineering-manager-loop/O5-00-SUMMARY.md"
      to: "voss/harness/session_tree.py"
      via: "live-import verification"
      pattern: "from voss\\.harness\\.session_tree import"
    - from: ".planning/phases/O5-engineering-manager-loop/O5-00-SUMMARY.md"
      to: ".planning/phases/O3-board-state-machine/O3-SPEC.md"
      via: "frozen-interface read-only audit"
      pattern: "O3-SPEC.md"
---

<objective>
W0 substrate gate. No code is written. The gate verifies that every interface
O5's later waves depend on is either (a) shipped and import-stable in live code
or (b) frozen on paper in O3-SPEC.md / O4-CONTEXT.md with the exact shape
O5-RESEARCH.md / O5-PATTERNS.md captured.

Purpose: O3 and O4 are not yet executed. O5 plans against frozen interfaces.
If those interfaces have drifted, every later O5 wave produces code that compiles
against a hallucination. This wave produces no implementation — it is the
blocking acceptance gate that proves the substrate is ready.

Output: `O5-00-SUMMARY.md` recording (1) live-import status for O1/O2 surfaces,
(2) frozen-interface snapshot for O3/O4 surfaces, (3) the three cross-phase
coordination flags from RESEARCH §metadata that must be re-surfaced at W5,
(4) the unique tag `EM_SUBSTRATE_READY` only if every check passed.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/ORCHESTRATION-PLAN.md
@.planning/phases/O5-engineering-manager-loop/O5-CONTEXT.md
@.planning/phases/O5-engineering-manager-loop/O5-RESEARCH.md
@.planning/phases/O5-engineering-manager-loop/O5-PATTERNS.md
@.planning/phases/O3-board-state-machine/O3-SPEC.md
@.planning/phases/O3-board-state-machine/O3-CONTEXT.md
@.planning/phases/O4-reviewer-ab-split/O4-CONTEXT.md
@.planning/phases/O2-voss-team-spec-roster/O2-CONTEXT.md
@.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-CONTEXT.md
@voss/harness/subagents.py
@voss/harness/session_tree.py
@voss/harness/session.py
@voss/harness/team.py
@voss/eval/judge.py

<interfaces>
<!-- Live imports the W0 gate must confirm: -->

From voss/harness/session_tree.py (LIVE):
  SessionTreeNode (dataclass: id, root_id, parent_run_id, envelope, terminal_state,
    created_at, ended_at, rejected_raises, _budget, _finalized)
  SessionTreeManager(root_node, *, reserve, cwd)
  finalize_node(node, *, exit_reason, final, cwd)
  mutate_envelope(node, delta, cwd)
  BudgetAllocationError, BudgetCapRaiseError

From voss/harness/session.py (LIVE):
  EXIT_REASONS: frozenset = {"done","max-iter","budget","interrupt","batch-invariant"}
  RunRecord (frozen-style dataclass with __post_init__ EXIT_REASONS guard)

From voss/harness/subagents.py (LIVE):
  SubagentSpec(id, description, role_prompt, model, mode, scope, budget, tools, net)
  SubagentRegistry: register(spec), get(id), ids(), entries()
  run_subagent(*, agent_id, task, registry, cwd, renderer, provider, model, gate,
    cognition=None, node=None, reserve=0)

From voss/harness/team.py (LIVE):
  TeamConfig(name, ceiling, policy, em_agent_id, roster_ids, board, rituals)
    — frozen, slots
  TeamCeiling, TeamPolicy, BoardSpec, RitualSpec, TeamRoleScope
  gate_for_role(spec, base_gate) -> PermissionGate
  filter_toolset_for_role(spec, base_toolset) -> dict[str, ToolEntry]
  compile_team(decl) -> (TeamConfig, SubagentRegistry)

From voss/eval/judge.py (LIVE — reference structured-LLM pattern):
  Verdict (pydantic BaseModel, extra="ignore", Literal["pass","fail"])
  judge_run(*, provider, model, task_prompt, final, file_diff, rubric)
    -> tuple[Verdict | None, str]

<!-- Frozen-on-paper interfaces (NOT YET LIVE). Verify the SPEC text matches RESEARCH/PATTERNS assumptions: -->

From O3-SPEC.md §Requirements (FROZEN, not live):
  Card == session-tree node; fields:
    (node_id, column, risk_tier, retry_count, deadline) + REQ-1 plus
    (scope, artifact, eval_threshold) per O3-02-PLAN
  Board.from_team_config(team_config, recorder, parent_node_id=None)
  Board.move(card, to=Column), Board.dry_run_gate, Board.tick(), Board._tick_once(now)
  6 columns: Backlog → Planned → InProgress → InReview → Blocked → Done
  ReviewerVerdict frozen dataclass:
    (conf: float, source: Literal["A","B"], tier: Literal["fast","strong"],
     verdict: Literal["pass","fail","block"], notes: str, evidence_refs: tuple[str,...])
  class Reviewer(Protocol): review(card) -> ReviewerVerdict
  DeterministicReviewerStub for O3 tests
  SessionTreeManager.get_node(node_id) -> SessionTreeNode | None  (additive, O3 ships)
  node.transitions: list[BoardTransition] additive
  node.retry_notes: list[RetryNote] additive (O3 open question #7 recommended)

From O4-CONTEXT.md (FROZEN, not live):
  Reviewer-A authors bar + verification from original_idea
  Reviewer-B independent tiered judge, EM-narrative-blind, sees
    [artifact, acceptance, repo, original_idea]
  O5 cross-phase coordination ask: ReviewerVerdict.domain_inferred:
    Optional[Literal["code","ai"]] — flag for O4 to add

Card↔Ticket gap (RESEARCH finding #3):
  O3 Card lacks: original_idea, domain, artifact_path, artifact_text, file_diff,
    a_verification_summary. O4-01-PLAN Gate 3 (line 120) WILL STOP if missing.
  O5 resolution: introduce Ticket wrapping Card + EM-authored scaffolding.
  Reviewer Protocol either takes Ticket or (card, ticket) tuple — surface as
    cross-phase coordination ask to O4 planner.
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 1: Live-substrate import gate (O1/O2)</name>
  <files>(no source files written; runs verification commands only)</files>
  <read_first>
    - voss/harness/session_tree.py (full)
    - voss/harness/subagents.py (full)
    - voss/harness/session.py (lines 70-150 for EXIT_REASONS + RunRecord)
    - voss/harness/team.py (lines 87-150 for gate_for_role + filter_toolset_for_role; lines 187-220 for frozen value-object cluster)
  </read_first>
  <action>
    Run the live-import probe via the project venv. Each import MUST succeed and
    the printed attribute MUST match the inventory below; any mismatch is a
    BLOCKING gate failure that halts O5 planning entirely.

    Probe 1 (O1 substrate):
      .venv/bin/python -c "from voss.harness.session_tree import SessionTreeNode, SessionTreeManager, finalize_node, mutate_envelope, BudgetAllocationError, BudgetCapRaiseError; from voss.harness.session import EXIT_REASONS, RunRecord; import dataclasses; assert {f.name for f in dataclasses.fields(SessionTreeNode)} >= {'id','root_id','parent_run_id','envelope','terminal_state','created_at','ended_at','rejected_raises'}; assert 'budget' in EXIT_REASONS; assert 'killed' not in EXIT_REASONS; print('O1_LIVE_OK')"

    Probe 2 (O2 substrate):
      .venv/bin/python -c "from voss.harness.team import TeamConfig, TeamCeiling, TeamPolicy, BoardSpec, TeamRoleScope, gate_for_role, filter_toolset_for_role, compile_team; from voss.harness.subagents import SubagentSpec, SubagentRegistry, run_subagent; import dataclasses; assert TeamConfig.__dataclass_params__.frozen is True; assert TeamConfig.__dataclass_params__.slots is True; print('O2_LIVE_OK')"

    Probe 3 (run_subagent signature carries node + reserve, per OEM-06):
      .venv/bin/python -c "import inspect, voss.harness.subagents as s; sig = inspect.signature(s.run_subagent); params = sig.parameters; assert 'node' in params and 'reserve' in params and 'gate' in params, f'missing kw on run_subagent: {list(params)}'; print('O1_FINALIZE_BOUNDARY_OK')"

    Document each probe's stdout (the three OK tokens) in O5-00-SUMMARY.md
    under a §Live Substrate Probes section. If any probe raises, capture the
    full traceback and STOP — do not advance to Task 2.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "from voss.harness.session_tree import SessionTreeNode, SessionTreeManager, finalize_node, mutate_envelope; from voss.harness.session import EXIT_REASONS; from voss.harness.team import TeamConfig, gate_for_role, filter_toolset_for_role; from voss.harness.subagents import SubagentSpec, SubagentRegistry, run_subagent; import inspect; sig = inspect.signature(run_subagent); assert {'node','reserve','gate'} <= set(sig.parameters); assert 'budget' in EXIT_REASONS and 'killed' not in EXIT_REASONS; print('O1_O2_SUBSTRATE_LIVE')" &amp;&amp; echo EM_LIVE_PROBE_OK</automated>
  </verify>
  <acceptance_criteria>
    - All three import probes print their OK tokens with zero traceback.
    - SessionTreeNode fields include 'rejected_raises' (the append-not-delete audit list).
    - run_subagent kwargs include 'node', 'reserve', 'gate' (the O1 finalize-boundary plumbing).
    - EXIT_REASONS contains 'budget' but does NOT yet contain 'killed' — confirms W1's additive extension is still pending.
  </acceptance_criteria>
  <done>Live-substrate probes pass; SUMMARY.md §Live Substrate Probes populated.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Frozen-paper interface audit (O3-SPEC + O4-CONTEXT)</name>
  <files>(no source files written; reads SPEC text)</files>
  <read_first>
    - .planning/phases/O3-board-state-machine/O3-SPEC.md (full — 9 requirements)
    - .planning/phases/O3-board-state-machine/O3-CONTEXT.md (full — module layout + open questions 5, 6, 7)
    - .planning/phases/O4-reviewer-ab-split/O4-CONTEXT.md (full)
    - .planning/phases/O5-engineering-manager-loop/O5-RESEARCH.md (key findings 1–7, §metadata cross-phase flags)
    - .planning/phases/O5-engineering-manager-loop/O5-PATTERNS.md (§Pattern Assignments)
  </read_first>
  <action>
    Read the O3-SPEC and O4-CONTEXT text directly. Confirm the frozen interface
    O5 plans against has not drifted from the snapshot captured in O5-RESEARCH
    and O5-PATTERNS. The audit MUST produce a checked list in O5-00-SUMMARY.md
    with EXACT line citations.

    For each item below, find the citation in the source SPEC file and record
    `file:line` in SUMMARY.md. If a citation cannot be located, the item is
    DRIFT and W0 fails.

    O3 audit (paper):
    1. Card frozen dataclass; fields exactly: (node_id, column, risk_tier,
       retry_count, deadline) + (scope, artifact, eval_threshold) — O3-SPEC
       REQ-1 + O3-02-PLAN reference in RESEARCH Q2.
    2. 6 columns exactly: Backlog → Planned → InProgress → InReview → Blocked → Done.
    3. ReviewerVerdict frozen dataclass with the 6 fields (conf, source, tier,
       verdict, notes, evidence_refs) — O3-SPEC REQ-7.
    4. Reviewer Protocol: single method `review(card) -> ReviewerVerdict`
       (sync vs async UNCONFIRMED in SPEC text; flag for W2 mock).
    5. DeterministicReviewerStub lives in voss/harness/board/stub.py — O3-CONTEXT
       §Module Layout.
    6. node.transitions: list[BoardTransition] is the audit storage location
       (NOT RunRecord.payload — O3-CONTEXT correction at lines 64-88).
    7. SessionTreeManager.get_node(node_id) MUST be added in O3-01-PLAN
       (additive only) — required by EMBoardHandle.dispatch_card.
    8. O3 open question #5: EXIT_REASONS extension for "timeout" pending —
       confirm "timeout" is NOT yet in live EXIT_REASONS.
    9. Card↔Ticket field gap: O3 Card LACKS (original_idea, domain,
       artifact_path, artifact_text, file_diff, a_verification_summary).
       O4-01-PLAN Gate 3 will STOP if these are missing. O5 resolution is
       the Ticket wrapper (RESEARCH Q2 recommendation). Record this as the
       PRIMARY cross-phase coordination ask.

    O4 audit (paper):
    1. Reviewer-A authors bar + verification from original_idea.
    2. Reviewer-B EM-narrative-blind, sees [artifact, acceptance, repo,
       original_idea].
    3. Reviewer-B has explicit authority to fail a card whose A-verification
       diverges from the idea (residual-2 invariant — MUST be implemented,
       not just documented).
    4. O5 cross-phase coordination ask: add `ReviewerVerdict.domain_inferred:
       Optional[Literal["code","ai"]]` so OEM-09 misroute audit can diff
       chosen_role vs domain_inferred without a notes-regex fallback.

    Cross-phase coordination flags to record verbatim in SUMMARY.md
    §Coordination_Asks for W5 to re-surface:
      C-01 — O3↔O5 Reviewer signature: `Reviewer.review(card)` vs
             `Reviewer.review(ticket)` (RESEARCH OQ-O5-7).
      C-02 — O4↔O5 `ReviewerVerdict.domain_inferred` field addition (OEM-09
             needs it; fallback is regex on notes — worse fidelity).
      C-03 — `EXIT_REASONS` additive: O3 wants "timeout"; O5 wants "killed".
             Both additive, both land in O1 session.py — coordinate ordering
             so the second-lander does not collide with the first.

    Also surface PATTERNS landmines as `LANDMINES` block in SUMMARY:
      L-01 (pydantic posture): EM LLM schemas use lenient `extra="ignore"`
           (mirror judge.py / RunSemantics), NOT strict `extra="forbid"` from
           cognition_schemas.py. STRICT is for config files; LLM output is
           lenient.
      L-02 (kind discriminator): EM-emitted records use `kind="em.*"`; never
           reuse the `board.*` namespace.
      L-03 (no L2 vocab): EM-emitted audit copy must not contain the strings
           "model" / "cost" / "token" / "provider" in user-visible fields.
      L-04 (append-not-delete): kill / rescope NEVER deletes a session-tree
           node — KillRecord/RescopeRecord appended, JSON sealed on disk.
      L-05 (read-from-registry): EM never constructs SubagentSpec or calls
           registry.register; EM only calls registry.get(role).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; test -f .planning/phases/O3-board-state-machine/O3-SPEC.md &amp;&amp; test -f .planning/phases/O3-board-state-machine/O3-CONTEXT.md &amp;&amp; test -f .planning/phases/O4-reviewer-ab-split/O4-CONTEXT.md &amp;&amp; grep -q "ReviewerVerdict" .planning/phases/O3-board-state-machine/O3-SPEC.md &amp;&amp; grep -q "EM-narrative-blind" .planning/phases/O4-reviewer-ab-split/O4-CONTEXT.md &amp;&amp; grep -q "Card.*node_id.*column.*risk_tier" .planning/phases/O3-board-state-machine/O3-SPEC.md &amp;&amp; echo EM_PAPER_AUDIT_OK</automated>
  </verify>
  <acceptance_criteria>
    - O3-SPEC + O3-CONTEXT + O4-CONTEXT files exist and contain the named anchor strings.
    - 9 O3 audit items each have a `file:line` citation in SUMMARY.
    - 4 O4 audit items each have a citation.
    - C-01 / C-02 / C-03 coordination flags written verbatim into SUMMARY §Coordination_Asks.
    - L-01..L-05 landmines block written verbatim into SUMMARY §Landmines.
  </acceptance_criteria>
  <done>SUMMARY.md §Paper Interface Audit + §Coordination_Asks + §Landmines populated; zero drift detected; closes with the unique tag EM_SUBSTRATE_READY only if both Task 1 and Task 2 fully passed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| frozen interfaces ↔ planned code | O5 W1–W5 write code against frozen-on-paper O3/O4 surfaces; drift here propagates silently into hallucinated implementation. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O5-W0-01 | Tampering | O3-SPEC.md drift between paper and live | mitigate | Direct file-line audit in Task 2; any drift halts the gate. |
| T-O5-W0-02 | Information disclosure | Cross-phase coordination asks lost | mitigate | C-01/C-02/C-03 recorded verbatim in SUMMARY for W5 to re-surface. |
| T-O5-W0-03 | Repudiation | Substrate gate passes silently without evidence | mitigate | Probe stdout tokens + file:line citations are persisted in SUMMARY. |
</threat_model>

<verification>
.venv/bin/python -c "from voss.harness.session_tree import SessionTreeNode, SessionTreeManager, finalize_node; from voss.harness.session import EXIT_REASONS; from voss.harness.team import TeamConfig, gate_for_role, filter_toolset_for_role; from voss.harness.subagents import SubagentSpec, SubagentRegistry, run_subagent; import inspect; assert {'node','reserve','gate'} <= set(inspect.signature(run_subagent).parameters); print('substrate ok')" && grep -q "EM_SUBSTRATE_READY" .planning/phases/O5-engineering-manager-loop/O5-00-SUMMARY.md && echo EM_SUBSTRATE_READY
</verification>

<success_criteria>
- Both Tasks pass blocking.
- O5-00-SUMMARY.md contains §Live Substrate Probes, §Paper Interface Audit, §Coordination_Asks, §Landmines.
- The tag `EM_SUBSTRATE_READY` is written exactly once at the bottom of SUMMARY.md.
- Zero code files created in this wave; this is a gate, not an implementation.
- W1 may proceed only after this SUMMARY exists and ends in `EM_SUBSTRATE_READY`.
</success_criteria>

<output>
Create `.planning/phases/O5-engineering-manager-loop/O5-00-SUMMARY.md` containing:

```
# O5-00 Substrate Gate SUMMARY

## Live Substrate Probes
[stdout from Task 1 probes]

## Paper Interface Audit
### O3 (9 items)
- [item 1, file:line]
...
### O4 (4 items)
- [item 1, file:line]
...

## Coordination_Asks
- C-01: ...
- C-02: ...
- C-03: ...

## Landmines
- L-01: pydantic posture — LENIENT for LLM output
- L-02: em.* kind namespace; never reuse board.*
- L-03: no L2 vocab in audit copy
- L-04: append-not-delete on kill/rescope
- L-05: read-from-registry, never construct SubagentSpec

EM_SUBSTRATE_READY
```
</output>
