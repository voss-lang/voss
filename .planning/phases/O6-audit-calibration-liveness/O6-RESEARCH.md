# Phase O6 Research: Audit Product + Calibration + Liveness Hardening

**Date:** 2026-05-20
**Mode:** Inline research because local GSD agents are not installed.
**Confidence:** Medium-high for plan shape; execution remains blocked on O1-O5 shipped interfaces.

## Inputs Read

- `.planning/ROADMAP.md` Phase O6 section.
- `.planning/ORCHESTRATION-PLAN.md` invariants, residual-risk register, and O-phase sequencing.
- `.planning/phases/O6-audit-calibration-liveness/O6-CONTEXT.md`.
- O1-O5 context, research, patterns, and available plan artifacts.
- Live `voss/harness/session_tree.py` and current harness session/redaction constraints.

## Derived Requirements

O6 has no `O6-SPEC.md` yet. These requirement IDs are derived from the locked roadmap/context and must be reconciled if a formal SPEC is later authored.

| ID | Requirement |
|---|---|
| OAUD-01 | Add a substrate preflight that verifies O1-O5 audit inputs exist before O6 execution proceeds. |
| OAUD-02 | Load session-tree audit data without mutating `.voss/sessions/` or `RunRecord` / `SessionRecord` schemas. |
| OAUD-03 | Produce a human review surface centered on the session tree, killed/re-scoped cards, and routing rationale. |
| OAUD-04 | Block approval until killed-card, misroute/routing, calibration, and liveness sections are explicitly acknowledged. |
| OAUD-05 | Compute reviewer calibration telemetry: B verdict vs A verification, slop rejection, disagreement, and sampled human spot-audit queue. |
| OAUD-06 | Surface liveness: reserve usage, timeout-to-Blocked paths, terminal completeness, and stranded-node risks. |
| OAUD-07 | Close Leak-6 by either implementing a bounded semantic-memory poisoning mitigation check or recording an accepted-gap decision. |
| OAUD-08 | Provide deterministic fixtures and acceptance tests that exercise killed card, rescope, misroute, reviewer disagreement, timeout, and Leak-6 outcomes. |

## Findings

### 1. O6 Is Downstream of Planned Interfaces, Not Live Interfaces

Live source currently has the O1 session-tree substrate (`voss/harness/session_tree.py`) but not the O3/O4/O5 board, reviewer, or EM runtime modules that O6 expects to audit. O6 plans must therefore start with a blocking preflight rather than assuming the O-track is executable.

Execution implication: O6 can be planned now, but O6 execution must stop until O1-O5 interfaces are present or provide compatible stubs in tests.

### 2. The Audit Layer Should Be Read-only by Default

O1 intentionally keeps `SessionTreeNode` separate from `RunRecord` and `SessionRecord`. O6 should preserve that boundary. Audit loaders should hydrate from persisted node files and optional O3-O5 event payloads, then normalize into O6-owned snapshot dataclasses.

Execution implication: no additive audit fields on `RunRecord` or `SessionRecord`; sign-off output belongs under an audit-specific path such as `.voss/audits/<root_id>/`.

### 3. Exported Artifacts Are the Lowest-risk First Review Surface

O6 context leaves TUI panel vs exported artifact vs both to planner discretion. A Markdown + JSON export is the lowest-risk first implementation because it is stable, easy to test, and can later feed M9 TUI or A-phase ADE surfaces.

Execution implication: make exported Markdown + machine JSON mandatory; keep TUI/ADE renderer hooks optional and out of O6 acceptance unless the live app surface already exists.

### 4. Sign-off Must Be Structural, Not Copy

The residual-risk register names overloaded human sign-off as the biggest systemic risk. A report that merely contains killed cards and misroutes is insufficient. Approval must be unavailable until acknowledgements are captured for all risk sections.

Execution implication: implement a pure `AuditSignoffGate` with named acknowledgement buckets and tests that prove missing buckets block approval.

### 5. Calibration Needs Both Aggregate Counts and Human Sampling

The O4 split only helps if O6 makes divergence visible. O6 should compute:

- A verification vs B verdict agreement/disagreement.
- B blocks where A passed.
- A failures later contradicted by B.
- slop-rejection rate.
- sampled spot-audit candidates, with deterministic selection for tests.

Execution implication: keep the sampling algorithm deterministic by default (`root_id`, node id, and sorted card id order) so tests do not depend on randomness.

### 6. Liveness Is a Reportable Invariant

O1/O3 promise reserved drain budget and timeout-to-Blocked escape. O6 should not re-implement budget enforcement. It should detect whether terminal records make the liveness story inspectable.

Execution implication: report `ok`, `warning`, or `blocked` per node/card based on terminal state, timeout transition, reserve availability, and open-node status.

### 7. Leak-6 Should Be an Explicit Closure Item

The orchestration plan explicitly allows Leak-6 to remain an accepted gap if mitigation proves out of scope. The dangerous outcome is silent omission.

Execution implication: O6 should add an explicit Leak-6 assessment section. If no standup-to-memory writer exists in the O1-O5 substrate, the correct O6 behavior is to record `accepted_gap` with evidence and make sign-off acknowledge it.

## Recommended Plan Shape

Six serial/partially parallel plans:

1. O6-01 preflight and RED acceptance fixtures.
2. O6-02 audit snapshot model and loader.
3. O6-03 report/export review surface.
4. O6-04 calibration and liveness metrics.
5. O6-05 sign-off gate and acknowledgement persistence.
6. O6-06 Leak-6 closure plus end-to-end acceptance.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| O5 data shape changes before execution | O6 loader/tests drift | O6-01 freezes required inputs before implementation. |
| Audit report becomes another wall of text | Human sign-off degrades | O6-05 requires structured acknowledgements before approve. |
| O6 mutates core session schemas | Redaction regression | O6-02 tests schema isolation and writes audit state separately. |
| LLM-judging-LLM telemetry gets treated as truth | False confidence | Report calibration as drift signal, not correctness oracle. |
| Leak-6 silently skipped | Residual register remains open | O6-06 forces mitigate-or-accepted-gap output. |
