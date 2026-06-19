---
phase: BOS6-privacy-governance-and-tenant-boundaries
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-GOVERNANCE-SPEC.md
autonomous: true
requirements: [BOS-GOV-01, BOS-GOV-02, BOS-GOV-03, BOS-GOV-04]

must_haves:
  truths:
    - "The spec defines the trust model: team-level reporting, the hard anti-surveillance bans, and the structural min-aggregation + no-cross-ranking rule (BOS-GOV-01)."
    - "The spec defines the four autonomy bands, the dual-scope kill-switch, and the gated-increase / immediate-decrease asymmetry (BOS-GOV-02)."
    - "The spec defines the three privacy tiers, private-by-default-and-local for code/prompts/sessions, the one-directional local->shared boundary, and team = isolation unit (BOS-GOV-03)."
    - "The spec defines all six guardrail dashboards each with a trip condition, and cites the BOS5/BOS15 scope boundary (BOS-GOV-04)."
    - "The spec surfaces N, retention/deletion, and kill-switch/autonomy RBAC as Open Questions, not decided answers."
    - "The spec reconciles the anti-surveillance rule with the BOS4 ledger `actor` field (stored != cross-reported)."
  artifacts:
    - path: ".planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-GOVERNANCE-SPEC.md"
      provides: "The BOS6 governance / trust contract covering BOS-GOV-01..04"
      contains: "## Open Questions"
  key_links:
    - from: "BOS6-GOVERNANCE-SPEC.md anti-surveillance section"
      to: "BOS4 decision-ledger actor field"
      via: "stored != cross-reported reconciliation (D-09)"
      pattern: "actor"
    - from: "BOS6-GOVERNANCE-SPEC.md guardrail section"
      to: "BOS5 reward/guardrail metrics and BOS15 eval gates"
      via: "explicit scope-boundary citation (D-11, D-03)"
      pattern: "BOS5|BOS15"
---

<objective>
Produce `BOS6-GOVERNANCE-SPEC.md`: the prose policy/trust contract that every later BOS recommendation surface (BOS9), policy (BOS13/14), and the eval phase (BOS15) must honor. It defines the trust model, anti-surveillance reporting rule, autonomy bands + kill-switch model, the three privacy/data-sensitivity tiers + tenant boundary, and the six guardrail dashboards.

Purpose: Governance is foundational, not bolted-on (PROJECT.md Key Decisions). This spec operationalizes the hard bans and the safety asymmetry so downstream phases inherit a stable trust contract.

Output: A single Markdown governance spec at the path above. NO code, NO enforcement implementation, NO schema definitions. Prose policy + boundaries only.

This is a docs-only phase. Final verification is human review against the locked CONTEXT decisions — there is no test command.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-CONTEXT.md
@.planning/REQUIREMENTS.md
@.planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md
@.planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-CONTEXT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write the four governance pillars (trust/anti-surveillance, autonomy/override, privacy/tenant, guardrails)</name>
  <files>.planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-GOVERNANCE-SPEC.md</files>
  <read_first>
    - .planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-CONTEXT.md (the locked decisions D-01..D-11; authoritative)
    - .planning/PROJECT.md (Constraints §Trust + §Safety; Out of Scope — the hard bans)
    - .planning/REQUIREMENTS.md (BOS-GOV-01..04, lines ~77-80)
    - .planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md (D-05/D-06 the `actor`/verdict fields that D-09 reconciles)
    - .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-CONTEXT.md (D-04/D-05 SQLite->Postgres one-directional boundary the privacy tiers ride on)
    - the doc being written (BOS6-GOVERNANCE-SPEC.md) if it already exists
  </read_first>
  <action>
    Create BOS6-GOVERNANCE-SPEC.md with a title, a short scope/purpose preamble (governance is foundational; docs-only; the trust contract downstream BOS surfaces inherit), and these four required sections, each grounded in the cited decisions with the EXACT locked values.

    Section "Trust Model and Anti-Surveillance Reporting" (BOS-GOV-01, D-08/D-09): restate the hard bans verbatim in intent — no individual rankings, no raw activity scoring, no keystroke/productivity telemetry, no nudge-engagement optimization (per PROJECT.md Out of Scope + Constraints). Then state the STRUCTURAL guarantees: (a) minimum-aggregation floor — a team metric is NEVER reported for fewer than N contributors, k-anonymity-style; state N is an Open Question and that the rule holds regardless of N's value (do NOT pick a value for N); (b) no per-individual cross-comparison/ranking/leaderboard, ever; (c) self-view permitted — an individual MAY see their own data; (d) the "stored != cross-reported" principle. Reconcile explicitly with the BOS4 decision-ledger `actor` field: actor is stored on verdicts for audit/training only, never surfaced as individual ranking output.

    Section "Autonomy Bands and Kill-Switch" (BOS-GOV-02, D-01/D-02/D-03): name all four bands in order — `suggest_only` -> `approve_required` -> `auto_with_post_review` -> `full_auto` — and state each recommendation surface carries a current band. State the dual-scope kill-switch: a global kill-switch (halts all recommendation/auto action) AND a per-surface kill-switch, either dropping the affected surface(s) to a safe state (effectively suggest_only/off). State the asymmetry explicitly and as intentional: an autonomy INCREASE (moving to a higher band) is gated by (a) an offline-eval pass (owned by BOS15), (b) a guardrail check, and (c) explicit human approval; an autonomy DECREASE or kill is always immediate and unilateral. State the human-approval + override-logging expectation for every recommendation surface (consistent with PROJECT.md §Trust human override).

    Section "Privacy Tiers and Tenant Boundary" (BOS-GOV-03, D-04/D-05/D-06/D-07): name all three sensitivity tiers — `team_shareable` / `team_private` / `never_leaves_local`. State private-by-default: code, prompts, and agent-session transcripts default to the most-restrictive tier, stay local (SQLite per BOS2 D-04), and never cross to shared Postgres unless explicitly promoted; only derived metadata + decision/outcome records cross the local->shared boundary (one-directional projection, BOS2 D-05). State calendar/identity data = minimal, with cross-source identity resolution deferred to BOS12 (reference, do not define). State incident/deploy metadata = team-shareable (operational, not individual-attributing). State tenant = the team as the isolation unit; no cross-team / multi-tenant SaaS in v0.2.

    Section "Guardrail Dashboards" (BOS-GOV-04, D-10/D-11): enumerate all SIX guardrails — fatigue, fairness, escaped defects, incidents, autonomy creep, reward hacking — each with what it measures and a trip/alert condition (trip-condition phrasing is your discretion per D-10; the underlying metric is owned by BOS5, so reference it, do not redefine it). State the scope boundary explicitly: BOS6 owns the dashboard definition + trip conditions; it REFERENCES BOS5 for the underlying reward/guardrail metric definitions and does not redefine them; BOS15 owns the eval gates.

    Do NOT define: the BOS3 event schema, BOS5 reward/guardrail metric definitions, BOS15 eval-gate mechanics, or BOS12 identity resolution — reference them as boundaries only. Tables/matrices for the band transitions and tier->handling mapping are encouraged (layout is your discretion). Do NOT add the Open Questions section in this task — it is Task 2.
  </action>
  <acceptance_criteria>
    - BOS6-GOVERNANCE-SPEC.md exists.
    - Doc names all four autonomy bands: suggest_only, approve_required, auto_with_post_review, full_auto.
    - Doc states an autonomy increase requires offline-eval pass + guardrail check + human approval, and that decrease/kill is immediate and unilateral.
    - Doc states both a global kill-switch and a per-surface kill-switch.
    - Doc names all three privacy tiers: team_shareable, team_private, never_leaves_local.
    - Doc states code/prompts/agent-session transcripts are private-by-default, stay local, and never cross to shared Postgres unless explicitly promoted.
    - Doc states the min-aggregation floor (no metric reported for fewer than N contributors) and that self-view is permitted while cross-individual ranking is never allowed.
    - Doc reconciles the rule with the BOS4 `actor` field (stored != cross-reported).
    - Doc enumerates all six guardrails (fatigue, fairness, escaped defects, incidents, autonomy creep, reward hacking), each with a trip/alert condition.
    - Doc restates the hard bans: no individual rankings, no raw activity scoring, no nudge-engagement optimization.
    - Doc states tenant = the team and no cross-team/multi-tenant in v0.2.
  </acceptance_criteria>
  <verify>
    <human-check>Reviewer confirms all four pillar sections are present and match the locked CONTEXT decisions (D-01..D-11) and the exact locked values (4 bands, 3 tiers, 6 guardrails, min-aggregation rule, gated-increase asymmetry). No test command — docs-only phase.</human-check>
  </verify>
  <done>BOS6-GOVERNANCE-SPEC.md contains the four pillar sections with all exact locked values; acceptance criteria above all hold on read-back.</done>
</task>

<task type="auto">
  <name>Task 2: Add Open Questions, cross-phase boundary citations, and a downstream-consumer note</name>
  <files>.planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-GOVERNANCE-SPEC.md</files>
  <read_first>
    - .planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-CONTEXT.md (the `<deferred>` block: N, retention/deletion, RBAC; plus D-11/D-03 boundaries)
    - .planning/PROJECT.md (Out of Scope — the v0.2 boundaries: no multi-tenant, no autonomy increase without eval)
    - the doc being written (BOS6-GOVERNANCE-SPEC.md, drafted in Task 1)
  </read_first>
  <action>
    Append to BOS6-GOVERNANCE-SPEC.md.

    Add a section titled exactly `## Open Questions` that lists the THREE flagged-undecided items as open questions, each stated as undecided with no invented answer: (1) the value of N for the minimum-aggregation floor (the rule is structural regardless of N); (2) the data retention / deletion policy — how long sessions, prompts, and decision records are kept, and right-to-delete; (3) RBAC — who may flip the global or per-surface kill-switch and who may change a surface's autonomy band (likely BOS7 web control plane or a later phase). Do NOT decide any of these; state them as open.

    Add a section "Cross-Phase Boundaries" that explicitly cites, as referenced-not-owned: BOS3 (engineering event schema — BOS6 classifies sensitivity, BOS3 defines the event entities), BOS5 (reward/guardrail metric definitions the dashboards reference, D-11), BOS15 (offline-eval gate mechanics that gate autonomy increases, D-03), and BOS12 (cross-source identity resolution, D-06). State BOS6 does not define any of these.

    Add a short closing "Downstream Consumers" note: this contract is inherited by BOS9 (recommendation review surface), BOS13/BOS14 (policies), and BOS15 (eval); the existing PermissionGate/operator-gate substrate is the enforcement layer a future phase maps these bands onto — BOS6 is policy-only.
  </action>
  <acceptance_criteria>
    - Doc contains a section titled exactly `## Open Questions`.
    - The Open Questions section lists N (aggregation floor), data retention/deletion, and kill-switch/autonomy-band RBAC, each stated as undecided.
    - Doc does not assign a numeric value to N and does not decide retention or RBAC.
    - Doc cites BOS3, BOS5, BOS15, and BOS12 as referenced boundaries it does not define.
    - Doc states BOS6 owns the dashboard + trip conditions but references BOS5 metrics and BOS15 eval gates.
    - Doc names downstream consumers (BOS9 review surface, BOS13/14 policies, BOS15 eval) and states BOS6 is policy-only over the existing PermissionGate substrate.
  </acceptance_criteria>
  <verify>
    <human-check>Reviewer confirms the `## Open Questions` section lists exactly N, retention/deletion, and RBAC as undecided (no invented answers), and that BOS3/BOS5/BOS12/BOS15 appear only as referenced boundaries. No test command — docs-only phase.</human-check>
  </verify>
  <done>BOS6-GOVERNANCE-SPEC.md has the `## Open Questions`, Cross-Phase Boundaries, and Downstream Consumers sections; the three undecided items are surfaced as open, not answered.</done>
</task>

</tasks>

<verification>
This is a docs-only phase with no test command. Final verification is human review of BOS6-GOVERNANCE-SPEC.md against the locked BOS6-CONTEXT decisions:
- All 4 autonomy bands named (D-01); dual-scope kill-switch (D-02); gated-increase / immediate-decrease asymmetry (D-03).
- All 3 privacy tiers named (D-04); private-by-default-local for code/prompts/sessions (D-05); calendar/identity minimal + incident/deploy team-shareable (D-06); tenant = team, no cross-team (D-07).
- Min-aggregation floor with N as Open Question (D-08); no cross-ranking + self-view + stored!=cross-reported reconciled with BOS4 actor (D-09).
- All 6 guardrails each with a trip condition (D-10); BOS5/BOS15 scope boundary cited (D-11).
- `## Open Questions` lists N, retention, RBAC — undecided.
- BOS3/BOS5/BOS12/BOS15 referenced as boundaries, not defined.
</verification>

<success_criteria>
- BOS6-GOVERNANCE-SPEC.md exists in the BOS6 phase directory.
- All four governance pillars (BOS-GOV-01..04) are covered with the exact locked values.
- The three flagged-undecided items appear under `## Open Questions`, not silently decided.
- Deferred/cross-phase items (BOS3 event schema, BOS5 metrics, BOS15 eval gates, BOS12 identity) are referenced as boundaries, never defined.
- No code, no schema, no enforcement implementation.
</success_criteria>

<output>
Create `.planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-01-SUMMARY.md` when done.
</output>
