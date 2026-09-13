---
phase: A10
slug: voss-app-status-bar
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-20
---

# Phase A10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) + cargo test (Rust) |
| **Config file** | `apps/voss-app/vitest.config.ts` / `crates/voss-app-core/Cargo.toml` |
| **Quick run command** | `cd apps/voss-app && pnpm vitest run src/status-bar` |
| **Full suite command** | `cd apps/voss-app && pnpm vitest run && cd ../../ && cargo test -p voss-app-core` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd apps/voss-app && pnpm vitest run src/status-bar`
- **After every plan wave:** Run `cd apps/voss-app && pnpm vitest run && cargo test -p voss-app-core`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (populated during planning) | | | BAR-01..08 | | | | | | pending |

---

## Validation Architecture

### Frontend (vitest + @testing-library/dom)

- StatusBar component renders three clusters with correct content
- Popover open/close behavior (click-outside, Esc dismiss, one-at-a-time)
- Notification store add/clear/persist/badge logic
- Git branch display + hide-when-no-git

### Rust (cargo test)

- Git HEAD reading + branch name extraction
- Notification JSON persistence read/write
- Git watcher event emission

### Integration

- App.tsx mounts StatusBar below GridRoot
- Focused pane signal threading from GridRoot to StatusBar
- Workspace-aware state scoping (when A8 built)

---

## Success Criteria (from ROADMAP)

1. Branch updates within 500ms of `git checkout` in any pane.
2. Pane count updates instantly on split/close.
3. Project-less status bar renders without branch/project clusters.
4. Notification log persists across restart (last 50).
5. Switching workspace tabs → status bar updates to reflect new workspace's state.
