---
phase: V14
slug: ade-run-cockpit-integrated-redesign-live-data-unification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-08
---

# Phase V14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Populated by the planner from RESEARCH.md "Validation Architecture" + the per-task acceptance criteria. Frontend phase — vitest (TS/Solid) + cargo (Rust IPC); Tauri E2E remains skip-deferred per project convention (macOS WebDriver blocked).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (apps/voss-app frontend) + cargo test (src-tauri / Rust IPC) |
| **Config file** | apps/voss-app/vitest.config.ts |
| **Quick run command** | `cd apps/voss-app && npx vitest run src/org` |
| **Full suite command** | `cd apps/voss-app && npx vitest run && npx tsc --noEmit` (+ `cargo test` for any Rust IPC touched) |
| **Estimated runtime** | ~30–60 s frontend; +Rust as needed |

---

## Sampling Rate

- **After every task commit:** Run the quick command scoped to touched area.
- **After every plan wave:** Run the full suite.
- **Before `/gsd-verify-work`:** Full suite green; `tsc --noEmit` clean.
- **Max feedback latency:** ~60 seconds.

---

## Per-Task Verification Map

> Planner fills one row per task. Gate: VCKP-13 OS-sandbox enforcement and VCKP-02 id-bridge must have automated verification (the keystone + the security floor). Tauri-runtime-only behaviors that cannot run headless on macOS go in Manual-Only.

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| (planner-filled) | | | VCKP-01..13 | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Golden `RunData` snapshot fixture + fake live-registry payload (id-bridge fixture for VCKP-01/02).
- [ ] **A1 verification (RESEARCH Open-Q1):** confirm native `run_id` vs harness `sessionID` vs `SessionTreeNode.id` equivalence against a real `.voss/sessions` tree — BEFORE the binding wave.
- [ ] Mock SSE stream fixture (VCKP-06 live-update test without a real `voss serve`).
- [ ] Normalized-model type stubs + selection-store skeleton.

*Resolve A1 in Wave 0 — the binding wave (VCKP-02) depends on which bridge applies.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cockpit visual/keyboard run-through | VCKP-05/10 | Tauri WebDriver blocked on macOS (project convention) | Launch app, ⌘⇧O → cockpit; select card; tab Board→drawer→timeline; verify selection drives all regions |
| OS sandbox denies out-of-scope write (real CLI) | VCKP-13 | Needs real sandboxed PTY spawn | Managed-launch agent with scope `tests/**`; attempt out-of-scope write; confirm kernel denial |
| Live SSE against real `voss serve` | VCKP-06 | Webview can't spawn server (Node-only launcher) | External `voss serve`; point cockpit at it; observe live board/budget update |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or a Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers id-bridge fixture + A1 + mock SSE
- [ ] VCKP-02 (id-bridge) and VCKP-13a (OS sandbox) have automated checks
- [ ] No watch-mode flags
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
