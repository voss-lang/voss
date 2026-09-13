---
phase: A1-voss-app-tauri-shell
plan: 03
subsystem: ui
tags: [tauri, solid, titlebar, window-controls, platform-gate, drag-region]

requires:
  - phase: A1-02
    provides: Variant B token system on :root; @theme inline Tailwind v4 mapping; get_theme_overrides Rust command + applyTheme.ts seam; App.tsx using var(--bg-0) as paint surface
provides:
  - 22px Variant B custom titlebar (Titlebar.tsx) with project-name placeholder "Voss ADE" + visual-only 4-preset switcher (fanout / pipeline / swarm / watchers, default `pipeline`)
  - Platform-switched window controls (WindowControls.tsx) — MacTrafficLights (3 functional OS-hex circles) on macOS; StubControls (renders null) on linux/win deferred to A10
  - data-tauri-drag-region wired on 2 spacer divs + 1 project-name div (3 total — see "in-flight" note) so drag-to-move works in empty zones AND on the title text (macOS standard behavior); button-bearing children NEVER carry the drag attr (RESEARCH Pitfall 1)
  - PresetSwitcher.tsx — 100% theme-driven (no raw hex; `var(--focus)` active bg, `var(--fg-2)` inactive text, `var(--border)` separator); click updates highlight only, no layout / window change (D-04 visual-only)
  - App.tsx replaced with flex-column root (Titlebar over empty `var(--bg-0)` body)
affects: [A1-04, A2, A3, A5, A10]

tech-stack:
  added: []
  patterns:
    - "Window control IPC pattern: `getCurrentWindow()` from `@tauri-apps/api/window`, gated by `capabilities/default.json` (close / minimize / toggle-maximize / set-fullscreen / is-fullscreen / start-dragging only). Calls scoped to current window — no cross-window or process-wide ops."
    - "Platform abstraction pattern: createSignal<string>('') + onMount(async () => setOs(await platform())) + Show with macos==='macos' guard. linux/win path is a one-line `StubControls` return null — A10 fills in concrete render."
    - "OS-convention hex exception: macOS traffic-light colors `#ff5f57` / `#febc2e` / `#28c840` are the SOLE raw-hex carve-out in components. PresetSwitcher and every theme element use `var(--token)` only."
    - "Drag-region structural rule: the attribute belongs only on inert (no-button-child) elements. Spacer divs need `align-self: stretch` so they fill the full titlebar height — without it, `flex: 1` collapses to 0px tall under `align-items: center` and there is no vertical drag surface."

key-files:
  created:
    - apps/voss-app/src/components/titlebar/WindowControls.tsx
    - apps/voss-app/src/components/titlebar/PresetSwitcher.tsx
    - apps/voss-app/src/components/titlebar/Titlebar.tsx
  modified:
    - apps/voss-app/src/App.tsx (replaced empty-body placeholder with flex-column Titlebar-over-body root; preserved `var(--bg-0)` paint surface from A1-02)

key-decisions:
  - WindowControls platform gate uses `@tauri-apps/plugin-os` `platform()` (NOT `navigator.platform`). Cross-platform reliable, identifier strings stable across Tauri versions.
  - `isFullscreen` state held in a Solid `createSignal<boolean>` and initialized via `await win.isFullscreen()` on mount. Zoom click toggles the signal AND calls `win.setFullscreen(next)`. Two-way sync left to a later wave if a system-initiated fullscreen change becomes a concern.
  - PresetSwitcher is 100% client-side state (one signal). No callback prop, no parent listener — A4 / L2 owns the layout-engine binding when presets become functional.
  - `data-tauri-drag-region` count departed from plan's "exactly 2 spacer divs" guard. Shipped value = 3. The third sits on the project-name div, with `align-self: stretch` + flex centering + NO `pointer-events: none`. Plan's verify guard was over-strict for the user-facing macOS convention that clicking title text drags the window. Documented in the in-flight section so the GSD plan-checker can relax the count rule next iteration.

patterns-established:
  - "Pre-commit verify count rule (drag-region) needs to be a minimum, not an equality. Future plan-checker change: `[ $count -ge 2 ]` over `[ $count -eq 2 ]`, with a separate guard that the OUTER container never carries the attribute."
  - "Spacers used for drag MUST stretch vertically — `align-self: stretch` is the structural fix when parent uses `align-items: center`."

requirements-completed: [SHL-03, SHL-04]

duration: ~30min (including 2 in-flight visual defect patches caught at Task 3 verify)
completed: 2026-05-18
---

# Phase A1, Plan 03: Custom Titlebar + Window Controls + Platform Gate Summary

**Shipped the 22px Variant B custom chrome: macOS traffic lights drive `close` / `minimize` / `setFullscreen`, the project-name placeholder "Voss ADE" centers between two drag-stretched spacers, the visual-only preset switcher (fanout / pipeline / swarm / watchers, default pipeline) lives at the right, and dragging works on every inert zone of the titlebar including the title text.**

## Performance

- **Tasks:** 3 (Tasks 1+2 auto; Task 3 blocking human-verify, 8-item checklist)
- **Files created:** 3 (WindowControls.tsx, PresetSwitcher.tsx, Titlebar.tsx)
- **Files modified:** 1 (App.tsx)
- **Wave:** 3

## Accomplishments

- macOS window controls: red closes, yellow minimizes (Dock restore confirmed), green toggles fullscreen — each scoped to the app window only (T-A1-01 capability-gated).
- Custom titlebar renders the 22px Variant B header with sharp corners (Variant B 0-radius intentional, RESEARCH Pitfall 2).
- Preset switcher visually-only swaps highlight (`pipeline` default) — no layout / window geometry change.
- Drag works on the left spacer, right spacer, AND the title text. Button-bearing children (traffic lights, preset buttons) do NOT drag the window (RESEARCH Pitfall 1).
- linux / Windows path is a single `StubControls` returning null — A10 replaces with concrete rendering (D-04 platform abstraction satisfied at the seam).
- No cost-meter / model indicator / token count appears anywhere on the bar (SHL-03 strict; CONCEPT §10 Q6 hidden in L1 entirely).

## Verify Output

### Tasks 1 + 2 automated
```
=== WindowControls ===  getCurrentWindow + plugin-os + StubControls + setFullscreen + #ff5f57 all present
=== PresetSwitcher ===  pipeline + fanout present; no raw hex; no `cost` string anywhere
=== Titlebar ===  data-tauri-drag-region present, var(--titlebar-height), "Voss ADE", WindowControls + PresetSwitcher imported, no cost/model/token strings
=== App.tsx ===  import Titlebar OK
=== pnpm build ===  ✓ built in 505ms — bundle 6.89 KB CSS + 33.74 KB JS
```

### Task 3 human-verify (8-item checklist)
| # | Step | Result |
|---|------|--------|
| 1 | Preset switch — click each, highlight moves only | PASS |
| 2 | Green = fullscreen toggle | PASS |
| 3 | Yellow = minimize, Dock restore | PASS |
| 4 | Drag empty area between regions | PASS (after spacer `align-self: stretch` fix) |
| 5 | Button click does NOT drag | PASS |
| 6 | 11px mono typography legibility | NOTED (deferred — see "Open Notes" below) |
| 7 | Red = quit | PASS |
| 8 | Multi-monitor | not exercised (single display dev) |

## In-Flight Issues Caught

1. **Drag-region count departure (plan vs ship: 2 vs 3).** Plan A1-03 frontmatter / verify command required EXACTLY 2 `data-tauri-drag-region` attrs (the two spacer divs). During Task 3 verify, user reported clicking the "Voss ADE" title text did NOT drag the window — a deviation from macOS standard (title-text-drag is a Finder / Safari / system convention). Added the drag attribute directly to the project-name div, removed its `pointer-events: none`, and gave it `align-self: stretch` + `display: flex` + `align-items: center` so it fills the 22px height vertically AND remains a valid drag surface. Final count = 3. Plan's "exactly 2" verify rule should become "≥ 2 AND the outer titlebar container must NOT carry the attribute" so the inert title-text drag passes a future checker run.
2. **Drag dead zone (spacer collapse).** Drag worked nowhere on first launch. Cause: `<div data-tauri-drag-region style={{ flex: '1' }} />` siblings under a parent with `align-items: center` collapsed to 0px vertical height — the attribute was correct but the spacer had no clickable surface. Fix: `align-self: 'stretch'` on every drag spacer so they fill the full 22px height. Same fix applied to the project-name drag region. Added the structural rule to the "patterns-established" list so A2/A3 don't repeat it.

## Open Notes / Deferred

- **11px JetBrains Mono legibility on Retina (UI-SPEC HiDPI note).** User flagged uncertainty about text legibility at 11px — A1-UI-SPEC pre-declared this as a non-blocking Dimension-4 verification. Defer the 11px-vs-11.5px verification to A2 once body text appears; if either size proves illegible, revisit token system at that point (variant-b.css has both as named tokens, easy adjust).
- linux / Windows custom window-control rendering — A10 (CONTEXT D-04 explicit deferral).
- Two-way fullscreen state sync (system-initiated F11 / green-button-via-menu) — likely fine in A1 since green is the only zoom path; revisit if A2+ adds menu items.

## Deferred (per plan scope, not regressions)

- `pnpm tauri build` smoke + restrictive CSP hardening + cert-procurement A10 long-pole note — Plan A1-04.
- Multi-monitor verification — opportunistic when a second display is available.
