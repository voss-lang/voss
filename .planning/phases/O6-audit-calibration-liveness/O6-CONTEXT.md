# Phase O6: Audit Product + Calibration + Liveness Hardening - Context

**Gathered:** 2026-05-17
**Status:** Planned inline on 2026-05-20 from roadmap/context because `O6-SPEC.md` is not present; reconcile if a formal SPEC is later authored.
**Source of truth:** `.planning/ORCHESTRATION-PLAN.md` (§4 invariants, §7 residual register, §8 decisions)

<domain>
## Phase Boundary

O6 makes "audit the cage" real: the human review product + the monitoring that keeps the cage honest + the residual-risk closure pass.

**In scope:**
- **Session-tree as the primary human review surface** (invariant #7) — the recorder is the product, not telemetry. Built on O1's tree.
- **Killed / re-scoped cards + routing rationale foregrounded first-class** (decisions #17, #20) — human sees what the EM avoided, not just what it shipped.
- **Reviewer calibration telemetry** (decision #16): B-verdict vs. A-verification (independent post-split), + sampled human **slop-rejection** spot-audit (residual #5).
- **Liveness surfacing**: reserve / timeout primitives from O1/O3 made visible at sign-off.
- **Sign-off forcing function** (residual #3 mitigation): mandatory killed-card + misroute diff presented *before* the approve action is available — defeats rubber-stamp.
- **Leak-6 mitigation candidate** (residual #1): `standup → semantic.memory` poisoning — expiry/correction path, OR an explicit documented accepted-gap decision.

**Out of scope:** Building the EM/board/reviewers (O1–O5). O6 surfaces, monitors, and closes — it does not add orchestration behavior.
</domain>

<decisions>
## Locked Decisions (from ORCHESTRATION-PLAN.md §8)

- **Calibration telemetry + sampled human spot-audit** (decision #16) — the cage's single point of failure (the judge) must have a drift signal; the A/B split (O4) makes the B-vs-A comparison genuinely independent.
- **Killed/re-scoped cards = first-class audit surface** (decision #17) — avoidance behavior is the most important signal.
- **Reserve + timeout** (decision #18) — primitives live in O1/O3; O6 surfaces them at the human boundary.

## Residual-risk closure pass (ORCHESTRATION-PLAN.md §7)
O6 explicitly closes **or documents as accepted**:
1. Leak 6 (`semantic.memory` poisoning) — mitigate or accept-and-document. Out-of-scope is a valid outcome if recorded.
2. Residual #3 (overloaded sign-off) — the forcing function is O6's primary mitigation.
3. Residual #5 (LLM-judging-LLM slop) — covered by slop-rejection-rate telemetry, not a structural fix.

### Claude's discretion (resolve at SPEC/plan)
- Review-surface presentation (TUI panel vs. exported artifact vs. both — relate to M9 TUI / A-phase ADE surfaces).
- Calibration sampling cadence + spot-audit selection policy.
- Whether Leak-6 mitigation is in O6 scope or a deferred documented gap.
</decisions>

## Dependencies
- Depends on: O5 (and O1–O4 transitively).
- Blocks: none (terminal O-phase). Closes the residual-risk register.
