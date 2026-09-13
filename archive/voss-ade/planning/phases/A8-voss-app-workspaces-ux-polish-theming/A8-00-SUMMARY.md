# A8-00 Preflight Summary

**Self-Check: PASSED**

All A8 planning artifacts, A7 command-palette substrate, and A6/A3/A4 source seams verified. A8 Wave 1 implementation may proceed.

## Assertions

| # | Assertion | Status |
|---|-----------|--------|
| 1 | A8-UI-SPEC.md has `status: approved` | PASS |
| 2 | A8-RESEARCH.md contains `## Validation Architecture` | PASS |
| 3 | A8-PATTERNS.md contains `## PATTERN MAPPING COMPLETE` | PASS |
| 4 | A7 registry exists: `apps/voss-app/src/command-palette/registry.ts` | PASS |
| 5 | A7 toast exists: `apps/voss-app/src/command-palette/toast.tsx` | PASS |
| 6 | A7 native menu source exists | PASS |
| 7 | App.tsx: `createCommandRegistry`, single `<GridRoot>`, palette wiring | PASS |
| 8 | GridRoot.tsx: `window.addEventListener('keydown', onKey)` | PASS |
| 9 | sessionPersist.ts: `installCloseSessionSave` | PASS |
| 10 | applyTheme.ts: `applyThemeOverrides` | PASS |
| 11 | A6 persistence seam documented in A8-RESEARCH.md | PASS |

## A7 Surface (explicit)

| Component | Path | Present |
|-----------|------|---------|
| Command registry | `apps/voss-app/src/command-palette/registry.ts` | Yes |
| Toast stack | `apps/voss-app/src/command-palette/toast.tsx` | Yes |
| Native OS menu | `apps/voss-app/src/command-palette/nativeMenu.ts` | Yes |
| Native menu tests | `apps/voss-app/src/command-palette/__tests__/nativeMenu.test.ts` | Yes |

## Source Seam Notes

### App.tsx (composition root)

- Single workspace model: one `<GridRoot>` instance (line ~428), gated by `showGrid()`.
- A7 palette: `createCommandRegistry` + `CommandPalette` overlay + `ToastStack`; capture-phase `onAppKey` routes chords before grid.
- A7 native menu: `setAsAppMenu(registry(), …)` on mount.
- A6 lifecycle: `installStructuralSessionAutosave` + `installCloseSessionSave` installed once in `controllerRef` when grid mounts (single `SessionContext`).

### GridRoot.tsx (global keydown host)

- `window.addEventListener('keydown', onKey)` on mount; removed on cleanup.
- A8 hazard (per RESEARCH): hidden workspaces must not receive split/close/layout keys — requires active-workspace gating when multiple `GridRoot` instances exist.

### sessionPersist.ts (single-workspace save lifecycle)

- `installCloseSessionSave`: one Tauri `onCloseRequested` handler per install; reentry guard after save.
- `installStructuralSessionAutosave`: debounced tree-only save via global `subscribeStructuralChange`.
- A8 refactor required: centralize quit save for all workspaces; per-workspace structural autosave (RESEARCH § Session Persistence Hazards).

### applyTheme.ts (runtime theme seam)

- `applyThemeOverrides(overrides)`: sets CSS custom properties on `:root`; documented for A8 hot-swap (D-06).

### A6 persistence seam (research)

- A8-RESEARCH.md documents A6 single-workspace lifecycle (`installStructuralSessionAutosave`, `installCloseSessionSave`, `saveSession` → `.voss/session.json`, `saveGlobalSession` → `global-session.json`) and required multi-workspace refactor (workspaces.json index, per-workspace sessions, one close handler).

## Automated Verification

```
A8_PREFLIGHT_OK
```

---

*Verified: 2026-05-21 | Plan: A8-00 | Phase: A8-voss-app-workspaces-ux-polish-theming*
