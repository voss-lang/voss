---
phase: A2-voss-app-pty-pane
plan: 01
subsystem: infra
tags: [pty, tauri-plugin, xterm, vitest, playwright, cargo-test, wave0, tdd-red]

requires:
  - phase: A1-04
    provides: voss-app Tauri shell complete (scaffold, Variant B tokens, titlebar, CSP, unsigned build); crates/voss-app-core placeholder crate + workspace member; apps/voss-app/package.json + pnpm workspace
provides:
  - voss-app-core expanded from A1 placeholder to a compiling Tauri-plugin crate (pty submodule skeleton, PtyRegistry default, init() plugin shell — NO PTY logic yet)
  - PTY dependency set pinned (portable-pty 0.9.0, nix 0.31 signal/term/process, libproc 0.14 macOS-gated, tauri 2 wry)
  - xterm v5 frontend stack pinned EXACT (@xterm/xterm 5.5.0 + addon-canvas 0.7.0 + addon-fit 0.11.0 + addon-search 0.16.0 + addon-web-links 0.12.0), enforced by root pnpm.overrides + check:xterm-pin script
  - Full RED test scaffold across all 3 runners — every A2-VALIDATION.md Wave 0 command resolves to a real failing test (3 cargo-test panics, 2 Vitest fails, 7 Playwright e2e fails, 1 flood-perf exit-1)
affects: [A2-02, A2-03, A2-04, A2-05]

tech-stack:
  added:
    - portable-pty 0.9.0
    - nix 0.31 (signal/term/process)
    - libproc 0.14 (macOS-gated)
    - tauri 2 (wry feature) [voss-app-core]
    - "@xterm/xterm 5.5.0 + addon-canvas/fit/search/web-links (exact pins)"
    - vitest 4.1.6, "@playwright/test 1.60.0", "@testing-library/dom 10.4.1", tsx 4.22.2, jsdom 29.1.1
  patterns:
    - "voss-app-core mirrors voss-agent flat pub-mod + pub-use; Tauri plugin via tauri::plugin::Builder::new + .setup(app.manage(PtyRegistry::default())). invoke_handler deliberately omitted in Wave 0 (no commands until A2-02)."
    - "RED-scaffold discipline: assert-fail / panic!, never .skip/.todo. Frontend tests do NOT import the not-yet-existing component (import would crash collection → 'no tests found'); they document the target props shape in a comment + expect(false)."

key-files:
  created:
    - crates/voss-app-core/src/pty/mod.rs
    - crates/voss-app-core/src/pty/commands.rs (doc-stub)
    - crates/voss-app-core/src/pty/reader.rs (doc-stub)
    - crates/voss-app-core/src/pty/writer.rs (doc-stub)
    - crates/voss-app-core/src/pty/foreground.rs (doc-stub)
    - crates/voss-app-core/src/pty/tests.rs (3 RED panics)
    - apps/voss-app/vitest.config.ts
    - apps/voss-app/playwright.config.ts
    - apps/voss-app/src/pane/__tests__/PasteGuard.test.tsx (2 RED)
    - apps/voss-app/scripts/test-flood-perf.ts (RED exit-1)
    - apps/voss-app/e2e/pty.spec.ts (7 RED)
  modified:
    - crates/voss-app-core/Cargo.toml (A1 placeholder -> PTY deps + workspace-inherited shared deps + macOS libproc target dep)
    - crates/voss-app-core/src/lib.rs (placeholder doc -> pub mod pty + PtyRegistry re-export + init() plugin shell)
    - apps/voss-app/package.json (xterm v5 exact pins + vitest/playwright/tsx/jsdom devDeps + test/test:e2e/test:flood-perf/check:xterm-pin scripts)
    - package.json (root — added pnpm.overrides @xterm/xterm 5.5.0; relocated from apps/voss-app where pnpm ignores it)

key-decisions:
  - Root Cargo.toml workspace-member add was ALREADY done by A1-01 (voss-app-core created as placeholder). A2-01 expanded the crate body in place — no duplicate member edit. A2-01 plan was written assuming the crate didn't exist; reconciled by treating A1's placeholder as the starting point.
  - **pnpm.overrides relocation (plan-defect):** A2-01 Task 2 instructed putting `pnpm.overrides` in `apps/voss-app/package.json`. pnpm emits `WARN ... will not take effect. Configure pnpm.overrides at the root` for non-root overrides in a workspace. T-A2-01 (xterm version-drift mitigation) REQUIRES the override to be effective, so it was moved to root `package.json` and the inert apps/voss-app block removed. Exact dep pin kept in apps/voss-app/package.json (satisfies the literal-pin grep). check:xterm-pin confirmed resolved 5.5.0.
  - Wave-0 lib.rs OMITS invoke_handler + the spawn_pty/... pub-use (those symbols don't exist until A2-02). The A2-PATTERNS.md lib.rs sample shows the full version; Wave 0 ships only the compiling subset (Builder + setup + manage) per Task 1 "NO PTY logic".
  - Test-infra devDeps pinned EXACT to latest (vitest 4.1.6 etc) consistent with the voss-app-track exact-pin discipline, even though only xterm/@tauri-apps/api/solid-js are security-mandated pins.

patterns-established:
  - "pnpm workspace rule: ALL pnpm.overrides live in the ROOT package.json, never a member package. Future version-pin mitigations must target root."
  - "Wave-0 crate skeleton compiles with empty doc-only submodule stubs + a single Default registry struct (#[allow(dead_code)] on the unused stub field); cfg(test) mod tests is fine to declare before tests.rs exists since cargo build skips it."

requirements-completed: [PTY-01, PTY-02, PTY-03, PTY-04, PTY-05, PTY-06, PTY-07, PTY-08]

duration: ~25min
completed: 2026-05-18
---

# Phase A2, Plan 01: Wave 0 — voss-app-core Scaffold + Pinned Deps + RED Test Suite Summary

**Expanded `voss-app-core` from A1's empty placeholder into a compiling Tauri-plugin crate with empty PTY submodules, pinned the xterm v5 + portable-pty dependency set with an enforced anti-drift override, and stood up a fully RED test suite (cargo-test / Vitest / Playwright / flood-perf) so every A2-VALIDATION.md PTY-0N command exists and fails before any feature work.**

## Performance

- **Tasks:** 3 (Task 0 blocking-human approved both gates; Tasks 1+2 auto)
- **Files created:** 11 | **modified:** 4
- **Wave:** 0 (foundation)

## Accomplishments

- `cargo build -p voss-app-core` exit 0; crate is a registered workspace package with a Tauri plugin `init()` shell + `PtyRegistry::default()` managed in `.setup`.
- PTY deps pinned: portable-pty 0.9.0, nix 0.31 (signal/term/process), libproc 0.14 (macOS target-gated), tauri 2 (wry).
- xterm v5 stack EXACT-pinned; **root** `pnpm.overrides` makes the `@xterm/xterm 5.5.0` pin survive `pnpm update` (T-A2-01); `check:xterm-pin` script confirms resolved = 5.5.0 pre- and post-install.
- RED suite proven discoverable, not skipped:
  - `cargo test -p voss-app-core` → 3 FAILED (test_pty_spawn_env / test_pty_round_trip / test_foreground_pgid panics)
  - `pnpm vitest run PasteGuard` → 2 failed (discovered, not "no tests found")
  - `e2e/pty.spec.ts` → 7 Playwright RED specs named to match A2-VALIDATION grep strings
  - `scripts/test-flood-perf.ts` → exit 1 with D-02 RED banner

## Verify Output

```
Task 1: cargo build -p voss-app-core → Finished (1m30s); CRATE_REGISTERED; MEMBER_OK
Task 2: SCAFFOLDS_PRESENT; ROOT_OVERRIDE_OK; xterm pin ok: 5.5.0 (resolved 5.5.0)
        cargo test -p voss-app-core → test result: FAILED. 0 passed; 3 failed
        pnpm vitest run PasteGuard → Test Files 1 failed (1); Tests 2 failed (2)
```

## In-Flight Issues Caught

1. **pnpm.overrides location (plan-defect).** Plan said put it in `apps/voss-app/package.json`; pnpm warns it is ignored outside the workspace root and the xterm anti-drift mitigation would be silently inert. Moved to root `package.json`, removed the inert member block, reinstalled — warning gone, pin effective. Logged as a patterns-established rule for future pin mitigations.
2. **A1/A2 crate-creation overlap.** A2-01 plan assumed it creates `crates/voss-app-core`; A1-01 already created it (placeholder) + added the workspace member. Reconciled by expanding the existing crate in place; no duplicate Cargo.toml member edit.

## Deferred (next waves)

- A2-02: real `PtySession` (portable-pty spawn, env, round-trip, foreground pgid) — turns the 3 RED cargo tests green; wires `invoke_handler` + the 5 `#[tauri::command]`s.
- A2-03: scrollback / clear / OSC title (pty-scrollback, pty-clear, pty-title).
- A2-04: PasteGuard banner + bypass, copy, OSC8 web-links (PasteGuard.test green, pty-copy, pty-osc8).
- A2-05: flood-perf harness real assertion (p95 rAF <33ms, echo <200ms) + ExitBanner restart.
- 11px Retina legibility re-check (carried from A1) — revisit once PTY pane renders body text.
