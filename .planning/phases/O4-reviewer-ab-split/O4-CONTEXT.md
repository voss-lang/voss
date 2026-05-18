# Phase O4: Reviewer A/B Split - Context

**Gathered:** 2026-05-17
**Status:** Seeded from `.planning/ORCHESTRATION-PLAN.md` — needs `/gsd-spec-phase` then `/gsd-plan-phase`
**Source of truth:** `.planning/ORCHESTRATION-PLAN.md` (§2 roles, §7 residuals, §8 decisions)

<domain>
## Phase Boundary

O4 builds the cage's keystone judgment layer: independent bar/verification authoring (A) cleanly split from independent judgment (B). This split is what restores two genuinely independent sources at →Done and un-blinds calibration.

**In scope:**
- **Reviewer-A:** re-derives the judging bar from the **original human idea** (not EM's AC); authors verification — deterministic tests for code domains, eval harness for the AI domain (reuse `voss/eval/` — `judge.py` `Verdict`/`judge_run`, `TaskSpec`, suite loader).
- **Reviewer-B:** independent session + model, **no shared memory with A or EM**; tiered (fast at intermediate gates, strong at →Done); checks AI slop / errors / correctness; input contract = `[artifact, acceptance, repo, original_idea]`, **blind to EM narrative/plan**.
- **Residual-2 invariant (must be implemented, not just documented):** Reviewer-B sees the raw idea and has explicit authority to **fail a card whose A-verification diverges from the idea**. Without this, Reviewer-A's misread propagates silently.

**Out of scope:** Board transition logic (O3 — O4 exposes the verdict/verification interface O3 consumes). EM dispatch (O5). Calibration telemetry (O6 — O4 must emit the data O6 will audit: B-verdict vs. A-verification).
</domain>

<decisions>
## Locked Decisions (from ORCHESTRATION-PLAN.md §8)

- **Confidence source is an independent reviewer** (decision #6), never self-reported (invariant #3).
- **Audit bar = original idea, Reviewer-A re-derives** (decision #13). EM's AC/DoD are worker scaffolding, never the judging bar.
- **Engineers cannot author the verification that gates them** (decisions #14, invariant #5) — Reviewer-A owns tests/eval.
- **A/B split** (decision #15): author ≠ judge. Single-reviewer concentration collapses the →Done double gate and blinds calibration; the split resolves both.
- **AI-card eval gate** (decision #21): the AI domain's second source is an eval harness, not deterministic tests.

### Claude's discretion (resolve at SPEC/plan)
- Model selection for A vs. B vs. B-tiers.
- Eval-harness authoring interface for Reviewer-A on AI cards (golden set vs. rubric).
- Exact information-isolation mechanism guaranteeing B has no EM/A memory bleed.
</decisions>

## Dependencies
- Depends on: O2 (roster/registry), O3 (gate consumes the verdict).
- Blocks: O5, O6.
- Carries residual risks: #2 (A misread — invariant above), #5 (LLM-judging-LLM slop — O6 telemetry).
