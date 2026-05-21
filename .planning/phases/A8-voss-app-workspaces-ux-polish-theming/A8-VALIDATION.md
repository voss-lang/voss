---
phase: A8
slug: voss-app-workspaces-ux-polish-theming
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-20
---

# Phase A8 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest + Solid Testing Library, Cargo test, Playwright/manual runtime checks |
| **Config file** | `apps/voss-app/vitest.config.ts`; Cargo workspace `Cargo.toml`; Playwright via `apps/voss-app` scripts |
| **Quick run command** | `pnpm --dir apps/voss-app test -- --run src/themes src/workspaces src/components/workspace && cargo test -p voss-app-core themes workspaces profiles` |
| **Full suite command** | `pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && cargo test -p voss-app-core && cargo build -p voss-app` |
| **Estimated runtime** | quick ~90s; full ~5-8m |

---

## Sampling Rate

- **After every task commit:** Run the task's focused Vitest/Cargo command.
- **After every plan wave:** Run the quick run command.
- **Before `/gsd:verify-work`:** Full suite must be green, then runtime/manual checks recorded.
- **Max feedback latency:** 8 minutes for automated gates; manual platform gates recorded separately.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| A8-00-01 | 00 | 0 | UXP-01..UXP-30 | T-A8-00 | A8 does not execute over missing A7/UI/source substrate | source + shell | `test -f .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md && test -f apps/voss-app/src/command-palette/registry.ts && test -f apps/voss-app/src/command-palette/toast.tsx` | no | pending |
| A8-01-01 | 01 | 1 | UXP-09..14, UXP-21, UXP-25..27 | T-A8-01/T-A8-02 | Theme/profile/settings files validate, fail safe, and never block boot on corrupt input | Vitest + Cargo | `pnpm --dir apps/voss-app test -- --run src/themes && cargo test -p voss-app-core themes profiles` | no | pending |
| A8-02-01 | 02 | 2 | UXP-01, UXP-02, UXP-06, UXP-08 | T-A8-03/T-A8-04 | All mounted workspaces restore, only active workspace handles keys, close saves all sessions | Vitest + Cargo | `pnpm --dir apps/voss-app test -- --run src/workspaces src/grid && cargo test -p voss-app-core workspaces session` | no | pending |
| A8-03-01 | 03 | 3 | UXP-03..08 | T-A8-05 | Workspace tab UI supports picker, rename, fixed color dots, reorder, shortcuts, and close guard | Vitest | `pnpm --dir apps/voss-app test -- --run src/components/workspace src/__tests__/App.test.tsx` | no | pending |
| A8-04-01 | 04 | 4 | UXP-15..24 | T-A8-06/T-A8-07 | Appearance settings apply live, font floor holds, reduced-motion and high-contrast override globally | Vitest + build | `pnpm --dir apps/voss-app test -- --run src/themes src/accessibility src/pane src/grid && pnpm --dir apps/voss-app build` | no | pending |
| A8-05-01 | 05 | 5 | UXP-28..30 | T-A8-08 | Platform effects are gated per OS and degrade gracefully where unsupported | build + manual | `cargo build -p voss-app && pnpm --dir apps/voss-app build` | no | pending |

*Status: pending, green, red, flaky*

---

## Wave 0 Requirements

- [ ] `A8-00-SUMMARY.md` verifies A8-CONTEXT, A8-RESEARCH, A8-VALIDATION, A8-UI-SPEC, and source seams.
- [ ] `A8-00-SUMMARY.md` records A7 implementation status and whether palette/profile command wiring is available.
- [ ] Focused tests or source probes prove `GridRoot` can be made active-workspace-aware before hidden workspaces mount.
- [ ] Focused tests or source probes prove A6 close-save can be centralized before multi-workspace close is implemented.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Native vibrancy/acrylic/mica visible or gracefully absent | UXP-15, UXP-28, UXP-29, UXP-30 | jsdom cannot prove OS compositor behavior | Run the Tauri app on macOS, Windows, and Linux. Set opacity below 1.0. Confirm macOS/Windows native effect where supported and Linux CSS fallback/no crash. |
| Hidden workspace PTYs continue running | UXP-01, UXP-02 | Requires live PTY process behavior | Open three workspaces, run a ticking command in workspace 1, switch away for 10s, switch back, confirm output advanced. |
| Quit/reopen restores three workspaces | UXP-06 | Requires real app close lifecycle | Open three workspaces with distinct layouts/cwds, quit, relaunch, confirm index and each session restore. |
| Drag-to-reorder feels native and does not resize tabs unpredictably | UXP-07 | Visual/interaction quality requires real pointer input | Drag tabs across positions, confirm order persists and labels/controls do not overlap. |
| High-contrast visual quality across 12 themes | UXP-21 | Automated contrast can pass while theme quality is poor | Toggle high contrast over each bundled theme and inspect pane, tab bar, titlebar, and overlays. |

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all missing design/source dependency references.
- [x] No watch-mode flags.
- [x] Feedback latency target recorded.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** pending
