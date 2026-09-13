---
phase: A2-voss-app-pty-pane
plan: 05
subsystem: ui
tags: [pty, flood-perf, d-02, alt-screen, pty-08, app-integration, e2e-deferred]

requires:
  - phase: A2-04
    provides: full pane interaction layer (paste-guard, ⌘C/SIGINT, find/clear, OSC8, fg-header, exit/restart)
  - phase: A2-02
    provides: Rust PTY backend (voss-app-core spawn_session/start_reader/validate_write/foreground + PtyRegistry/PtyEvent)
provides:
  - D-02 flood-perf harness finalized — real Linux-CI assertion (p95<33ms / echo<200ms, exit 1 on violation); macOS skip-defers with explicit notice (mechanism unit-proven A2-03)
  - e2e/flood-perf.spec.ts (Playwright perf driver, skip-with-reason on macOS, contract intact for Linux CI)
  - test-only window.__vossPerf rAF ring-buffer hook in PaneComponent (env-guarded, inert in production — T-A2-12)
  - PaneComponent mounted into App.tsx — first visible live terminal in the running voss-app shell
  - app src-tauri/src/lib.rs wires the PTY command surface (spawn_pty/pty_write/pty_resize/pty_pause/pty_resume/pty_kill/get_fg_process) + manages Arc<PtyRegistry>
  - Phase A2 complete: a working, interactive, Variant B PTY pane in the voss-app window
affects: [A3, A10]

tech-stack:
  added: []
  patterns:
    - "Cross-crate Tauri commands: tauri::generate_handler! only resolves the hidden command helper macros generated in the SAME crate; a pub use of cross-crate #[tauri::command]s does NOT bring those macros into scope. Fix = thin app-level #[tauri::command] wrappers delegating to the library's public API (voss-app-core::pty::*), registered in the app's single invoke_handler with app-managed state."
    - "Test-only perf instrumentation guarded by import.meta.env.MODE === 'test' — real on Linux CI / inert in the production bundle."
    - "macOS Tauri-E2E (Playwright) is uniformly skip-deferred with an explicit DEFERRED (not pass-masked) message; the assertion/measurement code is real for the Linux CI path."

key-files:
  created:
    - apps/voss-app/e2e/flood-perf.spec.ts
  modified:
    - apps/voss-app/scripts/test-flood-perf.ts (A2-01 red scaffold → real assertion: P95_MAX_MS=33 / ECHO_MAX_MS=200 / process.exit(1); macOS DEFERRED branch)
    - apps/voss-app/src/pane/PaneComponent.tsx (env-guarded window.__vossPerf rAF ring-buffer + perfStop cleanup)
    - apps/voss-app/src/App.tsx (mount <PaneComponent index={1}/> in the body — plan-defect fix; no A2 plan listed App.tsx)
    - apps/voss-app/src-tauri/src/lib.rs (plan-defect fix: register 7 PTY commands + manage Arc<PtyRegistry> — backend was never wired into the Tauri app)

key-decisions:
  - "**Two plan-defects fixed in flight, both required for A2 to function/verify:** (1) No A2 plan mounted PaneComponent into App.tsx → the pane was invisible; mounted it (A2's whole purpose: 'embed a working PTY pane in the shell'). (2) No A2 plan wired voss-app-core into apps/voss-app/src-tauri/src/lib.rs → spawn_pty rejected, terminal stayed black, dot stuck loading. Wired app-level command wrappers + Arc<PtyRegistry>."
  - "voss-app-core's tauri::plugin Builder::init() (A2-02) is unused by the app: Tauri plugin commands require plugin:name|cmd JS addressing + plugin permission config; the frontend (A2-03 pty-ipc.ts) uses bare invoke('spawn_pty'). App-level wrappers (delegating to voss-app-core public pty API) keep the bare-invoke contract with zero frontend churn and no plugin-permission rabbit hole. init() left in the crate as a harmless future option."
  - "D-02 flood-perf: per the recorded macOS-E2E decision (memory voss-app-tauri-e2e-macos-blocked), the live Playwright measurement is deferred to Linux CI; the script's threshold assertion (33/200, exit 1, no `|| true` mask) is real for that path. D-02 *mechanism* is unit-proven on macOS (A2-03 pty-ipc.test.ts 3/3: rAF coalescing + watermark pause>100k/resume<10k)."
  - "PTY-08 (Task 2 manual gate): user-approved via Claude Code running inside the pane — a maximal alt-screen TUI exercising alt-screen + colors + signals + OSC title (header showed `claude.exe`) + interactive input. This is a stronger proof than the vim/htop/tmux/less matrix; the 4-app matrix is recorded as a recommended later spot-check (non-blocking, Nyquist 'continue anyway' precedent). xterm.js #802 scrollback-dup cosmetic accepted (not observed/blocking)."

patterns-established:
  - "A-track integration checklist: a new pane/component is not done until it is (a) mounted in App.tsx and (b) its Tauri commands registered in apps/voss-app/src-tauri/src/lib.rs. Future A plans must list these files when adding a backend-backed component."

requirements-completed: [PTY-02, PTY-08]

duration: ~40min (incl. 2 integration plan-defect fixes + cross-crate Tauri-command resolution)
completed: 2026-05-19
---

# Phase A2, Plan 05: D-02 Flood Gate + PTY-08 + App Integration Summary

**Finalized the D-02 flood-perf assertion (real Linux-CI gate, macOS skip-deferred with the mechanism unit-proven on A2-03), mounted the PTY pane into App.tsx, and wired the voss-app-core PTY backend into the Tauri app — closing Phase A2 with a working, interactive Variant B terminal pane proven by Claude Code itself running inside it.**

## Performance

- **Tasks:** 2 (Task 1 auto; Task 2 blocking human-verify) + 2 in-flight integration plan-defect fixes
- **Files created:** 1 | modified: 4
- **Wave:** 4 (final A2 wave)

## Accomplishments

- D-02 flood-perf: A2-01 red scaffold → real assertion (`P95_MAX_MS=33`, `ECHO_MAX_MS=200`, `process.exit(1)` on violation, no mask); macOS prints explicit `D-02 DEFERRED` (exit 0) referencing the A2-03 unit proof; Linux-CI Playwright driver (`flood-perf.spec.ts`) carries the unchanged measurement contract.
- `window.__vossPerf` rAF ring-buffer hook added, env-guarded (`import.meta.env.MODE === 'test'`) — inert in production (T-A2-12); `perfStop` on cleanup.
- **Pane is live in the app:** PaneComponent mounted in App.tsx; PTY commands registered app-level; `pnpm tauri dev` shows the shell prompt, green running dot, OSC-title process slot.
- **PTY-08 proven:** Claude Code (full alt-screen TUI: status bar, input box, signals, OSC title `claude.exe`) ran interactively inside the pane — user-confirmed "it works".
- No regression: vitest 5/5, cargo 4/4, tsc 0, app builds clean.

## Verify Output

```
pnpm tsx scripts/test-flood-perf.ts        → D-02 DEFERRED [yes] … exit 0
pnpm tsx scripts/test-flood-perf.ts --cat  → D-02 DEFERRED [cat …] … exit 0
assertion literals P95_MAX_MS=33 / ECHO_MAX_MS=200 / process.exit(1) present; no `|| true`
window.__vossPerf guarded by import.meta.env.MODE === 'test'
cargo build -p voss-app → Finished (0 warnings)
vitest 5/5 · cargo 4/4 · tsc 0
PTY-08 → user-approved via Claude Code alt-screen TUI in-pane
```

## In-Flight Plan-Defects Fixed

1. **PaneComponent never mounted (App.tsx).** No A2 plan listed App.tsx; the pane was invisible in the running app. Mounted `<PaneComponent index={1}/>` in the body — this is A2's stated goal. Logged a patterns-established integration checklist.
2. **PTY backend never wired into the Tauri app (src-tauri/src/lib.rs).** voss-app-core existed + tested but the app registered only `get_theme_overrides`; `invoke('spawn_pty')` rejected → black terminal, loading dot. Root cause: cross-crate `tauri::generate_handler!` cannot resolve another crate's `#[tauri::command]` helper macros via `pub use`. Fixed with thin app-level command wrappers delegating to voss-app-core's public `pty` API + app-managed `Arc<PtyRegistry>` (keeps the bare-invoke frontend contract; avoids the plugin-permission path).

## Follow-ups / Captured

- **Feature request captured (NOT built — out of A2 scope):** navbar "Agents" button + agent-launcher prefixes (Claude/Codex/Gemini/OpenCode) → project memory `voss-agents-launcher-feature`; candidate future A-track phase after A3 (needs the grid). Validated by Claude Code running in-pane.
- Linux CI: un-skip `pty.spec.ts` + `flood-perf.spec.ts` + add tauri-driver job (A10 / dedicated CI phase).
- Backend opener gap (A2-04 carry): `open_url`/`open_path` Rust handlers still unimplemented — ⌘+click links no-op (A10 / tauri-plugin-opener).
- Recommended later spot-check: vim/htop/tmux/less alt-screen matrix (Claude Code already covers the same surface; non-blocking).

## Phase A2 — COMPLETE

5/5 plans. A working, interactive, Variant B PTY pane in the voss-app shell: spawn/IO/resize/backpressure (A2-02), xterm render + Channel transport + D-02 frontend (A2-03), full interaction layer (A2-04), flood gate + app integration (A2-05). Strict build order A1→A2→**A3 next** (grid engine — Warp-style locked tiling per memory `voss-app-grid-warp-parity`). Ready for `/gsd:verify-work`.
