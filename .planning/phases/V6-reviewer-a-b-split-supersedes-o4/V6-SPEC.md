# Phase V6: Reviewer A/B Split (supersedes O4) — Specification

**Created:** 2026-06-06
**Ambiguity score:** 0.137 (gate: ≤ 0.20)
**Requirements:** 5 locked (delta on shipped O4)

## Goal

Turn the shipped O4 reviewers into a coherent product flow: wire **both** Reviewer-A (authored verification) and Reviewer-B (independent verdict) into the board Done gate as two genuinely independent sources, persist the review artifacts, add the verdict's inferred-domain field, and ship a `voss review <run_id>` CLI — without touching the frozen record schemas.

## Background

O4 shipped real reviewers (`voss/harness/board/`, plans O4-01..04 with SUMMARYs):
- `reviewer_a.py` — derives the bar from the **original idea** (not EM AC); for code cards authors a test file + runs it via `shell_run` (exit code = verdict); for AI cards authors a rubric + delegates to `judge_run`. (REV-01,02,03,08.)
- `reviewer_b.py` — independent tiered judge (fast/strong) via one `provider.complete()`; **EM-narrative-blind**; **Residual-2** authority (block when A's verification diverges from the idea); parse-fail → fail-safe `block`. (REV-04,05,07.)
- `verdict.py` — frozen `ReviewerVerdict` (`conf`, `source`, `tier`, `verdict`, `notes`, `evidence_refs`) + `Reviewer` Protocol.

So **REV-01..05, 07, 08 are shipped.** Gaps vs PRD REV-01..10:
- **REV-06** — verdict lacks `domain_inferred` (code/ai/docs/unknown).
- **REV-09** — A's authored verification + B's verdict are not durably persisted.
- **REV-10** — no `voss review` CLI.
- **Board wiring** — `Board` has a single `reviewer` slot; the PRD requires two independent sources at Done (A's verification AND B's verdict).

V6 supersedes O4 (ROADMAP); O4 artifacts retained as reference. V6 sits on V5 (board) + V4 (session tree). **Locked direction (interview):** delta on shipped O4; wire both A+B into the Done gate (both required, independent); add `domain_inferred`; persist A verification + B verdict under the card's session-tree node; `voss review <run_id>` read-only, per-card A+B detail.

## Requirements

1. **Two-source Done gate** (VREV-03/04/07 integration): A's verification and B's verdict are both required at Done.
   - Current: `Board` takes one `reviewer`; A and B exist but aren't both wired as gating sources.
   - Target: `Board` takes `reviewer_a` + `reviewer_b`; a card reaches Done only if A's authored verification PASSES (tests exit 0 / eval ≥ threshold) **AND** B's verdict is `pass`; a B `block` (including A-divergence-from-idea) sends the card to Blocked; B stays EM-narrative-blind.
   - Acceptance: a Done transition with A-verification failing is refused; with B verdict ≠ pass is refused; with both passing (and other predicates) succeeds; a B `block` moves the card to Blocked.

2. **Verdict `domain_inferred`** (VREV-06): the verdict carries an inferred domain.
   - Current: `ReviewerVerdict` is 6-field, no domain.
   - Target: add `domain_inferred` (`code`/`ai`/`docs`/`unknown`) to the board-local `ReviewerVerdict`; B populates it, A defaults; additive (not a redaction-guarded record).
   - Acceptance: a B verdict carries a `domain_inferred` value from the allowed set; existing verdict construction still works.

3. **Review-artifact persistence** (VREV-09): review outputs are durable.
   - Current: verdicts/verification are not persisted to disk.
   - Target: A's authored verification (test file path / rubric text + result) AND B's verdict persist under the card's session-tree node (review sidecar file or node fields).
   - Acceptance: after a reviewed card, its A verification + B verdict are readable from the persisted node/sidecar without re-running review.

4. **`voss review` CLI** (VREV-10): review outcomes are inspectable.
   - Current: no `review` command.
   - Target: `voss review <run_id>` (default latest) prints, per card, A's verification (test/rubric + result) + B's verdict (verdict/conf/tier/domain/evidence/notes) + final Done/Blocked; read-only from persisted review artifacts.
   - Acceptance: `voss review` (no arg) prints the latest run's per-card A+B review and exits 0; an unknown run exits non-zero with stderr.

5. **Shipped reviewer verification** (verify): REV-01..05,07,08 regress green; O4 superseded.
   - Current: ReviewerA/B shipped + tested.
   - Target: verify after wiring — A derives bar from the original idea only (not EM AC); B stays EM-narrative-blind; A and B see different context packets; B retains Residual-2 block authority; reviewers operate within budget/scope. Mark O4 superseded.
   - Acceptance: A's context excludes EM AC/DoD; B's context excludes EM narrative and is distinct from A's; B blocks on A-divergence; existing O4 reviewer tests pass.

## Boundaries

**In scope:**
- Wire both Reviewer-A + Reviewer-B into the board Done gate (two independent sources).
- `domain_inferred` on `ReviewerVerdict`.
- Persist A verification + B verdict under the card's session-tree node.
- `voss review <run_id>` read-only CLI.
- Verification/regression of shipped ReviewerA/B; mark O4 superseded.

**Out of scope:**
- ADE reviewer-verdict panel rendering — V11.
- Reviewer calibration telemetry + slop-rejection spot-audit — V9 (Audit Product) / O6 residual register.
- EM routing / card creation — V7.
- Board state-machine changes beyond the reviewer wiring — V5.
- Any field change to `RunRecord`/`SessionRecord`/`voss_runtime.BudgetScope` — frozen.
- New third-party dependencies.

## Constraints

- **Two independent sources at Done:** A's authored verification AND B's verdict both required; B stays EM-narrative-blind; A derives the bar from the original idea only.
- `domain_inferred` is additive on the board-local `ReviewerVerdict` (not a redaction-guarded record); B populates, A defaults.
- Review artifacts persist under the card's session-tree node; `voss review` is read-only from persisted artifacts; default = latest run.
- No change to frozen `RunRecord`/`SessionRecord`/`BudgetScope`.
- Reuse existing reviewer/provider/judge plumbing; no new deps.

## Acceptance Criteria

- [ ] Board Done requires A's verification to PASS (tests exit 0 / eval ≥ threshold) AND B verdict = pass; either failing refuses Done; B `block` moves the card to Blocked.
- [ ] B retains Residual-2 authority: a card whose A-verification diverges from the original idea is blocked at the gate.
- [ ] `ReviewerVerdict` carries `domain_inferred` ∈ {code, ai, docs, unknown}; B populates, A defaults; existing construction still works.
- [ ] A's authored verification (test path/rubric + result) AND B's verdict persist under the card's session-tree node and are re-readable without re-running review.
- [ ] `voss review` (default latest) prints per-card A verification + B verdict (verdict/conf/tier/domain/evidence/notes) + final Done/Blocked, read-only; unknown run exits non-zero with stderr.
- [ ] Regress: A's context excludes EM AC/DoD; B's context excludes EM narrative and differs from A's; existing O4 reviewer tests pass.
- [ ] `git diff` shows zero field changes on `RunRecord`/`SessionRecord`/`BudgetScope`.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                          |
|--------------------|-------|------|--------|----------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Delta = two-source gate + domain + persistence + CLI           |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | ADE→V11, calibration→V9, EM→V7 explicit                        |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Two-source independence, additive verdict field, schema freeze  |
| Acceptance Criteria| 0.84  | 0.70 | ✓      | 7 pass/fail criteria, delta-focused                            |
| **Ambiguity**      | 0.137 | ≤0.20| ✓      |                                                                |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective       | Question summary                                  | Decision locked                                                       |
|-------|-------------------|--------------------------------------------------|----------------------------------------------------------------------|
| 0     | Researcher (scout)| What of REV-01..10 already exists?               | O4 shipped REV-01..05,07,08; gaps = domain/persistence/CLI + A+B wiring |
| 1     | Researcher        | V6 scope given O4 shipped?                        | Delta on shipped O4 + wire both A+B into Done gate; O4 superseded     |
| 1     | Researcher        | Add `domain_inferred` to verdict (REV-06)?       | Yes — additive on board-local ReviewerVerdict; B populates           |
| 1     | Researcher        | What/where to persist (REV-09)?                  | A verification + B verdict under the card's session-tree node        |
| 2     | Boundary Keeper   | How to wire two sources at Done?                  | Both required, independent: A verification PASS AND B verdict pass; B block→Blocked |
| 2     | Simplifier        | `voss review` output?                             | Per-card A verification + B verdict + final, read-only from persisted |

---

*Phase: V6-reviewer-a-b-split-supersedes-o4*
*Spec created: 2026-06-06*
*Next step: /gsd-discuss-phase V6 — implementation decisions (review sidecar schema, Done-gate composition, review CLI layout)*
