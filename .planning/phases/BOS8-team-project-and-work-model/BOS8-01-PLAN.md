---
phase: BOS8-team-project-and-work-model
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md
autonomous: true
requirements:
  - BOS-WORK-01
  - BOS-WORK-02
  - BOS-WORK-03

must_haves:
  truths:
    - "A reader can look up all 8 BOS entities (team, project, task, PR, service, incident, agent-run, engineer) and unambiguously see which TIER each belongs to: work / actor / reference (D-04)"
    - "A reader can read the projection invariant stated as an INVARIANT not a default: the work model is a read model derived from BOS3's append-only event log, there is NO separate mutable authoritative entity store, and any work item's state is reconstructable as-of any time (D-01)"
    - "A reader can read that reference entities (team, project, engineer, service) enter via registration/upsert events through the SAME append-only log, not via side config/reference tables (D-02)"
    - "A reader can see ONE canonical task lifecycle state machine with named states and transitions, applied only to WORK items, with off-path states (blocked/abandoned) — and a stated anti-PM-suite guardrail (D-03)"
    - "A reader can see how agent-run is reconciled as a DUAL entity (a work item with a lifecycle AND an actor that acts on other items) against BOS4 actor + BOS6 anti-surveillance / no individual ranking (D-04)"
    - "A reader can read that work intake happens two ways — auto-derived from harness sessions/swarm tasks and manual creation modeled as a creation EVENT (not a mutation) — with external Git/PM intake reserved to BOS12 (D-05)"
    - "A reader can read that work items link to sessions, swarm tasks, files, reviews, validations via BOS3 root correlation/causation refs and to outcomes via BOS5 entity-anchored joins, with NO new link primitive invented (D-06)"
    - "A reader can find a section mapping each of BOS-WORK-01, BOS-WORK-02, BOS-WORK-03 to the spec section that satisfies it"
  artifacts:
    - path: ".planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md"
      provides: "The BOS8 work model spec: 8-entity tiered model + canonical task lifecycle + projection/intake/linking semantics over BOS3/BOS5, covering BOS-WORK-01/02/03"
      min_lines: 120
      contains: "Entity Tier Model"
  key_links:
    - from: "BOS8-WORK-MODEL-SPEC.md entity tier model"
      to: "the 8 entities named in BOS-WORK-01"
      via: "a table assigning each entity to a tier (work/actor/reference)"
      pattern: "team.*project.*task.*PR.*service.*incident.*agent-run.*engineer"
    - from: "BOS8-WORK-MODEL-SPEC.md projection section"
      to: "BOS3's append-only event log (D-01)"
      via: "stated read-model invariant + no-mutable-store claim"
      pattern: "no.*mutable.*store|read model|projection"
    - from: "BOS8-WORK-MODEL-SPEC.md lifecycle section"
      to: "the canonical work-item state machine (D-03)"
      via: "an enumerated ordered state list plus off-path states"
      pattern: "intake.*triaged.*assigned.*in_progress.*in_review.*validated.*done"
    - from: "BOS8-WORK-MODEL-SPEC.md linking section"
      to: "BOS3 correlation/causation + BOS5 outcome joins (D-06)"
      via: "reuse of existing refs, no new link table"
      pattern: "correlation|causation|outcome join"
---

<objective>
Produce the BOS8 work model spec — a single docs-first specification that defines the Behavioral OS engineering entities (team, project, task, PR, service, incident, agent-run, engineer), the canonical work-item lifecycle + intake model, and how work items link to sessions/swarm/files/reviews/validations/outcomes. The deliverable is one markdown spec: an 8-entity tiered model + a canonical task lifecycle state machine + projection/intake/linking semantics expressed over BOS3 and BOS5. Covers BOS-WORK-01, BOS-WORK-02, BOS-WORK-03.

Purpose: This spec is the logical work/entity contract every later work-surface phase inherits. It tells BOS9 (recommendation surface renders over work items), BOS4 (decisions reference work items), and BOS5 (outcomes anchor to work items) exactly what a work item IS and how its lifecycle runs — without rebuilding Jira/Linear. Decisions and model only — NO runtime, NO store engine, NO UI, NO edits to voss/, apps/, or PROTOCOL.md.

Output: `.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md`
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/BOS8-team-project-and-work-model/BOS8-CONTEXT.md
@.planning/phases/BOS3-engineering-event-schema/BOS3-CONTEXT.md
@.planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-CONTEXT.md
@.planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md
@.planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-CONTEXT.md
</context>

<notes>
- The six LOCKED decisions D-01..D-06 in BOS8-CONTEXT.md are the spine of this deliverable. EXPRESS them; do not re-decide them.
- Established BOS docs-first convention: the deliverable artifact lives inside the phase directory and is a markdown spec (cf. BOS7-RESPONSIBILITY-MAP.md, BOS3 event schema contract). Use `BOS8-WORK-MODEL-SPEC.md` in this phase dir.
- BOS3 already names task/session/swarm/file/review/CI/validation/deploy/incident as event categories — BOS8 must NOT re-define them; it projects over them (D-01) and reuses their IDs/correlation model (D-06). Do not duplicate the event schema here.
- Per Claude's Discretion in BOS8-CONTEXT.md: a machine-readable schema (JSON Schema / Pydantic) for the entity shapes + lifecycle enum is encouraged alongside prose+tables, mirroring BOS3/BOS4. Embed it as a fenced schema block inside the spec deliverable — this is acceptable in the deliverable doc itself (it is the artifact). It is NOT permitted inside <action> below.
- The work↔service many-to-many is an OPEN CHECK (D-06): the spec must evaluate whether BOS3 correlation linkage suffices and either justify reuse or flag the gap — it must NOT pre-build a typed edge table.
- HARD INVARIANT (assert in every task acceptance): no edits to voss/, apps/, or .planning/PROTOCOL.md. The only file written is BOS8-WORK-MODEL-SPEC.md.
</notes>

<tasks>

<task type="auto">
  <name>Task 1: Scaffold the spec + write the entity tier model (8 entities) and projection invariant</name>
  <files>.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md</files>
  <read_first>
    - .planning/phases/BOS8-team-project-and-work-model/BOS8-CONTEXT.md (D-01 projection invariant; D-02 registration events; D-04 tiered coverage + agent-run dual-role note; Claude's Discretion on schema format)
    - .planning/phases/BOS3-engineering-event-schema/BOS3-CONTEXT.md (D-01 event categories already named; D-02 append-only/bitemporal/as-of; D-04 stable entity IDs + root correlation/causation — the substrate the projection sits on)
    - .planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md (the `actor` model that the engineer + agent-run actors must align with)
    - .planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-CONTEXT.md (anti-surveillance / no individual ranking; tenant=team — the agent-run dual role and engineer actor must stay compatible)
  </read_first>
  <action>
    Create `.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md`. Begin with a title (`# BOS8: Work Model Spec`), a one-line statement that this is the BOS-WORK-01/02/03 logical work/entity contract, and a short "How to read this" note (this spec defines a logical read model over BOS3 events; it is NOT a runtime, store engine, or PM suite; it places semantics, downstream phases design surfaces).

    Then write `## Projection Invariant` stating D-01 as an INVARIANT, not a default. Required load-bearing claims: the work model is a read model / projection derived from BOS3's append-only event log; there is NO separate mutable authoritative entity store; any work item's state is reconstructable as-of any time from BOS3 events; lifecycle transitions are DRIVEN BY events, never by mutating an entity record. Use the word "invariant" and the literal phrase "no mutable" (or "no separate mutable") store. Name the two rejected alternatives (authoritative mutable entity store; hybrid store) so the placement traces to D-01.

    Then write `## Entity Tier Model` (this exact heading) encoding D-04 as a markdown table. Rows = all 8 entities in this order: team, project, task, PR, service, incident, agent-run, engineer. Columns: `Entity` | `Tier` | `Has lifecycle?` | `Notes`. Tier values are exactly one of: `work`, `actor`, `reference`. Assign: task/PR/incident/agent-run = `work` (carry the canonical lifecycle, yes); engineer = `actor` (no lifecycle, identity ref); team/project/service = `reference` (no lifecycle, lightweight identity + attributes). agent-run must be marked as DUAL in its Notes cell (both work and actor) and cross-reference the dedicated reconciliation subsection.

    Directly under the table add `### agent-run dual role` resolving D-04's trickiest point: agent-run is a WORK item (it has a lifecycle — a run starts, executes, completes/fails) AND an ACTOR (it performs work on other items). State how both facets relate without double-counting: as a work item it carries the canonical lifecycle and is the subject of intake/outcomes; as an actor it maps to the BOS4 `actor` concept and acts on OTHER work items. Assert BOS6 compatibility explicitly: agent-run / engineer actors must NOT power a per-individual leaderboard or ranking surface (no individual ranking; tenant=team). Name the rejected alternatives (all-8-full-lifecycle = Jira-shaped; task-only-now-rest-stubs = under-specifies BOS-WORK-01).

    Then add `### Registration Events` encoding D-02: reference + actor entities with no natural observed activity (team, project, engineer, service) enter via registration/upsert event types (e.g. `project.registered`, `engineer.identified`) flowing through the SAME append-only log — one substrate, projection-consistent, NOT side config/reference tables. Name the rejected alternatives (plain config/seed tables = two substrates; defer all identity to BOS12). You MAY include a machine-readable schema sketch (JSON Schema or Pydantic) for entity shapes + tiers in this deliverable doc per Claude's Discretion.

    Do NOT touch voss/, apps/, or PROTOCOL.md. Write only BOS8-WORK-MODEL-SPEC.md.
  </action>
  <verify>
    <automated>SPEC=.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md; test -f "$SPEC" && grep -q "## Entity Tier Model" "$SPEC" && grep -q "## Projection Invariant" "$SPEC"</automated>
    <automated>SPEC=.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md; for e in team project task PR service incident agent-run engineer; do grep -qi "$e" "$SPEC" || { echo "MISSING entity: $e"; exit 1; }; done</automated>
    <automated>SPEC=.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md; grep -qi "invariant" "$SPEC" && grep -Eqi "no (separate )?mutable" "$SPEC"</automated>
    <automated>SPEC=.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md; grep -qi "dual" "$SPEC" && grep -Eqi "no individual ranking|leaderboard" "$SPEC" && grep -qi "registration" "$SPEC"</automated>
    <automated>git diff --quiet voss/ apps/ .planning/PROTOCOL.md && echo "protected paths untouched"</automated>
  </verify>
  <acceptance_criteria>
    - BOS8-WORK-MODEL-SPEC.md exists with a `## Projection Invariant` and a `## Entity Tier Model` heading.
    - The Entity Tier Model table has rows for all 8 entities (team, project, task, PR, service, incident, agent-run, engineer) and assigns each a tier of exactly work / actor / reference, with work items marked as having the lifecycle and actor/reference as having none (D-04).
    - Projection Invariant uses the word "invariant" and states there is no (separate) mutable entity store + state is reconstructable as-of any time (D-01); names the two rejected alternatives.
    - A `### agent-run dual role` subsection reconciles work + actor facets, maps the actor facet to BOS4 `actor`, and asserts BOS6 no-individual-ranking compatibility (D-04).
    - A `### Registration Events` subsection states team/project/engineer/service enter via registration/upsert events on the same append-only log, not side config tables (D-02).
    - `git diff --quiet voss/ apps/ .planning/PROTOCOL.md` passes.
  </acceptance_criteria>
  <done>The spec is scaffolded with the projection invariant (D-01), the 8-entity tier model (D-04), the agent-run dual-role reconciliation (D-04 + BOS4/BOS6), and the registration-events model (D-02), all grep-traceable and with no protected-path edits.</done>
</task>

<task type="auto">
  <name>Task 2: Write the canonical task lifecycle state machine + work intake model</name>
  <files>.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md</files>
  <read_first>
    - .planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md (the entity tier model written in Task 1 — append below it, do not rewrite)
    - .planning/phases/BOS8-team-project-and-work-model/BOS8-CONTEXT.md (D-03 canonical lifecycle + anti-Jira guardrail; D-05 intake = auto-from-harness + manual-as-event; discretion on exact state names/guards/off-path states)
    - .planning/phases/BOS3-engineering-event-schema/BOS3-CONTEXT.md (D-02 outcomes-as-later-events; the lifecycle is the spine outcomes accumulate over; events drive transitions)
    - .planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-CONTEXT.md (D-03/D-05 — outcomes append over the entity lifecycle; lifecycle must be rich enough to drive later review-depth/validation-depth recommendations)
  </read_first>
  <action>
    Append `## Canonical Task Lifecycle` to BOS8-WORK-MODEL-SPEC.md (below Task 1 content; do not edit it), encoding D-03. State that ONE small state machine governs all WORK-tier items (the "no Jira" guardrail) and that other tiers reference it rather than carrying their own. Provide the ordered main-path state list exactly: intake -> triaged -> assigned -> in_progress -> in_review -> validated -> done. Provide the off-path states: blocked and abandoned (and state which states they are reachable from / return to). Render the machine as BOTH a state-list/transition table AND a short text/ASCII transition diagram showing the main path. State that transitions are DRIVEN BY BOS3 events (consistent with the D-01 projection invariant), not by mutating a status field. State the anti-overbuild line: this is a single lean state machine sufficient to drive later review-depth / validation-depth recommendations, NOT a per-status PM workflow engine. Name the rejected alternatives (per-entity state machines = PM-suite-shaped; minimal open/active/closed enum = too thin). You MAY include a machine-readable enum (JSON Schema / Pydantic) for the lifecycle states in this deliverable.

    Then append `## Work Intake` encoding D-05. State the two v0.2 intake paths: (a) AUTO-DERIVED from the harness sessions / swarm tasks Voss emits today — observed events project into work items (cite swarm task ownership/assignment/completion + session events as the first auto-intake sources); (b) MANUAL CREATION — which, under the projection invariant (D-01), is itself a creation EVENT (e.g. `task.created`) so it stays projection-consistent and is NOT modeled as a mutable insert. State explicitly that external Git/PM/CI intake is a RESERVED BOS12 source — slot only, not built here. Name the rejected alternatives (auto-from-harness-only = can't represent un-routed work; manual-first/tracker-shaped = PM-suite-shaped). Use the literal phrase "creation event" for manual intake and reference BOS12 for the external slot.

    Do NOT touch voss/, apps/, or PROTOCOL.md.
  </action>
  <verify>
    <automated>SPEC=.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md; grep -q "## Canonical Task Lifecycle" "$SPEC" && grep -q "## Work Intake" "$SPEC"</automated>
    <automated>SPEC=.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md; for s in intake triaged assigned in_progress in_review validated done blocked abandoned; do grep -qi "$s" "$SPEC" || { echo "MISSING lifecycle state: $s"; exit 1; }; done</automated>
    <automated>SPEC=.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md; grep -Eqi "creation event" "$SPEC" && grep -qi "BOS12" "$SPEC" && grep -Eqi "swarm|session" "$SPEC"</automated>
    <automated>SPEC=.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md; grep -Eqi "no[t]? .*(PM|Jira)|anti-?(jira|pm)|not a .*workflow engine" "$SPEC"</automated>
    <automated>git diff --quiet voss/ apps/ .planning/PROTOCOL.md && echo "protected paths untouched"</automated>
  </verify>
  <acceptance_criteria>
    - Doc contains `## Canonical Task Lifecycle` with all main-path states (intake, triaged, assigned, in_progress, in_review, validated, done) AND both off-path states (blocked, abandoned), rendered as a transition table + a transition diagram (D-03).
    - The lifecycle section states transitions are event-driven (consistent with D-01) and states the anti-PM-suite guardrail + names the rejected alternatives (D-03).
    - Doc contains `## Work Intake` with both paths: auto-derived from harness sessions/swarm tasks, and manual creation modeled as a "creation event" (not a mutation); external intake reserved to BOS12 (D-05).
    - `git diff --quiet voss/ apps/ .planning/PROTOCOL.md` passes.
  </acceptance_criteria>
  <done>The canonical lifecycle state machine (D-03) and the two-path work intake model (D-05) are appended to the spec, with all states grep-traceable, manual intake stated as a creation event, the BOS12 slot reserved, and no protected-path edits.</done>
</task>

<task type="auto">
  <name>Task 3: Write the linking model (BOS3/BOS5 reuse) + requirement-coverage map + final verification</name>
  <files>.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md</files>
  <read_first>
    - .planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md (the entity model + lifecycle + intake from Tasks 1-2 — append below; do not rewrite)
    - .planning/phases/BOS8-team-project-and-work-model/BOS8-CONTEXT.md (D-06 linking reuse + work<->service open check; requirement->decision mapping in <decisions>; deferred ideas to NOT include)
    - .planning/phases/BOS3-engineering-event-schema/BOS3-CONTEXT.md (D-04 root correlation/trace id + parent/causation refs — the link substrate to name semantics over)
    - .planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-CONTEXT.md (D-03 entity-anchored outcome joins — the outcome link substrate to reuse)
    - .planning/REQUIREMENTS.md (lines 40-42 — BOS-WORK-01/02/03 exact wording for the coverage map)
  </read_first>
  <action>
    Append `## Linking Model` to BOS8-WORK-MODEL-SPEC.md encoding D-06. State that work items connect to sessions, swarm tasks, files, reviews, and validations via BOS3's EXISTING root correlation/trace id + parent/causation refs (BOS3 D-04), and to outcomes via BOS5's entity-anchored outcome joins (BOS5 D-03). State explicitly that BOS8 NAMES the link SEMANTICS over what BOS3/BOS5 already provide and invents NO new link primitive / association table. Provide a short table mapping each connection target (session, swarm task, file, review, validation, outcome) to the existing BOS3/BOS5 mechanism it reuses. Name the rejected alternatives (new explicit work<->artifact link tables = duplicates BOS3 lineage; hybrid extra typed edges).

    Then add `### Open check: work<->service` resolving D-06's flagged open question: evaluate whether the BOS3 correlation/causation linkage is sufficient to express the work<->service relationship (potentially many-to-many). EITHER justify that correlation lineage suffices (preferred — no new edge) OR explicitly flag it as a gap for a future typed edge — but do NOT pre-build a typed edge table here. State the decision and its rationale.

    Then append `## Requirement Coverage` mapping each requirement to the section that satisfies it: BOS-WORK-01 (the 8 entities) -> Entity Tier Model + Registration Events; BOS-WORK-02 (intake + lifecycle without a full PM suite) -> Canonical Task Lifecycle + Work Intake; BOS-WORK-03 (connections to sessions/swarm/files/reviews/validations/outcomes) -> Linking Model. Cite each requirement ID literally.

    Then run the full structural verification (automated checks below) over the completed spec to confirm all six decisions D-01..D-06 are traceable and no protected paths were touched. Confirm NO deferred ideas leaked in (no PM-suite workflow features, no governance policy rules, no outcome taxonomy, no external ingestion mechanics, no physical store engine).

    Do NOT touch voss/, apps/, or PROTOCOL.md.
  </action>
  <verify>
    <automated>SPEC=.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md; grep -q "## Linking Model" "$SPEC" && grep -q "## Requirement Coverage" "$SPEC"</automated>
    <automated>SPEC=.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md; for r in BOS-WORK-01 BOS-WORK-02 BOS-WORK-03; do grep -q "$r" "$SPEC" || { echo "MISSING requirement: $r"; exit 1; }; done</automated>
    <automated>SPEC=.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md; grep -Eqi "correlation|causation" "$SPEC" && grep -Eqi "outcome join|entity-anchored" "$SPEC" && grep -Eqi "no new link|invent[s]? no|without .*new" "$SPEC"</automated>
    <automated>SPEC=.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md; grep -Eqi "work.*service|service.*work" "$SPEC"</automated>
    <automated>SPEC=.planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md; lines=$(grep -vc '^[[:space:]]*$' "$SPEC"); [ "$lines" -ge 120 ] || { echo "spec too short: $lines non-blank lines (<120)"; exit 1; }</automated>
    <automated>git diff --quiet voss/ apps/ .planning/PROTOCOL.md && echo "protected paths untouched"</automated>
  </verify>
  <acceptance_criteria>
    - Doc contains `## Linking Model` reusing BOS3 correlation/causation refs (for session/swarm/file/review/validation) and BOS5 entity-anchored outcome joins (for outcomes), with an explicit "no new link primitive" statement and a per-target mapping table (D-06).
    - Doc contains a `### Open check: work<->service` subsection that either justifies correlation-lineage reuse or flags a future typed edge — without pre-building one (D-06).
    - Doc contains `## Requirement Coverage` citing BOS-WORK-01, BOS-WORK-02, BOS-WORK-03 each mapped to its satisfying section.
    - The completed spec is at least 120 non-blank lines and all six decisions D-01..D-06 are traceable via the Task 1/2/3 grep checks.
    - No deferred ideas (PM-suite workflow, governance policy, outcome taxonomy, external ingestion mechanics, physical store engine) are introduced.
    - `git diff --quiet voss/ apps/ .planning/PROTOCOL.md` passes.
  </acceptance_criteria>
  <done>The linking model (D-06) + work<->service open-check resolution + requirement-coverage map are appended; the full spec passes structural verification (all sections present, >=120 non-blank lines, all 6 decisions traceable, no deferred-idea leakage, protected paths untouched).</done>
</task>

</tasks>

<verification>
Phase-level checks (run after all tasks):
- `test -f .planning/phases/BOS8-team-project-and-work-model/BOS8-WORK-MODEL-SPEC.md`
- All 8 entities present and tiered: `## Entity Tier Model` heading + each of team/project/task/PR/service/incident/agent-run/engineer grep-hits
- Projection invariant present: `grep -qi invariant <spec>` and `grep -Eqi "no (separate )?mutable" <spec>`
- Canonical lifecycle present: all of intake/triaged/assigned/in_progress/in_review/validated/done/blocked/abandoned grep-hit
- Intake present: "creation event" + BOS12 + swarm/session grep-hit
- Linking present: correlation/causation + outcome join + "no new link" grep-hit; work<->service open check present
- Requirement coverage: BOS-WORK-01, BOS-WORK-02, BOS-WORK-03 all grep-hit
- Doc >=120 non-blank lines
- Protected paths untouched: `git diff --quiet voss/ apps/ .planning/PROTOCOL.md`
</verification>

<success_criteria>
- BOS8-WORK-MODEL-SPEC.md exists in the phase directory and is the single deliverable for BOS-WORK-01/02/03.
- The entity tier model unambiguously assigns all 8 entities to work/actor/reference tiers, with only work items carrying the lifecycle and agent-run's dual role reconciled against BOS4 actor + BOS6 anti-surveillance (D-04).
- The projection invariant (D-01) and registration-events model (D-02) are stated as the substrate, with no mutable entity store.
- The canonical task lifecycle (D-03) is one lean event-driven state machine with the named states + off-path states + anti-PM-suite guardrail.
- The work intake model (D-05) defines auto-from-harness + manual-as-creation-event, reserving external intake to BOS12.
- The linking model (D-06) reuses BOS3 correlation/causation + BOS5 outcome joins with no new primitive, and resolves the work<->service open check.
- No edits to voss/, apps/, or PROTOCOL.md; no deferred ideas leak in.
</success_criteria>

<output>
Create `.planning/phases/BOS8-team-project-and-work-model/BOS8-01-SUMMARY.md` when done.
</output>
