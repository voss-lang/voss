---
phase: V11
slug: ade-org-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-07
---

# Phase V11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Test seams + fixture requirements derived from V11-RESEARCH.md "## Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (frontend)** | vitest (existing — `apps/voss-app/vitest.config.ts`) |
| **Framework (Rust/Tauri)** | `cargo test` (`apps/voss-app/src-tauri`, `crates/voss-app-core`) |
| **Type gate** | `tsc --noEmit` (frontend) |
| **Quick run command** | `cd apps/voss-app && npx vitest run <changed test>` |
| **Full suite command** | `cd apps/voss-app && npx vitest run && npx tsc --noEmit && cargo test --manifest-path src-tauri/Cargo.toml` |
| **Estimated runtime** | ~60–120 seconds |
| **E2E** | Tauri WebDriver E2E is platform-blocked on macOS — skip-deferred (per CONTEXT discretion + memory). Gate = vitest + tsc + cargo only. |

---

## Sampling Rate

- **After every task commit:** Run the quick vitest command for the touched module (+ `tsc --noEmit` if types changed).
- **After every plan wave:** Run the full suite command.
- **Before `/gsd-verify-work`:** Full suite must be green AND the terminal-grid view must not regress.
- **Max feedback latency:** ~120 seconds.

---

## Fixture Strategy (golden JSON)

Golden-JSON fixtures captured from a **real persisted V4+ run** under `.voss/sessions/<run-id>/` drive panel + reducer tests (per CONTEXT discretion). Required fixtures (shapes verified in RESEARCH.md):

- `session-tree.json` — `SessionTreeNode` tree with `transitions[]` (5 kinds) — drives session-tree panel + replay reducer (VADE-02, VADE-10).
- `run-final.json` — `RunFinal` (10 fields + optional `sign_off`) — drives board final state, budget, scope, sign-off (VADE-01/05/06/07/09).
- `<card>.review.json` sidecar — `a_verification` / `b_verdict` / `final_outcome` — drives reviewer-verdict (VADE-03) and the diff-drilldown verification result (VADE-08; **note: raw diff text does not persist — `a_verification` is the per-card verification surface**).
- `audit --format json` output — `AuditReport` hierarchy — drives audit panel incl. unsupported-EM-claim flag + residual-risk (VADE-04).
- A run directory + a legacy flat `.json` session file — drives the `enumerate_runs` dual-layout filter test (must return only V4+ subdirs) (VADE / D-03).
- An invalid/missing run id — drives the view-level empty/error state (no crash) (VADE-01 acceptance).

---

## Per-Task Verification Map

> Populated during execution as task IDs are assigned. Each VADE requirement maps to at least one fixture-driven vitest assertion or a cargo test for the Tauri command layer.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | — | — | VADE-01..10 | T-V11-* | CLI is sole write path; no app-side run-decision writes | unit | `npx vitest run` / `cargo test` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Golden-JSON fixtures captured from a real persisted run (see Fixture Strategy) committed under `apps/voss-app/src/**/__tests__/fixtures/` (or chosen location).
- [ ] Hand-authored TS contract types + runtime validation guards (D-02) with a parse-failure test (drift surfaces as error).
- [ ] `enumerate_runs` Rust unit test covering the dual-layout dir filter.

*Existing vitest + cargo infrastructure covers the framework — no install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Decision action actually shells the V7/V9 CLI (observable) | VADE-09 | End-to-end subprocess invocation needs a live `voss` binary + real run | Trigger approve/reject/unblock in the Org/Run view; confirm the confirmation dialog shows the literal CLI command and that the command runs (process observable) and panels auto-refresh |
| Org/Run view toggles without disturbing the terminal grid | VADE-02 | Visual/interaction state across views | Toggle to Org/Run and back; confirm grid layout unchanged |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (fixtures, contract types, enumerate filter)
- [ ] No watch-mode flags (`vitest run`, not `vitest`)
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
