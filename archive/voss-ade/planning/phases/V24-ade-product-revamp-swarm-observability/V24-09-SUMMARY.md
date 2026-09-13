---
phase: V24-ade-product-revamp-swarm-observability
plan: 09
subsystem: ui
tags: [portal-rail, workspaces, lucide-solid, accessibility, product-contract, vitest]

# Dependency graph
requires:
  - phase: V24-02
    provides: PortalRail tablist/tab navigation contract
  - phase: V24-03
    provides: canvas-swap shell and demoted layout affordance
  - phase: V24-08
    provides: cross-surface portalA11y phase gate
provides:
  - collapsible Workspaces-first PortalRail contract
  - lucide-solid nav icon dependency verification
  - updated PRODUCT.md and UI-SPEC rail contracts
  - extended portalA11y coverage for toggle, Workspaces, and icon-only accessible names
affects: [V24 verification, product navigation, terminal-first UX]

# Tech tracking
tech-stack:
  added:
    - lucide-solid@1.18.0
  patterns:
    - "Controlled collapsible rail: App owns expanded state and persists it to `voss:portalExpanded`."
    - "Workspaces routes to `activeView='grid'`, reusing the existing canvas-swap path so `GridRoot` stays mounted."
    - "Portal nav icons are lucide-solid SVGs sized 20/currentColor; collapsed icon-only buttons keep aria-label names."

key-files:
  created:
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-09-SUMMARY.md
  modified:
    - apps/voss-app/package.json
    - apps/voss-app/package-lock.json
    - apps/voss-app/src/portal/portalTypes.ts
    - apps/voss-app/src/portal/PortalRail.tsx
    - apps/voss-app/src/portal/portal.css
    - apps/voss-app/src/App.tsx
    - apps/voss-app/src/portal/__tests__/PortalRail.test.tsx
    - apps/voss-app/src/__tests__/portalA11y.test.tsx
    - apps/voss-app/PRODUCT.md
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md

key-decisions:
  - "Workspaces is the first user-facing portal item and names the persistent terminal/tmux grid home."
  - "Expanded rail labels supersede hover tooltip as the primary label reveal."
  - "lucide-solid is pinned exactly at 1.18.0 and imported by icon subpaths."

patterns-established:
  - "PortalRail remains controlled: active view and expansion state are App-owned."
  - "A11y gate verifies the new rail toggle and collapsed icon-only accessible names."

requirements-completed: [VADE2-09]

# Metrics
duration: Wave execution across plan V24-09
completed: 2026-06-15
---

# Phase V24-09: Collapsible Portal Rail Summary

**The left portal now has a persistent-grid home: Workspaces is first, the rail collapses between 48px icon-only and 220px icon+name with persisted state, and the product/a11y contracts verify the new Workspaces-first lucide rail.**

## Implementation Summary
- `PortalRail` is controlled/collapsible via `expanded` and `onToggleExpanded`, with `aria-expanded` plus `Expand portal` / `Collapse portal` labels on the toggle.
- `PORTAL_ITEMS` has 9 items, with `Workspaces` (`id: 'grid'`) first. Selecting it routes through the existing `activeView='grid'` canvas-swap path, so the terminal grid remains the persistent canvas rather than a new surface.
- Portal nav items render lucide-solid SVG icons at size 20/currentColor and include label spans; collapsed icon-only tabs retain non-empty `aria-label` accessible names.
- `App.tsx` persists expansion state in `localStorage` under `voss:portalExpanded`.
- `PRODUCT.md` and `V24-UI-SPEC.md` now describe the 9-item IA, Workspaces vocabulary, collapsible rail geometry, lucide icon contract, push-canvas behavior, and toggle ARIA.

## Files Created/Modified
- `apps/voss-app/src/portal/portalTypes.ts` - Workspaces-first 9-item portal data contract.
- `apps/voss-app/src/portal/PortalRail.tsx` - controlled expand/collapse toggle, lucide icons, label spans, Workspaces routing.
- `apps/voss-app/src/portal/portal.css` - 48px/220px rail widths, expanded label reveal, reduced-motion-safe width transition.
- `apps/voss-app/src/App.tsx` - persisted `voss:portalExpanded` state and PortalRail prop wiring.
- `apps/voss-app/src/portal/__tests__/PortalRail.test.tsx` - unit coverage for data contract, toggle, labels/icons, Workspaces routing, and 9-tab semantics.
- `apps/voss-app/src/__tests__/portalA11y.test.tsx` - cross-surface a11y gate extended for toggle ARIA, Workspaces tab, and collapsed accessible names.
- `apps/voss-app/PRODUCT.md` - IA and locked vocabulary updated for Workspaces and 9 portal items.
- `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md` - rail contract updated for collapsible lucide Workspaces-first behavior.
- `apps/voss-app/package.json` / `apps/voss-app/package-lock.json` - `lucide-solid@1.18.0` pinned and locked.

## Verification
- `cd apps/voss-app && npm test -- portalA11y` -> **5 passed (1 file), 0 failed**.
- `cd apps/voss-app && npm test` -> **879 passed | 5 skipped, 0 failed** (101 files passed | 1 skipped).
- `cd apps/voss-app && npx tsc --noEmit` -> **0 errors**.
- `cd apps/voss-app && npm ls lucide-solid` -> resolves `lucide-solid@1.18.0`.
- `cd apps/voss-app && npm view lucide-solid scripts` -> package scripts inspected; no install/postinstall/prepare script reported.
- Docs gate using `rg` equivalent -> **DOCS_OK** (`Workspaces` in `PRODUCT.md`; `portal-rail--expanded` / `voss:portalExpanded` / `collapsible` in UI-SPEC).
- Read lints for edited Wave 4 files -> **no linter errors found**.

## Threat Checkpoint Notes
- **T-V24-09-SC (supply chain):** mitigated by exact pin `lucide-solid@1.18.0`, lock metadata, `npm ls lucide-solid`, and `npm view lucide-solid scripts` verification. Wave 2 hit an `npm install` caveat involving a `jsdom` / `wireit` prepare issue, but dependency lock metadata and the follow-up package verification succeeded.
- **T-V24-09-CS (canvas-swap integrity):** mitigated by routing Workspaces through `onNavTo('grid')` and the existing display toggle, not a new mount path.
- **T-V24-09-LS (localStorage):** accepted as cosmetic-only state; `voss:portalExpanded` uses a string `=== 'true'` read pattern.
- **T-V24-09-L1 (terminal-first):** strengthened by making the terminal/tmux grid a named first-class destination.

## Manual Smoke Note
Post-build smoke remains manual: run `cd apps/voss-app && npm run tauri dev`, expand/collapse the rail, reload to confirm persistence, verify lucide icons and labels visually, then click **Workspaces** and confirm the existing terminal panes/sessions remain intact.

## User Setup Required
None for automated verification. Manual smoke is recommended before final product sign-off.

## Next Phase Readiness
VADE2-09 is ready for verification: the Workspaces-first collapsible rail is implemented, product/docs contracts match, and the requested full frontend verification is green.

---
*Phase: V24-ade-product-revamp-swarm-observability*
*Completed: 2026-06-15*
