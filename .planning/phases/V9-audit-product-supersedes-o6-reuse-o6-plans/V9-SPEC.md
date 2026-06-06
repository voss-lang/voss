# Phase V9: Audit Product (supersedes O6) — Specification

**Created:** 2026-06-06
**Ambiguity score:** 0.137 (gate: ≤ 0.20)
**Requirements:** 9 locked (greenfield; O6 plans → reference only)

## Goal

Make the audit trail the primary trust product: ship `voss audit <run_id>` that renders a complete, deterministic, source-tagged audit (idea → principles → team → budget → scope → board → reviews → lineage → residual risk) from persisted run data, export it as Markdown + JSON, add a hard sign-off forcing function, and close the O6 residual register (calibration telemetry + Leak-6) — read-only, without touching the persistence schemas it consumes.

## Background

O6 is **planned but not executed** (6 `O6-*-PLAN.md` + `O6-CONTEXT.md`, **no SUMMARY**; no audit code; no `voss audit`). So V9 is a greenfield build of the read/aggregate/present layer over everything V2–V7 persist:
- principles (V2 `.voss/principles.yml` / active set), team config (V3), session-tree nodes + budget envelopes + scope/role + rejected raises (V4), board cards + transitions + WIP (V5), Reviewer-A verification + Reviewer-B verdicts (V6 review sidecars), `run-final.json` + kill/rescope lineage + routing rationale (V7).

The persistence contracts those phases define changed under the V-track, so the existing O6 plans are treated as **reference only** — V9 re-plans fresh. **Locked direction (interview):** re-plan fresh (O6 superseded, plans not reused); V9 ships the audit data model + Markdown/JSON export + `voss audit` CLI, with the ADE navigable render deferred to V11; V9 absorbs all of O6 (calibration telemetry + Leak-6); hard sign-off gate; source-tagged claims-vs-evidence; Leak-6 mitigate-or-accept.

## Requirements

1. **`voss audit` CLI** (VAUD-01): a run is auditable from the CLI, deterministically.
   - Current: no `audit` command; no audit assembly.
   - Target: `voss audit <run_id>` (default latest) assembles a complete audit **read-only** from persisted data; deterministic (same persisted data → identical audit).
   - Acceptance: `voss audit` (no arg) renders the latest run and exits 0; `voss audit <run_id>` renders that run; unknown run exits non-zero with stderr; two runs on identical persisted data produce identical output.

2. **Audit content surface** (VAUD-02): the audit shows the full run.
   - Current: none.
   - Target: the audit includes original idea, active principles (V2), team config (V3), budget + scope, board timeline + cards, agent actions, diff summary, tests/evals, reviewer outputs, blocked/killed/rescoped items, evidence references, and final status — per PRD §9's section structure.
   - Acceptance: the audit contains each named section, populated from the corresponding persisted source; an empty/missing source renders an explicit "none" rather than crashing.

3. **Claims vs verified evidence** (VAUD-03): EM claims are distinguished from verification.
   - Current: none.
   - Target: each audit item is source-tagged — EM-authored claim vs independently-verified evidence (reviewer verdict / test or eval result / recorder event) — rendered in distinct sections; unsupported EM claims are flagged.
   - Acceptance: an EM claim with no backing reviewer/test evidence is flagged as unsupported; a verified item shows its evidence ref; the two are visually/structurally separated.

4. **Budget + scope accounting** (VAUD-04/05): per-node budget and scope events are shown.
   - Current: none.
   - Target: the audit shows budget allocation + consumption per session-tree node, and scope violations + denied attempts (rejected raises, scope-denials).
   - Acceptance: each node's envelope (limit/spent) appears; rejected budget raises and scope denials appear with their recorded reasons.

5. **Reviewers separate + lineage** (VAUD-06/07): independent review outputs and kill/rescope lineage.
   - Current: none.
   - Target: Reviewer-A and Reviewer-B outputs appear in separate sections; killed/rescoped card lineage (with routing rationale) is shown.
   - Acceptance: A and B outputs are in distinct sections; every killed/rescoped card appears with its lineage record + routing rationale.

6. **Markdown + JSON export** (VAUD-08): the audit is exportable.
   - Current: none.
   - Target: `voss audit` can export both a Markdown report and a machine-readable JSON document for a run.
   - Acceptance: both a valid Markdown report and a valid JSON document are produced for a run; the JSON round-trips the audit data.

7. **Residual-risk section + Leak-6** (VAUD-10): the audit names residual risk.
   - Current: none.
   - Target: the audit includes a residual-risk section; Leak-6 (semantic.memory digest poisoning) is either mitigated (an expiry/correction path on semantic.memory digests) or documented as an accepted gap here.
   - Acceptance: a residual-risk section is present; Leak-6 appears either as an implemented mitigation (with a test) or as an explicitly documented accepted gap.

8. **Sign-off forcing function** (VAUD-SIGNOFF): approve is gated on review of risk.
   - Current: V7 ships a basic approve/reject prompt with no forcing function.
   - Target: in `voss team run` sign-off and `voss audit`, the approve action is **unavailable until the human has acknowledged the killed-card + misroute diff**.
   - Acceptance: attempting to approve before acknowledging the killed-card/misroute diff is refused; after acknowledgement, approve is available; the acknowledgement is recorded.

9. **Calibration telemetry** (VAUD-CAL): reviewer reliability is measured.
   - Current: none.
   - Target: derive reviewer calibration telemetry from persisted verdicts — false-pass / slop-rejection rate (B verdict vs A verification outcome) — and provide a sampled human spot-audit hook.
   - Acceptance: a calibration report computes false-pass / slop-rejection rate from persisted verdicts; a sampled spot-audit selection hook exists.

## Boundaries

**In scope:**
- `voss audit <run_id>` read-only, deterministic CLI.
- Full audit content surface (PRD §9 sections) from persisted V2–V7 data.
- Source-tagged claims-vs-evidence with unsupported flagging.
- Per-node budget accounting + scope violations/denials.
- Separate Reviewer-A/B sections + killed/rescoped lineage.
- Markdown + JSON export.
- Residual-risk section + Leak-6 mitigate-or-accept.
- Sign-off forcing function (hard gate).
- Reviewer calibration telemetry + spot-audit hook.
- Mark O6 superseded (plans = reference only).

**Out of scope:**
- ADE navigable session-tree / audit panel rendering (AUD-09) — V11 (V9 ships data + CLI + export).
- Reuse of the existing O6 plans — re-plan fresh against the V4–V7 persistence contracts.
- Any change to the persistence schemas V9 consumes — audit is a read-only consumer.
- Any field change to `RunRecord`/`SessionRecord`/`voss_runtime.BudgetScope` — frozen.
- New third-party dependencies.

## Constraints

- **Read-only + deterministic:** the audit is assembled purely from persisted data (`run-final.json` V7, session-tree nodes V4, review sidecars V6, lineage V7, active principles V2); the same persisted data yields an identical audit; the audit never writes to the audited run's data.
- **Forcing function:** approve is blocked until the killed-card + misroute diff is acknowledged (in both `voss team run` sign-off and `voss audit`).
- Calibration telemetry is derived from persisted verdicts (B verdict vs A verification outcome); slop-rejection rate is tracked, not just pass/fail.
- No change to frozen `RunRecord`/`SessionRecord`/`BudgetScope`; no new deps.

## Acceptance Criteria

- [ ] `voss audit` (default latest) renders a complete audit and exits 0; `voss audit <run_id>` renders that run; unknown run exits non-zero with stderr; identical persisted data → identical audit.
- [ ] The audit contains every PRD §9 section, populated from its persisted source (missing source → explicit "none", no crash).
- [ ] Each item is source-tagged EM-claim vs verified-evidence; an unsupported EM claim is flagged; verified items show evidence refs.
- [ ] Per-node budget (limit/spent) is shown; rejected budget raises + scope denials appear with reasons.
- [ ] Reviewer-A and Reviewer-B outputs are in separate sections; every killed/rescoped card shows its lineage + routing rationale.
- [ ] `voss audit` exports both a valid Markdown report and a valid JSON document; the JSON round-trips the audit data.
- [ ] A residual-risk section is present; Leak-6 is either mitigated (with a test) or documented as an accepted gap.
- [ ] Approve is refused until the killed-card + misroute diff is acknowledged (in `voss team run` + `voss audit`); the acknowledgement is recorded.
- [ ] A calibration report computes reviewer false-pass / slop-rejection rate from persisted verdicts; a sampled spot-audit hook exists.
- [ ] `git diff` shows zero field changes on `RunRecord`/`SessionRecord`/`BudgetScope`.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                            |
|--------------------|-------|------|--------|------------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Audit product + forcing function + calibration + Leak-6 scoped    |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | ADE render→V11, O6-plan reuse out, read-only consumer explicit    |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Read-only/deterministic, hard forcing gate, schema freeze         |
| Acceptance Criteria| 0.84  | 0.70 | ✓      | 10 pass/fail criteria                                            |
| **Ambiguity**      | 0.137 | ≤0.20| ✓      |                                                                  |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective       | Question summary                                  | Decision locked                                                       |
|-------|-------------------|--------------------------------------------------|----------------------------------------------------------------------|
| 0     | Researcher (scout)| Is O6 / any audit shipped?                       | O6 planned, NOT executed; no audit code → V9 greenfield               |
| 1     | Researcher        | V9 scope vs the 6 O6 plans?                       | Re-plan fresh; O6 plans = reference only; O6 superseded               |
| 1     | Researcher        | AUD-09 ADE render?                                | Data + CLI + export in V9; ADE navigable render → V11                 |
| 1     | Researcher        | Calibration (O6-04) + Leak-6 (O6-06)?            | Include — V9 absorbs all of O6                                        |
| 2     | Failure Analyst   | Sign-off forcing-function strength?              | Hard gate — approve blocked until killed-card+misroute acknowledged  |
| 2     | Boundary Keeper   | AUD-03 claims-vs-evidence mechanism?             | Source-tagged; unsupported EM claims flagged                         |
| 2     | Failure Analyst   | Leak-6 disposition?                              | Mitigate-or-accept (mitigation with test, else documented gap)      |

---

*Phase: V9-audit-product-supersedes-o6-reuse-o6-plans*
*Spec created: 2026-06-06*
*Next step: /gsd-discuss-phase V9 — implementation decisions (audit section schema, JSON shape, forcing-function UX, calibration metrics)*
