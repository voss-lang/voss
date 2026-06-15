---
phase: V24-ade-product-revamp-swarm-observability
plan: 09
type: execute
wave: 6
depends_on: ["V24-02", "V24-03", "V24-08"]
autonomous: true
requirements: [VADE2-09]
files_modified:
  - apps/voss-app/package.json
  - apps/voss-app/src/portal/portalTypes.ts
  - apps/voss-app/src/portal/PortalRail.tsx
  - apps/voss-app/src/portal/portal.css
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/portal/__tests__/PortalRail.test.tsx
  - apps/voss-app/src/__tests__/portalA11y.test.tsx
  - apps/voss-app/PRODUCT.md
  - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md
must_haves:
  truths:
    - "The left portal rail is collapsible: a pin/toggle control flips it between 48px (icon-only) and an expanded width (icon + name), and the canvas is pushed (no overlap)"
    - "The expanded/collapsed state persists across reloads via localStorage (mirrors the voss:contextPanelOpen pattern)"
    - "Each nav item renders a lucide-solid icon (not a raw Unicode glyph), sized larger and consistently weighted"
    - "A Workspaces nav item is the first portal item and routes to the persistent terminal/tmux grid canvas (activeView='grid') without remounting GridRoot — grid/pane/PTY identity survives (canvas-swap D-01 intact)"
    - "The full apps/voss-app vitest suite is green; the existing portalA11y tablist/tab/aria contract and the swarmPortal canvas-swap + pane-identity tests stay green"
  artifacts:
    - path: "apps/voss-app/src/portal/PortalRail.tsx"
      provides: "Collapsible rail: controlled expanded prop + toggle, lucide icons, label spans, Workspaces item"
      contains: "lucide-solid"
    - path: "apps/voss-app/src/portal/__tests__/PortalRail.test.tsx"
      provides: "Behavior tests: toggle aria-expanded + onToggleExpanded, per-item svg icon, label visibility by class, Workspaces→onNavTo('grid')"
      contains: "aria-expanded"
    - path: "apps/voss-app/src/portal/portalTypes.ts"
      provides: "PORTAL_ITEMS with Workspaces (id 'grid') first; PortalView unchanged (grid already a member)"
      contains: "Workspaces"
  key_links:
    - from: "apps/voss-app/src/portal/PortalRail.tsx"
      to: "the persistent terminal grid canvas"
      via: "Workspaces item onNavTo('grid') → App setActiveView('grid') → existing canvas-swap display toggle"
      pattern: "grid"
    - from: "apps/voss-app/src/App.tsx"
      to: "localStorage persistence"
      via: "voss:portalExpanded read on init + written on toggle"
      pattern: "voss:portalExpanded"
---

<objective>
Fix the left portal rail UX (VADE2-09). Today the rail is a fixed 48px icon-only
strip with raw Unicode glyphs, no labels, no way to read what each item is, and no
explicit way back to the terminal grid. Make it:

1. **Collapsible** — a pin/toggle control flips the rail between collapsed (48px,
   icon-only) and expanded (icon + name), persisted across reloads. Expanding
   pushes the canvas (flex sibling widens; no overlap, no float).
2. **Better icons** — replace the 8 Unicode glyphs with `lucide-solid` icons,
   larger and consistently stroke-weighted, token-colored via `currentColor`.
3. **Workspaces tab** — add a Workspaces item (FIRST) that surfaces the persistent
   terminal/tmux grid we keep mounted for multi-session agentic work. It routes
   through the existing canvas-swap path (`activeView='grid'`) so GridRoot is NOT
   remounted and pane/PTY identity survives.

This closes the "feels like a terminal spawner, no visible nav home" gap and the
"can't tell what the icons mean" gap, while preserving the L1 terminal-first
guarantee (Workspaces makes the terminal grid an explicit, named destination).

Output: a collapsible, lucide-iconed PortalRail with a Workspaces item; persisted
expand state; updated PRODUCT.md IA + UI-SPEC §1 contract; green full suite.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@apps/voss-app/PRODUCT.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md

<interfaces>
<!-- Verified from codebase 2026-06-15. -->

Current state (ground truth):
- `src/portal/portalTypes.ts`: `PortalView` union already INCLUDES `'grid'`.
  `PORTAL_ITEMS` is 8 items (grid intentionally excluded). `PortalItem = {id,label,glyph}`.
- `src/portal/PortalRail.tsx`: CONTROLLED component (Pitfall 5 — it does NOT own
  activeView; App owns it). Props: activeView, onNavTo, onOpenComposer,
  activeLayout, layoutDisabled, onLayoutSelect. Renders `<nav aria-label="Voss portal">`
  → `.portal-tablist[role=tablist]` → per item `<button role="tab" aria-selected
  aria-label title><span aria-hidden>{glyph}</span></button>`, then the ask trigger
  + layout menu.
- `src/portal/portal.css`: `.portal-rail{width:48px}`, `.portal-item{height:48px;
  font-size:16px}`, active = `box-shadow: inset 2px 0 0 var(--focus)`.
- `src/App.tsx`:
  - `const [activeView, setActiveView] = createSignal<PortalView>('grid')` (line ~297).
  - localStorage prefs pattern (lines ~320-339): `voss:contextPanelOpen`,
    `voss:sidebarCollapsed` — init `localStorage.getItem(k)==='true'`, toggle writes
    `localStorage.setItem(k, String(next))`. REUSE this exact shape for `voss:portalExpanded`.
  - PortalRail mounted at ~1514 with `activeView={activeView()} onNavTo={setActiveView}`.
    The rail is a flex-row sibling of the work-surface column → widening the rail
    pushes the canvas automatically (no overlay needed).
  - Grid canvas div at ~1550: `display: activeView()==='grid' ? 'flex' : 'none'`
    (canvas-swap; GridRoot stays mounted). Selecting Workspaces = setActiveView('grid')
    flips this back to flex — the SAME mechanism already used by onClose/back paths.
- `src/portal/PortalShell.tsx`: `<Show when={activeView!=='grid'}>` — when grid is
  active the portal surface renders nothing, so a Workspaces item (id 'grid') never
  needs a Switch/Match arm or a placeholder. labelFor('grid') returns 'Workspaces'
  but is never rendered (grid short-circuits). No PortalShell change required.

lucide-solid API (verified via context7 /lucide-icons/lucide, package not yet installed):
- Install: `npm install lucide-solid` (pin the exact resolved version in package.json).
- Import: `import { Network } from 'lucide-solid'` → Solid component rendering `<svg>`.
- PREFER subpath imports for vite-dev perf (barrel is ~1700 modules):
  `import Network from 'lucide-solid/icons/network'`.
- Props: `size` (number, default 24), `color` (default `currentColor`),
  `stroke-width`/`strokeWidth` (default 2), `absoluteStrokeWidth`, plus any SVG attr
  (`class`, `aria-hidden`, etc.). Use `size={20}` (or 22), `aria-hidden="true"`,
  color via `currentColor` so existing `.portal-item` color tokens still drive it.

Suggested lucide icon mapping (executor may substitute equivalents):
  Workspaces → SquareTerminal (or LayoutGrid)   Overview → LayoutDashboard
  Tasks → ListChecks                            Agents → Bot
  Swarm Map → Network                           Review → ClipboardCheck
  Context → FileText                            Memory → Brain
  Settings → Settings                           collapse/expand → PanelLeftClose / PanelLeftOpen
  ask trigger (optional swap, else keep ❯) → Sparkles

Test harness analogs:
  src/__tests__/portalA11y.test.tsx (V24-08 — tauri-mock + mount/dispose; extend here)
  src/surfaces/tasks/__tests__/TasksSurface.test.tsx (mount/dispose pattern)
  src/__tests__/swarmPortal.test.tsx (canvas-swap + pane-identity round-trip — MUST stay green)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Workspaces item + portalTypes contract (RED → GREEN)</name>
  <files>apps/voss-app/src/portal/portalTypes.ts, apps/voss-app/src/portal/__tests__/PortalRail.test.tsx</files>
  <read_first>
    - apps/voss-app/src/portal/portalTypes.ts (current 8-item PORTAL_ITEMS + the "grid intentionally absent" comment to revise)
    - apps/voss-app/src/portal/PortalShell.tsx (confirm grid short-circuit means no Match arm needed)
  </read_first>
  <action>
    RED: In `PortalRail.test.tsx`, add a describe asserting the data contract:
    `PORTAL_ITEMS[0]` is `{ id: 'grid', label: 'Workspaces', … }`; `PORTAL_ITEMS.length === 9`;
    all `id`s unique; every item still has a non-empty `label`.
    GREEN: In `portalTypes.ts`, prepend `{ id: 'grid', label: 'Workspaces', glyph: '▦' }`
    to `PORTAL_ITEMS` (keep `glyph` for the labelFor fallback + non-icon callers).
    Update the header comment: 'grid' is now the FIRST portal item (Workspaces) AND
    remains the canvas-swap default — selecting Workspaces routes back to the grid
    via activeView='grid' (no remount). Keep `PortalView` unchanged (grid is already
    a member). Delete the trailing dangling comment line (line 41) if it is orphaned.
    Then grep the test suite for any assertion of `PORTAL_ITEMS.length === 8` or
    '8 items' / '8 navigable' and update them to 9 (record each in the SUMMARY).
  </action>
  <verify>
    <automated>cd apps/voss-app && npm test -- PortalRail 2>&1 | tail -12; grep -rn "length === 8\|length).toBe(8\|8 items\|8 navigable" src --include="*.ts" --include="*.tsx" | grep -i portal || echo "no stale 8-counts"</automated>
  </verify>
  <acceptance_criteria>
    - PORTAL_ITEMS has 9 items, Workspaces (id 'grid') first, unique ids, all labelled.
    - No test still asserts a portal count of 8.
    - PortalView union unchanged; PortalShell needs no new Match arm.
  </acceptance_criteria>
  <done>Workspaces is a first-class portal item routing to the grid canvas; contract tests green.</done>
</task>

<task type="auto">
  <name>Task 2: Collapsible rail + lucide icons + labels (RED → GREEN)</name>
  <files>apps/voss-app/package.json, apps/voss-app/src/portal/PortalRail.tsx, apps/voss-app/src/portal/portal.css, apps/voss-app/src/portal/__tests__/PortalRail.test.tsx</files>
  <read_first>
    - apps/voss-app/src/portal/PortalRail.tsx (controlled-component shape, Pitfall 5)
    - apps/voss-app/src/portal/portal.css (rail/item geometry to extend)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md §1 (rail contract)
  </read_first>
  <action>
    Install `lucide-solid` (`npm install lucide-solid`) and PIN the exact resolved
    version in package.json (no caret drift). Use subpath imports
    (`lucide-solid/icons/<name>`) for the per-item icons + the toggle icons.

    RED (extend PortalRail.test.tsx, tauri-mock harness, mount/dispose):
    - Toggle: PortalRail renders a collapse/expand `<button>` with `aria-label`
      matching /(Collapse|Expand) (the )?portal/ and `aria-expanded` reflecting the
      `expanded` prop; clicking it calls `onToggleExpanded`.
    - Push-canvas state: when `expanded` is false the `.portal-rail` element does NOT
      carry `portal-rail--expanded`; when true it DOES (the CSS width swap; jsdom does
      not compute layout so assert on the class, not px).
    - Icons: each `.portal-item` contains an `<svg>` (lucide), 9 total; no raw glyph
      text node leaks as the only accessible content (aria-label still present).
    - Labels: a `.portal-item__label` span per item with `textContent === item.label`
      exists in the DOM in BOTH states (CSS hides it when collapsed; assert presence +
      text, plus that the expanded class gates visibility).
    - Workspaces routing: clicking the Workspaces button calls `onNavTo('grid')`.
    - Regression: tablist still has `role="tablist"`, 9 `role="tab"` items each with
      `aria-selected` ∈ {true,false} and a non-empty `aria-label`.

    GREEN (PortalRail.tsx):
    - Add props `expanded?: boolean` and `onToggleExpanded?: () => void` (controlled —
      App owns the signal, Pitfall 5).
    - Root `<nav class={`portal-rail${expanded ? ' portal-rail--expanded' : ''}`}>`.
    - A header toggle button (top of rail): lucide PanelLeftClose (expanded) /
      PanelLeftOpen (collapsed), `aria-label={expanded ? 'Collapse portal' : 'Expand portal'}`,
      `aria-expanded={String(!!expanded)}`, `onClick={() => props.onToggleExpanded?.()}`.
    - Per nav item: render `<Icon size={20} stroke-width={1.75} aria-hidden="true" />`
      from a `Record<PortalView, Component>` icon map (kept in PortalRail.tsx — keep
      portalTypes data-only), plus `<span class="portal-item__label">{item.label}</span>`.
      Keep `role="tab" aria-selected aria-label title` exactly as today.
    - Show labels on the ask trigger + layout button too when expanded (optional polish).
    GREEN (portal.css):
    - `.portal-rail--expanded { width: 220px; }`; `.portal-item__label { display:none }`
      by default, `.portal-rail--expanded .portal-item__label { display:inline }`.
    - Expanded items: `justify-content:flex-start; gap:12px; padding:0 14px`. Bump icon
      box / item to read larger (icon 20px; keep 48px item height).
    - Rail width `transition: width 120ms ease` — the existing global reduced-motion
      kill switch must disable it; if no global transition kill covers the rail, wrap
      the transition in `@media (not (prefers-reduced-motion: reduce))` (A8 discipline).
    - Add `.portal-toggle` button styles (full-width, --fg-3, hover --bg-2, focus ring).
  </action>
  <verify>
    <automated>cd apps/voss-app && npm test -- PortalRail 2>&1 | tail -15; npm ls lucide-solid 2>&1 | tail -3; npx tsc --noEmit 2>&1 | tail -8 && echo TSC_OK</automated>
  </verify>
  <acceptance_criteria>
    - lucide-solid installed + pinned; `npm ls lucide-solid` resolves the official package.
    - Toggle button: correct aria-label/aria-expanded; click calls onToggleExpanded.
    - 9 nav items each render a lucide `<svg>` + a `.portal-item__label` with the item name.
    - `.portal-rail--expanded` gates width + label visibility; collapsed stays 48px icon-only.
    - Workspaces click calls onNavTo('grid'); tablist/tab/aria contract intact; tsc clean.
  </acceptance_criteria>
  <done>The rail collapses/expands with lucide icons + readable labels; controlled by props.</done>
</task>

<task type="auto">
  <name>Task 3: App wiring — persisted expand state + pass-through (RED → GREEN)</name>
  <files>apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/App.tsx lines ~320-339 (contextPanelOpen/sidebarCollapsed persistence pattern to mirror)
    - apps/voss-app/src/App.tsx ~1514 (PortalRail mount)
  </read_first>
  <action>
    Add `portalExpanded` state mirroring the existing pattern EXACTLY:
    `const [portalExpanded, setPortalExpanded] = createSignal(localStorage.getItem('voss:portalExpanded') === 'true');`
    and `const togglePortalExpanded = () => setPortalExpanded(prev => { const next = !prev; localStorage.setItem('voss:portalExpanded', String(next)); return next; });`
    Pass `expanded={portalExpanded()} onToggleExpanded={togglePortalExpanded}` to
    `<PortalRail>`. Workspaces routing needs NO new wiring — `onNavTo={setActiveView}`
    already handles `onNavTo('grid')`.
    Verification here is the full regression (App is large; behavior is covered by the
    PortalRail unit tests + the persistence shape mirrors a tested pattern). Confirm the
    canvas-swap + pane-identity invariants by re-running swarmPortal.
  </action>
  <verify>
    <automated>cd apps/voss-app && grep -n "voss:portalExpanded" src/App.tsx; grep -n "expanded={portalExpanded" src/App.tsx; npm test -- swarmPortal 2>&1 | tail -8</automated>
  </verify>
  <acceptance_criteria>
    - App owns `portalExpanded` persisted to `voss:portalExpanded` (init + toggle write), mirroring contextPanelOpen.
    - PortalRail receives `expanded` + `onToggleExpanded`.
    - swarmPortal canvas-swap + pane-identity tests stay green (Workspaces routes via the existing grid display toggle; GridRoot not remounted).
  </acceptance_criteria>
  <done>Expand state persists across reloads and drives the rail; grid identity preserved.</done>
</task>

<task type="auto">
  <name>Task 4: a11y gate extension + contract docs + full regression</name>
  <files>apps/voss-app/src/__tests__/portalA11y.test.tsx, apps/voss-app/PRODUCT.md, .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md</files>
  <read_first>
    - apps/voss-app/src/__tests__/portalA11y.test.tsx (V24-08 gate to extend)
    - apps/voss-app/PRODUCT.md §Information Architecture + §Locked Vocabulary
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md §1 Left Portal Rail
  </read_first>
  <action>
    Extend `portalA11y.test.tsx` (the single pre-verify a11y gate): assert the rail
    exposes a toggle `<button>` with `aria-expanded` + an Expand/Collapse `aria-label`,
    that a Workspaces tab is present (`aria-label="Workspaces"`), and that collapsed
    icon-only items keep an accessible name (aria-label present even when the label span
    is visually hidden). Keep the existing tablist/dialog/button-row/reduced-motion
    assertions passing (now 9 tabs).
    Update contracts:
    - `PRODUCT.md` §Information Architecture: the portal now has 9 items — add
      **Workspaces** at the top (surfaces the persistent terminal/tmux grid; the L1
      home), note it maps to the grid canvas (canvas-swap, not a new surface). Add
      "Workspaces" to §Locked Vocabulary (user-facing nav label for the terminal grid).
    - `V24-UI-SPEC.md` §1 Left Portal Rail: replace the fixed-48px/Unicode-glyph spec
      with the collapsible contract — collapsed 48px (icon-only) ↔ expanded 220px
      (icon + name) via a toggle, persisted (`voss:portalExpanded`), push-canvas; icons
      are lucide-solid (size 20, currentColor); Workspaces is item 1. Keep the ARIA
      block; add the toggle's `aria-expanded`/`aria-label`. Note the rail supersedes the
      previously-specced hover tooltip as the primary label-reveal.
    Run the FULL suite + tsc. Document any pre-existing unrelated red as out-of-scope.
    Create `V24-09-SUMMARY.md`.
  </action>
  <verify>
    <automated>cd apps/voss-app && npm test -- portalA11y 2>&1 | tail -12; npm test 2>&1 | tail -20; npx tsc --noEmit 2>&1 | tail -5 && echo TSC_OK; grep -qi "Workspaces" PRODUCT.md && grep -q "portal-rail--expanded\|voss:portalExpanded\|collapsible" ../../.planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md && echo DOCS_OK</automated>
  </verify>
  <acceptance_criteria>
    - portalA11y asserts the toggle's aria-expanded + Expand/Collapse aria-label, a Workspaces tab, and collapsed-state accessible names; existing assertions pass with 9 tabs.
    - PRODUCT.md IA lists Workspaces (mapped to the grid canvas) + §Locked Vocabulary has "Workspaces".
    - UI-SPEC §1 documents the collapsible rail (geometry, persistence, lucide icons, Workspaces item, toggle ARIA).
    - `npm test` full suite green; `tsc --noEmit` clean; DOCS_OK printed.
  </acceptance_criteria>
  <done>The a11y gate covers the new controls; contracts match the build; full suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| npm registry → build | `lucide-solid` is a NEW third-party dependency pulled at install. |
| portal nav → terminal grid canvas | The Workspaces item routes user navigation back into the live PTY/terminal grid (the L1 surface). |
| localStorage → UI state | `voss:portalExpanded` is read on boot to set the initial rail width. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V24-09-SC | Tampering (supply chain) | lucide-solid install | mitigate | **Package-legitimacy checkpoint:** `lucide-solid` is the official SolidJS port from the `lucide-icons` org (MIT, high reputation, used widely). Pin the EXACT resolved version in package.json (no caret). After install, confirm `npm ls lucide-solid` resolves the official package and that it ships no surprising postinstall script (`npm view lucide-solid scripts`). Subpath imports only — no eval/runtime codegen. This is the single [NEW-DEP] gate for this plan. |
| T-V24-09-CS | Tampering (canvas-swap integrity) | Workspaces → activeView='grid' | mitigate | Workspaces reuses `onNavTo('grid')` → the EXISTING display:flex/none toggle; GridRoot is NOT remounted and no new mount path is added. Verified by swarmPortal canvas-swap + pane-identity tests staying green (re-run in Task 3). |
| T-V24-09-L1 | Verification integrity (L1 baseline) | terminal-first guarantee | mitigate | The change strengthens L1 (terminal grid becomes an explicitly named destination). Full suite incl. existing grid/pane/terminal tests must stay green; the V24-08 terminal-first checklist is unaffected (no PTY/grid behavior change). |
| T-V24-09-LS | Tampering | localStorage `voss:portalExpanded` | accept | String `=== 'true'` compare (no JSON.parse), mirroring the existing `voss:contextPanelOpen`/`voss:sidebarCollapsed` prefs — a tampered value only changes initial rail width. Cosmetic, no escalation. |

No HIGH-severity threats. The only new attack surface is the single dependency, gated by the legitimacy checkpoint above.
</threat_model>

<verification>
- `npm test` full suite green, including the extended PortalRail + portalA11y tests and the unchanged swarmPortal canvas-swap / pane-identity tests.
- `npm test -- PortalRail` and `npm test -- portalA11y` GREEN.
- `npx tsc --noEmit` → 0 errors.
- `npm ls lucide-solid` resolves the pinned official package; `git diff apps/voss-app/package.json` shows exactly one new dependency, version-pinned.
- `grep "voss:portalExpanded" src/App.tsx` present; PRODUCT.md + UI-SPEC updated (DOCS_OK).
</verification>

<success_criteria>
The portal rail collapses/expands via a persisted toggle (48px icon-only ↔ 220px icon+name,
pushing the canvas); the 9 nav items render larger, consistent lucide-solid icons with
readable names when expanded; a Workspaces item (first) surfaces the persistent terminal/tmux
grid through the existing canvas-swap path without remounting GridRoot; the full vitest suite,
the a11y gate, and the canvas-swap identity tests are all green; PRODUCT.md and UI-SPEC §1
reflect the new contract (VADE2-09 met).
</success_criteria>

<output>
Create `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-09-SUMMARY.md` when done.

## Manual smoke (post-build, not a blocking checkpoint)
Run `npm run tauri dev` and confirm: the rail toggle expands/collapses and the choice
survives a reload; the lucide icons are visibly larger/cleaner than the old glyphs; clicking
**Workspaces** returns to the live terminal grid with panes/sessions intact.
</output>
