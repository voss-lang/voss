# Phase V12: Safety & Factory Fallbacks — Specification

**Created:** 2026-06-06
**Ambiguity score:** 0.142 (gate: <= 0.20)
**Requirements:** 7 locked

## Goal

Add a project-local safety policy layer that detects dangerous or factory-only operations, routes them through explicit human confirmation or fixed named runbooks, and records every factory fallback in audit without changing the normal autonomous path for ordinary work.

## Background

The harness already has safety primitives, but no deliberate factory tier:
- `PermissionGate` gates tools by mode, project rules, mutability, network use, and optional interactive prompts.
- `ToolEntry` records tool metadata (`is_mutating`, group, network flag, scope requirements, audit behavior).
- `RunRecorder` records capability invocations, and V9 audit models consume persisted run evidence.
- The EM cage bounds autonomous orchestration through `EMBoardHandle`, role gates, and filtered toolsets.

Missing today: no `factory-only` policy, no classification for irreversible/deploy/delete/migration/money/prod operations, no fixed runbook/fixed-pipeline route, no risk-summary confirmation with exact action text, no weak-model scaffold marker, and no audit field that says a strict factory fallback was used.

**Locked direction (interview):** V12 is policy + audit first. It protects both autonomous EM-dispatched work and normal harness tool invocations. Project policy lives in a new safety file such as `.voss/safety.yml`. Fixed runbooks are named deterministic procedures for dangerous operations; V12 does not build a general workflow DSL or real deployment/payment integrations.

## Requirements

1. **Explicit dangerous-action confirmation** (VSAFE-01): irreversible operations cannot run without an action-specific human confirmation.
   - Current: `PermissionGate` can prompt for mutating operations, but `auto_yes` and mode rules can approve broad classes of actions; prompts do not include a structured risk summary or exact command/action contract.
   - Target: operations classified as irreversible require explicit confirmation that includes risk summary + exact command/action, even when the outer harness is in `auto` mode or the operation is requested by the autonomous EM.
   - Acceptance: a classified irreversible action is denied unless the prompt response confirms that exact action; a non-matching or absent confirmation leaves the action unexecuted and audited as denied.

2. **Dangerous-operation factory routing** (VSAFE-02): deploy/delete/migration/money/prod operations use fixed named runbooks.
   - Current: tool calls are allowed/denied by tool metadata and project permission rules; there is no runbook registry or mandatory strict-procedure route for dangerous domains.
   - Target: safety policy rules classify deploy/delete/migration/money/prod operations and route them to a named factory runbook before execution; direct autonomous execution is rejected when no matching runbook exists.
   - Acceptance: policy-matched dangerous operations invoke or require their configured runbook; the same operation cannot execute directly from an EM plan or ordinary tool call path when the runbook requirement is present.

3. **Latency fixed-pipeline opt-in** (VSAFE-03): latency-critical operations can bypass deliberative autonomy through an explicit fixed-pipeline policy.
   - Current: no policy differentiates latency-critical operations from ordinary agent-planned work.
   - Target: safety policy supports an opt-in fixed-pipeline classification for named operations; those operations follow their deterministic pipeline and are marked as factory fallback rather than being planned freely by the agent.
   - Acceptance: a configured latency-critical operation is routed through the fixed pipeline and audit marks the route; the same operation remains ordinary when no policy rule marks it latency-critical.

4. **Weak-model scaffolds** (VSAFE-04): weaker model roles can be forced onto scaffolded procedures.
   - Current: role defaults and explicit team specs support model tiers and filtered toolsets, but they do not change execution mode based on weak/cheap/fast model risk.
   - Target: safety policy can require scaffolded procedure mode for configured roles or model tiers; scaffolded mode constrains the role to declared steps/checklists and records that constraint in audit.
   - Acceptance: a configured weak-model role receives only the scaffolded procedure path for matching operations; strong/unconfigured roles keep the normal autonomous path.

5. **Factory fallback audit marker** (VSAFE-05): every strict-procedure route is visible in run/audit output.
   - Current: `RunRecorder.observe_capability()` records capability invocations but has no factory fallback or runbook fields; V9 audit models have no strict-runbook marker.
   - Target: each factory fallback records operation classification, runbook/pipeline name, trigger rule, confirmation status, actor role, and final allow/deny/executed outcome in persisted audit evidence.
   - Acceptance: a run with a factory fallback exposes an audit entry naming strict runbook mode; a run without factory fallback has no false-positive factory marker.

6. **Project-local factory-only policy** (VSAFE-06): users can configure factory-only directories or operations.
   - Current: `.voss/permissions.yml` supports allow/ask/deny rules by tool/cmd/path, but no factory-only directory/operation semantics.
   - Target: a project-local safety policy file (default `.voss/safety.yml`) declares factory-only path globs, command/operation patterns, dangerous classifications, and associated runbook/pipeline names.
   - Acceptance: policy validation accepts well-formed factory-only path/operation rules and rejects malformed or unknown runbook references; matching paths/operations are forced through the factory route.

7. **Autonomous EM cannot execute dangerous actions alone** (VSAFE-07): EM dispatch is subject to the same safety policy as direct tool calls.
   - Current: EM board operations are caged, but dispatched worker tool calls rely on the role-derived `PermissionGate`; there is no separate factory safety overlay.
   - Target: EM-dispatched work and ordinary harness tool invocations share one safety decision path, so a dangerous action from a card/worker is blocked, confirmed, or runbook-routed exactly like the same action from a direct `voss do` tool call.
   - Acceptance: the same dangerous operation is denied or routed identically when requested through EM dispatch and when requested through the direct tool loop.

## Boundaries

**In scope:**
- Project-local safety policy file such as `.voss/safety.yml`.
- Safety classification for irreversible, deploy/delete/migration/money/prod, latency-critical, weak-model scaffold, and factory-only path/operation rules.
- Safety overlay on existing `PermissionGate`/tool invocation flow, covering EM-dispatched worker work and ordinary harness tool calls.
- Fixed named runbook/fixed-pipeline routing for configured dangerous operations.
- Human confirmation prompt contract: risk summary + exact command/action + explicit matching confirmation.
- Persisted audit evidence for every factory fallback.
- Tests proving direct and EM-dispatched dangerous operations share policy behavior.

**Out of scope:**
- A general workflow/pipeline DSL — V12 only needs named deterministic procedures sufficient to enforce safety routing.
- Real cloud deployment, database migration, payment, or production integrations — tests use deterministic local/stub operations.
- Rollback or revert semantics after rejection/failure — V12 blocks or records; it does not undo side effects.
- ADE UI for safety prompts/audit — V11/ADE consumes audit later.
- Rewriting the existing permissions system — V12 layers safety policy over the existing gate/tool metadata surface.
- Network/service policy beyond operations explicitly classified by safety rules.

## Constraints

- Safety policy must be additive over the existing `PermissionGate` and `ToolEntry` metadata; ordinary unclassified operations keep the current behavior.
- `auto_yes` cannot bypass explicit confirmation for classified irreversible actions.
- Factory fallback must not contaminate the normal autonomous path: only matching safety rules trigger strict procedure mode.
- EM cage invariants remain intact; V12 must not add EM APIs for mutating ceilings, budgets, roster, or gates.
- Audit additions must be backward-compatible: old run records without factory fields remain readable.
- No new third-party dependency unless planning proves the standard library/project stack cannot parse the selected safety file format.

## Acceptance Criteria

- [ ] `.voss/safety.yml` (or the final project-local safety policy name) loads and validates factory-only path/operation rules plus runbook/pipeline references; malformed rules fail with actionable diagnostics.
- [ ] A classified irreversible action requires explicit human confirmation containing risk summary + exact command/action; `auto_yes` does not bypass this requirement.
- [ ] Deploy/delete/migration/money/prod operations matched by safety policy cannot execute directly; they are routed to the configured fixed runbook or denied if no runbook is available.
- [ ] Latency-critical rules route configured operations through fixed pipelines and leave unconfigured operations on the normal autonomous path.
- [ ] Weak-model role/tier rules force matching operations through scaffolded procedure mode while strong/unconfigured roles keep normal behavior.
- [ ] Every factory fallback persists audit evidence with classification, trigger rule, runbook/pipeline name, actor role, confirmation status, and outcome.
- [ ] The same dangerous operation receives the same safety decision when requested through autonomous EM-dispatched work and through the direct harness tool loop.
- [ ] Existing permission, capability-audit, team-role, and EM cage tests remain green; old run records without factory fields still load.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                        |
|--------------------|-------|------|--------|--------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Policy + audit first, not full pipeline engine               |
| Boundary Clarity   | 0.86  | 0.70 | ✓      | DSL/integrations/rollback/ADE excluded                       |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Safety file, additive gate overlay, auto_yes cannot bypass   |
| Acceptance Criteria| 0.84  | 0.70 | ✓      | 8 pass/fail criteria across config, gates, audit, EM parity  |
| **Ambiguity**      | 0.142 | ≤0.20| ✓      |                                                              |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective       | Question summary                                  | Decision locked                                                        |
|-------|-------------------|--------------------------------------------------|------------------------------------------------------------------------|
| 0     | Researcher (scout)| What safety primitives exist today?              | PermissionGate, ToolEntry metadata, RunRecorder, and EM cage exist; no factory tier |
| 1     | Researcher        | What should V12 first deliver?                   | Policy + audit first; no full pipeline DSL                             |
| 1     | Boundary Keeper   | Which execution surfaces are protected?          | Both EM-dispatched work and ordinary harness tool invocations          |
| 1     | Simplifier        | Where does factory-only policy live?             | New project-local safety file such as `.voss/safety.yml`               |

---

*Phase: V12-safety-factory-fallbacks*
*Spec created: 2026-06-06*
*Next step: /gsd-discuss-phase V12 — implementation decisions (policy schema, classifier, runbook registry, confirmation prompt, audit shape)*
