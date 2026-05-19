---
phase: A2-voss-app-pty-pane
plan: 03
subsystem: ui
tags: [xterm, solid, pty, tauri-channel, backpressure, raf-coalescing, variant-b]

requires:
  - phase: A2-02
    provides: Rust PTY backend (spawn_pty/pty_write/pty_resize/pty_pause/pty_resume/pty_kill/get_fg_process commands, PtyEvent Channel enum)
  - phase: A2-01
    provides: xterm v5 pinned deps, vitest config, RED PasteGuard scaffold
provides:
  - pty-ipc.ts PtyTransport — Tauri Channel transport with D-02 frontend half (per-rAF coalescing + watermark backpressure HIGH=100k/LOW=10k), spawn/write/resize/kill wrappers, injected-write for testability
  - PaneComponent.tsx — Solid pane: xterm v5.5.0 Terminal (verbatim UI-SPEC theme) + Canvas addon AFTER open, FitAddon/Search/WebLinks, bidirectional onData→pty_write, 150ms-debounced ResizeObserver→fit+pty_resize, DPR re-fit, 22px Variant B header, focus bg-lift, onCleanup dispose+kill
  - pane.css — Variant B chrome (tokens only, transition:none, radius:0, focus inset-glow, slim scrollbar)
  - 3 green pty-ipc unit tests (coalescing / pause / resume thresholds)
affects: [A2-04, A2-05, A3]

tech-stack:
  added: []
  patterns:
    - "PtyTransport injects the xterm `write` fn (decoupled from Terminal) so the D-02 coalescing+watermark logic is unit-testable without a real xterm/AppHandle."
    - "rAF coalescing + watermark are complementary and BOTH applied: data events push to pendingData + accumulate watermark; one rAF merges→single term.write; write-complete cb drains watermark; >HIGH→pty_pause, <LOW→pty_resume."
    - "CanvasAddon strictly after term.open() (D-01 Pitfall 2) — enforced and grep-verified by source order."
    - "Solid pane lifecycle: onMount build+open+spawn+observe; onCleanup clears timer, disconnects observer, removes DPR listener, kills PTY, disposes term."

key-files:
  created:
    - apps/voss-app/src/pane/pty-ipc.ts
    - apps/voss-app/src/pane/PaneComponent.tsx
    - apps/voss-app/src/pane/pane.css
    - apps/voss-app/src/pane/__tests__/pty-ipc.test.ts
  modified:
    - apps/voss-app/vitest.config.ts (include glob widened *.test.tsx → *.test.{ts,tsx}; pty-ipc.test.ts is .ts)

key-decisions:
  - PtyTransport guards pty_pause/pty_resume on a non-null sessionId — so unit tests must spawn() (mocked invoke→'sess-1') before asserting backpressure; matches real flow (transport always spawned before data).
  - Header shell-name + cwd come from props (A2 static structure per plan); real $SHELL/cwd wiring + status-dot/process lifecycle is A2-04. Loading dot = --fg-3 until spawn resolves → running (--accent-green); exit → --accent-red.
  - vitest include glob was .tsx-only (A2-01) — widened to {ts,tsx} so the .ts transport test is discovered (A2-01 config-defect; pty-ipc is logic, not a component, so .ts is correct).
  - `@xterm/xterm/css/xterm.css` + `./pane.css` side-effect imports type-check via the scaffold's `vite/client` ambient `*.css` declaration (src/vite-env.d.ts) — no extra .d.ts needed.

patterns-established:
  - "Frontend transport logic lives in plain .ts (testable in jsdom); only view components are .tsx. vitest include must cover both."
  - "Backpressure commands require a live session id — assert after spawn in tests, never on a bare transport."

requirements-completed: [PTY-02, PTY-03, PTY-08]

duration: ~30min
completed: 2026-05-18
---

# Phase A2, Plan 03: Solid xterm Pane + Channel Transport Summary

**Built the rendering+transport half of the pane: a Variant B Solid `PaneComponent` mounting xterm.js v5.5.0 (verbatim UI-SPEC theme, Canvas addon after open, 10k scrollback) wired bidirectionally to the A2-02 Rust PTY over a Tauri Channel, with the D-02 flood contract (per-rAF coalescing + 100k/10k watermark backpressure) implemented in a unit-tested, xterm-decoupled `PtyTransport`.**

## Performance

- **Tasks:** 2 (both auto; autonomous plan)
- **Files created:** 4 | modified: 1
- **Wave:** 2

## Accomplishments

- `pnpm vitest run pty-ipc` → **3/3 green**: N data events/frame ⇒ exactly 1 merged write; >100k bytes ⇒ `pty_pause`; drain <10k via write-cb ⇒ `pty_resume`.
- `pnpm exec tsc --noEmit` → **0 errors** (PaneComponent type-checks against A2-01/A2-02 deps).
- CanvasAddon loads strictly AFTER `term.open()` (source order 87<88, grep-verified — D-01 Pitfall 2).
- `pane.css` is token-only (`var(--bg-*)`/`--border`/`--focus-glow`), `transition: none`, `border-radius: 0`, focus = bg-lift + inset glow (no border change).
- 10k scrollback, full 16-color Variant B theme, `allowProposedApi:false`, `macOptionIsMeta:true` — verbatim UI-SPEC §3.
- onData→pty_write keystroke path; 150ms-debounced ResizeObserver→fit+pty_resize; DPR-change re-fit; onCleanup kills PTY + disposes term.

## Verify Output

```
Task 1: pnpm vitest run pty-ipc → Test Files 1 passed; Tests 3 passed
Task 2: tsc --noEmit → (no output = 0 errors)
        CanvasAddon OK · scrollback OK · tokens OK · transition:none OK
        open-before-canvas OK (87<88) · pty-ipc import OK · cleanup kill OK
```

Full `pnpm vitest run` shows 2 failed = the A2-01 **PasteGuard RED scaffold** (intentional, owned by A2-04) — NOT an A2-03 regression. A2-03's own gate (`vitest run pty-ipc`) is fully green.

## In-Flight Issues Caught

1. **vitest include glob (A2-01 config-defect).** `src/**/__tests__/**/*.test.tsx` missed `pty-ipc.test.ts` ("No test files found"). Widened to `*.test.{ts,tsx}` — transport logic is correctly `.ts`, not a `.tsx` component.
2. **Backpressure tests need a session.** pty_pause/pty_resume guard on non-null sessionId; tests initially asserted on a bare transport (0 invoke calls). Added `await t.spawn(...)` (mocked) before the assertions — matches real flow.

## Deferred (next waves)

- A2-04: PasteGuard banner+bypass (turns A2-01 RED green), copy/SIGINT smart ⌘C, OSC8 web-links activation, ⌘F/⌘⇧K search/clear UI, status-dot + live process-slot lifecycle, real $SHELL/cwd header values.
- A2-05: flood-perf real assertion (p95 rAF <33ms, echo <200ms) on top of this rAF+watermark pair; ExitBanner + restart; pane mounted into App.tsx (currently PaneComponent is standalone, not yet rendered in the A1 shell body).
- 11px Retina legibility re-check (carried from A1) — now that a real terminal renders, evaluate in A2-04/05 visual gate.
