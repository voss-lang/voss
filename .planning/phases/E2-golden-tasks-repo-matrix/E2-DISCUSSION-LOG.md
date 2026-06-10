# Phase E2: Golden Tasks × Repo Matrix - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** E2-golden-tasks-repo-matrix
**Areas discussed:** Fixture repo nature, Matrix coverage, Toolchain strategy, Cognition-proof depth (all 4 — user delegated)

---

## Gray-area selection

No E2-SPEC existed; discuss-phase ran with `spec_loaded=false` (decisions seed EVGLD-* requirements). Four gray areas presented. **User response: "apply all of your recommendations and create CONTEXT.md"** — full delegation to Claude's recommended defaults.

| Area | Options offered | Decision applied |
|------|-----------------|------------------|
| Fixture repo nature | synthetic-minimal · realistic-small vendored | **synthetic-minimal** (hermetic, in-repo, ≤5 files/lang) |
| Matrix coverage | full 5×3=15 · curated subset | **curated ~12** (analyze/approved-edit/validation × py/rust/ts = 9; plan-only/resume/fetch-summarize ×1 on Python) |
| Toolchain strategy | require-all fail-loud · skip-absent · containerize | **require-present + explicit recorded skip** (`skipped: toolchain-absent` surfaced; `--require-all-toolchains` strict flag; preflight prints availability) |
| Cognition-proof depth | edit/tests-pass only · also assert architecture.md | **both** (behavioral toolchain gate + edit-landed file-contains AND analyze→architecture.md names language-correct tooling) |

---

## Rationale anchors

- All four defaults derive from E1's substrate + the E-track posture (internal-only, $0 subscription auth, deterministic-gate-first, anti-false-green).
- Synthetic-minimal + curated matrix keep cost/maintenance down while concentrating signal where project shape changes agent behavior.
- "No silent caps" (E1) → "no silent skips" (E2): a skipped toolchain must read as skipped, never green.
- Cognition gate (architecture.md correctness) defeats lucky-edit false-green — the E-track's reason to exist.

## Deferred Ideas

- Full 15-cell matrix · realistic vendored repos · containerized toolchains · more languages (Go/Java) · `tests/e2e/` graduation question (cross-E-track).
