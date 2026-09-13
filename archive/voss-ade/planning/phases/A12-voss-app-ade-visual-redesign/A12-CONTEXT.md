# Phase A12: voss-app ADE Visual Redesign - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform voss-app from a functional terminal multiplexer into a state-of-the-art Agent Development Environment. Adds a collapsible left sidebar (agent list, sessions, file tree, git log), a "Voss Ignite" warm theme based on the site's design language, a full agent launch modal with per-CLI configuration, branded titlebar, and enhanced pane chrome. Terminals remain the hero element — sidebar is supplementary context, not dominant.

</domain>

<decisions>
## Implementation Decisions

### Sidebar Scope & Sections
- **D-01:** Sidebar has 4 sections in order: **Agents → Sessions → Files → Git**. No Quick Launch section in sidebar body.
- **D-02:** `+ Agent` button lives in the sidebar header (top-right, next to collapse chevron). Opens the agent launch modal.
- **D-03:** Sidebar is **visible by default** on app launch. Users collapse via `⌘⇧B`.
- **D-04:** Fixed width **280px**. No user-resizable drag.
- **D-05:** Files section is **read-only directory tree** — expand/collapse dirs, see file names. Click does nothing (future: open in editor pane).
- **D-06:** Sessions section tracks **agent session start/stop/complete** — separate from Git section which shows recent commits.
- **D-07:** ContextPanel (right-side overlay, `⌘I`) **coexists** with sidebar. Two panels, two purposes — sidebar for agents/files/history, ContextPanel for in-context heatmap.
- **D-08:** Sidebar Agents section shows **only detected agent CLIs** — regular shell panes do not appear.

### Theme Migration
- **D-09:** Create new theme **"Voss Ignite"** as a catalog entry in existing theme system (`themeCatalog.ts`, `themeRuntime.ts`, `schema.ts`). Set as default. Variant B preserved as fallback theme.
- **D-10:** Full **chrome + terminal** retheme — xterm.js foreground/background/cursor/ANSI palette all warm-shifted for cohesive experience.
- **D-11:** **Selective rounding** — 0 radius on panes/grid/panels (density). Small radius (3-6px) on interactive elements: buttons, badges, pills, sidebar items. Cards get 6px.
- **D-12:** **Poppins for display headings only** — app name in titlebar, sidebar section titles, modal headers. Inter stays for UI labels/buttons. JetBrains Mono for terminal + code.
- **D-13:** Warm palette tokens: bg `#0b0a09→#131110→#1a1714→#221f1b`, fg `#f5f1ea→#c4beb5→#8a847a→#5a554d`, accent `#ff5b1f`, border `#1d1a16`/`#2e2924`.

### Agent Launch UX
- **D-14:** `+ Agent` button opens a **centered modal overlay** (like command palette). Dismiss with Escape.
- **D-15:** Modal offers **6 CLI presets**: Claude, Codex, Antigravity (Gemini), OpenCode, **Voss**, Custom.
- **D-16:** **Context-sensitive config panels**: selecting Claude/Codex/Antigravity/OpenCode shows generic agent config (model selector, effort level, plan mode toggle, skip permissions toggle, task prompt). Selecting **Voss** shows Voss-specific config surface (command: chat/do/resume/skill/agent, mode: edit/plan, auth choice, task prompt).
- **D-17:** **Full config modal** scope in A12 — model selector, effort level, mode toggles, task prompt. Not deferred.
- **D-18:** Task prompt field is **optional**. If filled, passed as CLI positional arg. If empty, CLI starts in interactive mode.
- **D-19:** Agent spawns by **splitting from the currently focused pane** (horizontal split). Consistent with existing `⌘D` fork behavior.
- **D-20:** Modal accessible via `+ Agent` button **only** — not via `⌘K` palette. Single entry point.
- **D-21:** Custom CLI entry lets users register any binary with a name and command. Persisted in settings.

### Sidebar ↔ Grid Interaction
- **D-22:** **Bidirectional focus sync** — click agent in sidebar focuses its pane in grid; focusing a pane in grid highlights its agent in sidebar. Sidebar scrolls to active agent if needed.
- **D-23:** **Right-click context menu** on agent items: Stop, Restart, Detach, Copy cost, Focus pane.
- **D-24:** **Live cost/token display** in agent rows — updates reactively from OSC telemetry, no polling.
- **D-25:** **Drag to reorder** agents in sidebar list. Visual preference only — doesn't affect grid layout.

### Status Bar Agent Badge
- **D-26:** Orange pill on right side of status bar: `● 3 agents · $1.42`. Count + total cost, live-updating.
- **D-27:** Clicking badge **toggles sidebar** open/closed. Secondary entry point.

### Titlebar Branding
- **D-28:** Voss logo mark (18-20px inline SVG, `#ff5b1f` fill) placed **left of project name** in centered titlebar area. Layout: traffic lights → gap → logo → project name → preset switcher.
- **D-29:** Project name rendered in **Poppins 500** (was monospace). Other titlebar elements stay Inter/mono.

### Animation & Transitions
- **D-30:** **Subtle and fast** motion level. Sidebar: 200ms slide. Modal: 150ms fade+scale. Pane focus: 100ms border transition. Agent streaming: pulsing dot (CSS keyframes). All respect `prefers-reduced-motion`.

### Claude's Discretion
- Exact ANSI color remapping for xterm warm palette (within the warm family, specific hue choices)
- Agent session tracking data structure (what persists, format)
- File tree implementation details (recursive readdir depth limits, debounce)
- Context menu positioning and dismissal behavior
- Drag-to-reorder implementation (SolidJS-compatible library or custom)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design Source
- `.planning/ADE-REDESIGN.md` — Full design plan with component props, layout diagrams, token reference. Written from sketch 002 Variant A winner.
- `site/app/globals.css` — Site palette source of truth (warm tokens, glow effects, scrollbar, selection)
- `site/public/logo.svg` — Voss logo mark SVG (inline in titlebar/sidebar)

### App Architecture
- `apps/voss-app/src/App.tsx` — Composition root. Layout structure, workspace management, keybinding dispatch. Sidebar integrates here.
- `apps/voss-app/src/grid/GridRoot.tsx` — Grid engine. Sidebar sits outside this; grid resizes via ResizeObserver.
- `apps/voss-app/src/pane/agentDetect.ts` — Agent process detection. Sidebar agent list derives from this.
- `apps/voss-app/src/pane/contextRegistry.ts` — OSC telemetry (cost, tokens). Feeds sidebar live cost and status bar badge.

### Theme System
- `apps/voss-app/src/themes/schema.ts` — Theme JSON schema. "Voss Ignite" must conform.
- `apps/voss-app/src/themes/themeCatalog.ts` — Theme registry. Add Ignite entry here.
- `apps/voss-app/src/themes/themeRuntime.ts` — Runtime theme application. Handles CSS var injection + xterm palette.
- `apps/voss-app/src/styles/variant-b.css` — Current token file (preserved as "Variant B" theme, not overwritten).

### Voss CLI (for launch modal)
- `crates/voss-cli/src/lib.rs` — CLI command definitions (Chat, Do, Resume, Skill, Agent, Doctor). Informs Voss-specific config panel.

### Existing Components (integration points)
- `apps/voss-app/src/components/ContextPanel.tsx` — Right-side panel. Coexists with sidebar (D-07).
- `apps/voss-app/src/components/StatusBar.tsx` — Agent badge lives here (D-26).
- `apps/voss-app/src/components/titlebar/Titlebar.tsx` — Logo + branding changes (D-28, D-29).
- `apps/voss-app/src/components/workspace/WorkspaceTabBar.tsx` — Stays between titlebar and sidebar+grid area.
- `apps/voss-app/src/grid/PaneHeader.tsx` — Pane chrome accent bar changes (from ADE-REDESIGN.md Phase 6).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `agentDetect.ts` + `procRegistry.ts`: Agent detection already identifies Claude/Codex/Gemini by process name. Sidebar agent list derives from `agentConfigByPaneId` in App.tsx.
- `contextRegistry.ts`: OSC telemetry already parses cost/token data per pane. Feeds live sidebar cost display.
- `Popover.tsx`: Existing popover component in grid — reusable for agent context menu.
- `DotMenu.tsx`: Existing dot menu pattern — reusable for sidebar item menus.
- Theme system (`schema.ts`, `themeCatalog.ts`, `themeRuntime.ts`): Full theme infrastructure exists. New theme = new catalog entry + token values.

### Established Patterns
- SolidJS reactive state: `createSignal` + `createMemo` throughout. Sidebar state follows same pattern.
- CSS modules pattern: component `.css` files alongside `.tsx`. Sidebar gets `sidebar.css`.
- `localStorage` for persistence: used for contextPanelOpen. Sidebar collapsed state follows same pattern.
- Command registry: `registry.ts` with `AppContext` handlers. Sidebar toggle adds a new command entry.

### Integration Points
- `App.tsx` layout: Sidebar wraps around the grid area in a flex row. Insertion point: between WorkspaceTabBar and the grid/SetupWindow content.
- `StatusBar.tsx`: Agent badge component added to right side, pulling from same agent data.
- `Titlebar.tsx`: Logo SVG inserted left of project name.
- Keybinding: `⌘⇧B` registered in command registry for sidebar toggle.

</code_context>

<specifics>
## Specific Ideas

- **Warp-style theme picker** (screenshot shared): theme cards with terminal preview thumbnails, filter tabs (All/Dark/Light), search. Reference for future A9 settings phase — not built in A12 but the theme system should be extensible enough to support it.
- **New Agent Session modal** (screenshot shared): Warp-like agent launch modal with CLI tabs, model selector buttons, effort level, Plan Mode / Skip Permissions toggles, task prompt textarea. Voss Ignite orange as accent throughout. "Press Ctrl+Enter to start" affordance.
- **Voss CLI as first-class preset**: When "Voss" selected in launcher, config panel shows Voss-specific options (command: chat/do/resume/skill/agent spawn) instead of generic agent options. Based on `crates/voss-cli/src/lib.rs` Cmd enum.

</specifics>

<deferred>
## Deferred Ideas

- **Warp-style theme picker UI** with card previews, filter tabs, search — belongs in A9 (Settings + Theme) or new phase.
- **File tree click-to-open** — clicking a file opens it in an editor pane. Needs pane-spawn + $EDITOR integration. Future phase.
- **Agent session persistence** — saving/restoring agent sessions across app restart. Depends on F1 (Durable Session Persistence).
- **Pane chrome accent bars** — role-colored 3px left bars on agent pane headers. Documented in ADE-REDESIGN.md Phase 6 but may split as separate plan within A12.

</deferred>

---

*Phase: A12-voss-app-ade-visual-redesign*
*Context gathered: 2026-05-22*
