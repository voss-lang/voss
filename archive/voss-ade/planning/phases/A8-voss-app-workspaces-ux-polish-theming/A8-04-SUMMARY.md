# A8-04 Summary

**Self-Check: PASSED**

Live theme/font/cursor/bell settings, accessibility overlays, transitions, and pane chrome polish wired.

## Tasks

| Task | Status | Verification |
|------|--------|--------------|
| 1 — Theme runtime + xterm hot-swap | PASS | `pnpm test --run src/themes src/pane` |
| 2 — Font/cursor/bell/high-contrast settings | PASS | `pnpm test --run src/appearance src/pane`; `cargo test fonts appearance` |
| 3 — CSS transitions + pane chrome polish | PASS | PaneChrome + themes tests; `pnpm build` |

## Deliverables

### Theme runtime (`apps/voss-app/src/themes/themeRuntime.ts`)

- Terminal registry (scrollbackRegistry pattern)
- `applyThemeToRuntime` — CSS vars via `applyThemeOverrides()` + live `term.options.theme` updates (no remount)
- Preview stack: `previewTheme` / `cancelThemePreview` / `commitThemePreview`
- `themeToXtermTheme` — cssVars + ANSI → xterm ITheme

### Appearance settings (`apps/voss-app/src/appearance/`)

- `types.ts`, `settings.ts` — font, cursor, bell, high contrast, reduced motion; 10px font floor
- `fontStorage.ts` — system font list + JetBrains Mono fallback
- `appearance.rs` + `fonts.rs` (Rust) — settings.json persistence; `list_system_fonts`
- Tauri: `load_appearance_settings`, `save_appearance_settings`, `list_system_fonts`

### Pane + chrome

- **PaneComponent** — theme/appearance subscribe; no hardcoded xterm hex; bell behaviors (visual/audible/none/badge)
- **index.css** — reduced-motion kill switch (OS + user class); allowed transition durations
- **pane.css** — theme-aware scrollbars; bell flash; focus transitions
- **DragHandle / SplitNode** — token-only hover/focus; stable pane dimensions
- **PaneChrome.test.tsx** — reduced motion, stable headers, no badge chrome

## Requirements covered

UXP-12, UXP-14, UXP-15, UXP-16, UXP-17, UXP-18, UXP-19, UXP-21, UXP-22, UXP-23, UXP-24

## Verification totals

- Frontend: **498 tests** passed
- Rust: fonts (2) + appearance (2)
- Production build: OK

## Next

**A8-05** — platform-native window chrome (vibrancy, mica/acrylic, Linux WM hints).

---

*Completed: 2026-05-21 | Plan: A8-04 | Phase: A8-voss-app-workspaces-ux-polish-theming*
