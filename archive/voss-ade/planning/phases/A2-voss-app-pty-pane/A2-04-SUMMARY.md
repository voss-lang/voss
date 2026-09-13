---
phase: A2-voss-app-pty-pane
plan: 04
subsystem: ui
tags: [xterm, solid, paste-guard, sigint, find, osc8, exit-banner, e2e-deferred]

requires:
  - phase: A2-03
    provides: PaneComponent xterm mount + PtyTransport (Channel/coalescing/backpressure)
  - phase: A2-02
    provides: Rust PTY backend (pty_write/pty_kill/get_fg_process + PtyEvent exit)
provides:
  - PasteGuard.tsx (inline non-modal multi-line paste banner, UI-SPEC §5, copy-exact "Discard")
  - ExitBanner.tsx ([exited N] + Restart, 3-tier dot color, UI-SPEC §4)
  - FindBar.tsx (⌘F scrollback search overlay, Find… placeholder, UI-SPEC §8)
  - PaneComponent interaction layer — capture-phase paste→guard, customKeyEventHandler (⌘⇧V bypass / ⌘C smart copy-or-SIGINT 0x03 / ⌘F / ⌘⇧K clear), OSC8+file-path linkHandler with scheme allowlist, OSC0/2 title + 2s-guarded pgid fallback, exit→banner→restart (scrollback preserved)
  - PtyTransport.fgProcess() (D-07 pgid poll wrapper)
  - 5/5 frontend vitest green (PasteGuard reds resolved); Playwright e2e skipped-with-reason (macOS block, deferred to Linux CI)
affects: [A2-05, A3, A10]

tech-stack:
  added: []
  patterns:
    - "Capture-phase `paste` listener on the pane container intercepts before xterm; multi-line + !bypass → PasteGuard signal, else direct writePty; ⌘⇧V is a one-shot bypass flag consumed per paste."
    - "customKeyEventHandler returns false to swallow xterm default for ⌘C/⌘F/⌘⇧K; ⌘⇧V returns true (let native paste fire, banner suppressed by flag)."
    - "OSC8/file-path open path validates URL scheme against {http,https,mailto,file} allowlist BEFORE invoke (T-A2-09); other schemes silently dropped."
    - "D-07 arbitration: term.onTitleChange stamps lastOscTitleAt; 500ms pgid poll early-returns if an OSC title arrived within 2s."

key-files:
  created:
    - apps/voss-app/src/pane/PasteGuard.tsx
    - apps/voss-app/src/pane/ExitBanner.tsx
    - apps/voss-app/src/pane/FindBar.tsx
  modified:
    - apps/voss-app/src/pane/PaneComponent.tsx (6 interaction layers added; A2-03 mount logic preserved)
    - apps/voss-app/src/pane/pty-ipc.ts (added fgProcess() pgid-poll wrapper)
    - apps/voss-app/src/pane/pane.css (appended exit-banner / paste-guard / find-bar rules — A2-03 rules untouched)
    - apps/voss-app/src/pane/__tests__/PasteGuard.test.tsx (A2-01 RED → 2 green: preview/N-lines/Discard-not-Cancel + Send/Discard callbacks)
    - apps/voss-app/e2e/pty.spec.ts (7 specs → test.skip with documented macOS-platform reason)

key-decisions:
  - "**E2E platform block (decision gate).** Tauri WebDriver E2E is impossible on macOS (no WKWebView WebDriver; tauri-driver = Linux/Windows only). A2-VALIDATION specced 7 Playwright specs + flood-perf as automated Tauri E2E — unsatisfiable on the macOS dev machine (A1 platform). User chose 'Code + unit/tsc green, e2e deferred': all interaction code implemented, gate = vitest + cargo test + tsc; Playwright specs converted to test.skip with reason, deferred to a future Linux CI (A10/CI phase). Logged to project memory voss-app-tauri-e2e-macos-blocked. Nyquist 'continue anyway' (T6/A3 operator-waived precedent)."
  - "copyMode is `'smart' as CopyMode` (not `: CopyMode`) — a plain annotation lets TS narrow the const to the 'smart' literal and flags the !== 'sigint'/'copy' branches as no-overlap under strict; the cast widens it to the union (D-06 configurable hook; A8 surfaces UI)."
  - "Backend gap (documented, out of plan scope): PaneComponent invokes `open_url`/`open_path` but no Rust handler exists (voss-app-core = PTY commands only; no tauri-plugin-opener). Plan files_modified excludes Rust — frontend contract is correct; ⌘+click currently no-ops via the caught reject. Wire a Rust opener (or tauri-plugin-opener) in A2-05/A10."

patterns-established:
  - "macOS Voss desktop work gates on vitest+cargo+tsc; Tauri WebDriver E2E is a Linux-CI concern, never a macOS blocker."
  - "Strict-mode literal-narrowing escape: use `'x' as Union` for configurable-default consts whose value is compared against other union members."

requirements-completed: [PTY-03, PTY-04, PTY-05, PTY-06, PTY-07]

duration: ~45min (incl. E2E-platform decision gate + strict-narrowing fix)
completed: 2026-05-19
---

# Phase A2, Plan 04: Pane Interaction Layer Summary

**Implemented every human-facing pane behavior on the live terminal — multi-line PasteGuard (copy-exact "Discard"), ⌘C smart copy-or-SIGINT (0x03), ⌘F FindBar + ⌘⇧K clear, OSC8/file-path links with a scheme allowlist, OSC0/2-title + 2s-guarded pgid header, and the [exited N] ExitBanner with scrollback-preserving Restart. A2-01's RED PasteGuard tests are green; the Tauri-WebDriver E2E suite is skip-deferred (macOS platform block, user-approved).**

## Performance

- **Tasks:** 2 (both auto; autonomous plan) + 1 user decision gate (E2E strategy)
- **Files created:** 3 | modified: 5
- **Wave:** 3

## Accomplishments

- `pnpm vitest run` → **5/5 green** (PasteGuard 2 + pty-ipc 3); the A2-01 RED PasteGuard scaffold is now real green tests.
- `cargo test -p voss-app-core` → **4/4 green** (unchanged, no regression).
- `pnpm exec tsc --noEmit` → **0 errors**.
- Interaction contract greps: customKeyEventHandler, SIGINT `0x03`, scheme allowlist, onTitleChange, 2s-OSC guard all present.
- Components are copy-exact per UI-SPEC §9: `Discard` (not `Cancel`), `[exited N]`, `Find…`, `⌘⇧V skips this`, `Send`/`⏎`/`Esc`.
- All overlays `transition: none` + `border-radius: 0` (Variant B, UI-SPEC §11).

## E2E Decision Gate

Tauri WebDriver E2E cannot run on macOS (Apple ships no WKWebView WebDriver). Surfaced to the user; chose **"Code + unit/tsc green, e2e deferred"**. The 7 `pty.spec.ts` specs are `test.skip` with an in-file reason + the contract intent retained as comments for a future Linux CI un-skip. Project memory `voss-app-tauri-e2e-macos-blocked` records this so A2-05+ do not re-trip it.

## Verify Output

```
vitest run            → Test Files 2 passed; Tests 5 passed
cargo test            → test result: ok. 4 passed; 0 failed
tsc --noEmit          → EXIT=0
contract greps        → keyhandler / SIGINT byte / scheme allowlist / onTitleChange / 2s-OSC guard : all OK
playwright pty.spec   → 7 skipped (documented platform block)
```

## Deferred / Gaps

- **A2-05:** flood-perf real assertion (also Playwright — same macOS block; will follow the same skip-defer + a macOS-runnable perf proxy if feasible), ExitBanner-aware PasteGuard `above-exit` offset wiring, mount PaneComponent into App.tsx (first visible terminal in `pnpm tauri dev` — manual visual spot-check replaces automated E2E for A2 sign-off).
- **Backend opener gap:** `open_url`/`open_path` Rust handlers not implemented (out of A2-04 plan scope — Rust not in files_modified). ⌘+click links no-op until wired (A2-05/A10 / tauri-plugin-opener).
- **Linux CI E2E:** un-skip `pty.spec.ts` + add tauri-driver job — A10 or dedicated CI phase.
- 11px Retina legibility re-check (carried from A1) — do at the A2-05 manual visual gate once the pane is mounted.
