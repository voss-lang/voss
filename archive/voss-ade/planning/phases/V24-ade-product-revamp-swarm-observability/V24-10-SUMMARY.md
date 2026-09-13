---
phase: V24-ade-product-revamp-swarm-observability
plan: 10
subsystem: ui
tags: [portal, canvas-swap, settings, context, memory, appearance, vitest, spec-gap]

# Dependency graph
requires:
  - phase: V24-02
    provides: PortalShell canvas-swap Switch + reviewSlot pattern + PortalView contract
  - phase: V24-09
    provides: 9-item PortalRail (Context/Memory/Settings tabs already navigable)
provides:
  - Context/Settings/Memory portal surfaces wired to real implementations
  - deletion of SurfacePlaceholder + the "Coming in a later V24 plan" copy
  - contextSlot thunk on PortalShell (mirrors reviewSlot)
affects: [V24 verification, product navigation, V24-SPEC §41/86/91 closure]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Slot thunks for App-local data surfaces: Context joins Review as a contextSlot/reviewSlot lazy thunk so PortalShell stays prop-light and App owns focused-pane state."
    - "Settings surface drives the existing appearance store directly (applyAppearanceSettings + saveAppearanceSettings) — no new Tauri command, no new schema."
    - "Honest-signal surface: MemorySurface renders static truth (harness-backed, /memory slash command) with zero fabricated rows, like the Swarm Map missing-signal handling."
---

# V24-10 — Context / Settings / Memory surface wiring (SPEC gap closure)

## What shipped
Closed the V24-SPEC §41/86/91 requirement that Review/Context/Memory/Settings all
"wire to existing panels as-is" this phase. Only Review had been wired; Context,
Memory, and Settings fell through `PortalShell`'s `<Switch>` fallback to
`SurfacePlaceholder`, which hardcoded the now-false **"Coming in a later V24 plan."**

- **Context** — `surfaces/context/ContextSurface.tsx` wraps the shipped
  `components/ContextPanel` (the F4 drawer) at full-canvas, fed by the focused pane's
  `ContextData` via a new `contextSlot` thunk on `PortalShell` (mirrors `reviewSlot`;
  App owns the data, including the `write_context_pins` toggle logic). ContextPanel's
  own empty state covers the no-agent-pane case.
- **Settings** — `surfaces/settings/SettingsSurface.tsx` + `settings.css`, backed by
  the existing appearance store. Real persisted controls: font size, high contrast,
  reduced motion, bell behavior, cursor shape, cursor blink. Each change calls
  `applyAppearanceSettings` (live) then `saveAppearanceSettings` (persist), and the
  surface subscribes to external changes. (The previous `appearanceCommands` palette
  entries were stubs that just re-opened the palette.)
- **Memory** — `surfaces/memory/MemorySurface.tsx`, an honest state: memory is
  harness-backed (`voss/harness/memory_store.py`, the `/memory` slash command) and not
  exposed over the server HTTP API, so there is no live in-app data. Points to the
  real entry point; renders no fabricated rows.
- **PortalShell** — added Match arms for context/settings/memory + the `contextSlot`
  prop; **deleted** `SurfacePlaceholder` and the stale copy. Header comment rewritten.
- **App.tsx** — passes `contextSlot` reusing the same derivation as the F4 ContextPanel
  (`focusedPaneId`/`contextByPaneId`/`agentConfigByPaneId`/`write_context_pins`).

## Tests
- `surfaces/settings/__tests__/SettingsSurface.test.tsx` (3) — reflects committed
  values; a toggle + a select each apply AND persist.
- `surfaces/context/__tests__/ContextSurface.test.tsx` (2) — file rows from
  ContextData (agent pane); empty state on null.
- `__tests__/portalA11y.test.tsx` — extended: Context/Settings/Memory each render a
  `role="tabpanel"` with the right accessible name and do NOT contain the stale string;
  Memory mentions `/memory`.
- `grep "Coming in a later V24 plan"` over non-test `src` → gone; `SurfacePlaceholder`
  → gone. `tsc --noEmit` clean.

## Deviations / decisions
- **Theme + font-family selection deferred** in SettingsSurface. The theme catalog
  lives behind `themes/themeRuntime` (the palette's `switchTheme` uses
  `save_active_theme_id`), not the flat AppearanceSettings store this surface drives.
  Scoped to the AppearanceSettings fields — persisted+applied is the bar. Follow-up
  can add a theme `<select>` sourced from the theme registry.
- **Memory is honest-empty, not functional.** Live in-app memory needs a server
  `/memory` route + typed client (backend work). Tracked as deferred (suggest
  **VADE2-11** / a V21/V23 memory phase) per the plan's Deferred section.

## Pre-existing unrelated red (NOT introduced here)
`src/org/live/__tests__/sidecarCommand.test.ts` (3 failures) — `startVossServe`
reads `h.port` from a handshake the test's `invoke` mock returns as `undefined`.
Fails in isolation; outside this plan's diff; introduced by an earlier concurrent
commit (`1ec50c82`, which added the `port: h.port` devlog). Out of scope for V24-10.
Full suite otherwise: 897 passed / 5 skipped, plus the 13 new/extended tests green.

## Manual smoke (pending, non-blocking)
`npm run tauri dev`: Context shows the focused-pane token heatmap; Settings toggle
high-contrast / change font size → reload → stuck; Memory shows the honest state.
No surface shows "Coming in a later V24 plan."
