---
phase: A5-voss-app-project-open
plan: 04
type: execute
wave: 3
depends_on: [A5-02]
files_modified:
  - apps/voss-app/src/components/setup/SetupWindow.tsx
  - apps/voss-app/src/components/setup/__tests__/SetupWindow.test.tsx
autonomous: true
requirements: [WS-01, WS-02, WS-05]
must_haves:
  truths:
    - "SetupWindow is a controlled, no-local-state, tokens-only Solid component (PresetSwitcher pattern)"
    - "All three actions are reachable: Open project, Start without project, Open recent (per path)"
    - "Recents block is hidden when the recents list is empty (Solid <Show>)"
    - "All colors come from CSS variables (no raw hex, no 'white' literals)"
    - "Every interactive element has a deterministic aria-label query handle"
    - "SetupWindow surface carries NO L2 vocab (no agent / worktree / reviewer / model / cost / token)"
  artifacts:
    - path: "apps/voss-app/src/components/setup/SetupWindow.tsx"
      provides: "Variant B Solid component for the no-project launch surface"
      contains: "SetupWindowProps"
    - path: "apps/voss-app/src/components/setup/__tests__/SetupWindow.test.tsx"
      provides: "vitest DOM suite for render + interaction + token-discipline"
      contains: "SetupWindow"
---

<objective>
Build the no-project launch surface. Pure presentational Solid component; no signals, no I/O, no Tauri imports — just props in, callbacks out. Mirror `PresetSwitcher.tsx` (110 lines, the freshest controlled-component pattern in the repo) for structure, styling, and aria-label discipline.

Purpose: Give A5-05 a concrete component to mount inside the `<Show fallback={...}>` branch. Decouples visual design from composition so this can be reviewed/styled independently and the App.tsx wave focuses on signal wiring.
Output: A green `pnpm vitest run src/components/setup/__tests__/SetupWindow.test.tsx`, a `tsc --noEmit` clean module, and a tokens-only rendered DOM.
</objective>

<context>
@.planning/phases/A5-voss-app-project-open/A5-SPEC.md
@.planning/phases/A5-voss-app-project-open/A5-CONTEXT.md
@.planning/phases/A5-voss-app-project-open/A5-RESEARCH.md
@.planning/phases/A5-voss-app-project-open/A5-PATTERNS.md
@apps/voss-app/src/components/titlebar/PresetSwitcher.tsx
@apps/voss-app/src/components/titlebar/__tests__/PresetSwitcher.test.tsx

<interfaces>
SetupWindow component contract — A5-05 consumes this.

From apps/voss-app/src/components/setup/SetupWindow.tsx (this plan creates):

  export type SetupWindowProps = {
    recents: string[];
    onOpenProject: () => void;        // App.tsx wires this to pickFolder -> openProject flow
    onOpenRecent: (path: string) => void;
    onStartProjectLess: () => void;
  };

  export default function SetupWindow(props: SetupWindowProps) { ... }

From the analog apps/voss-app/src/components/titlebar/PresetSwitcher.tsx (clone style):

  export type PresetSwitcherProps = {
    activeLayout: ActiveLayout;
    disabled?: boolean;
    onSelect: (preset: LayoutPreset) => void;
  };
  export default function PresetSwitcher(props: PresetSwitcherProps) { ... }

Copy constants imported from apps/voss-app/src/project/projectStorage.ts (A5-03):

  import { OPEN_PROJECT_LABEL, START_PROJECT_LESS_LABEL, RECENTS_HEADING } from '../../project/projectStorage';
</interfaces>
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Token system vs raw color | PresetSwitcher.test.tsx asserts no 'white' literal in rendered styles — A5 must respect the same gate |
| L1 vs L2 surface vocabulary | LAY-08-equivalent rule: setup surface must contain no agent/worktree/reviewer/model/cost/token vocab |
| Recents path display | Recents items are arbitrary user paths; rendering as text is safe, but using them as innerHTML would be XSS — Solid's default JSX text is safe |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A5-L1-LEAK | Information disclosure | L2 vocab on L1 surface | mitigate | Test greps the rendered DOM for forbidden tokens (agent, worktree, reviewer, model, cost, token) and asserts none present |
| T-A5-TOKEN | Tampering | raw color in styles | mitigate | Test clones PresetSwitcher.test.tsx:170-182 — assert rendered style strings contain no `white` literal and no `#` hex |
| T-A5-A11Y | Repudiation | unlabeled interactive controls | mitigate | Every button has an explicit `aria-label`; tests query by aria-label for openButton, projectLessButton, and `recentButton(path)` |
</threat_model>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: Build SetupWindow component + DOM tests</name>
  <files>apps/voss-app/src/components/setup/SetupWindow.tsx, apps/voss-app/src/components/setup/__tests__/SetupWindow.test.tsx</files>
  <read_first>
    - apps/voss-app/src/components/titlebar/PresetSwitcher.tsx (entire file ~110 lines) — controlled, tokens-only, aria-labeled
    - apps/voss-app/src/components/titlebar/__tests__/PresetSwitcher.test.tsx (entire file ~183 lines) — mount/dispose, aria query helpers, token-discipline assertion (lines 170-182), controlled-component test (lines 139-152)
    - apps/voss-app/src/project/projectStorage.ts (from A5-03) — the locked copy constants OPEN_PROJECT_LABEL, START_PROJECT_LESS_LABEL, RECENTS_HEADING
    - .planning/phases/A5-voss-app-project-open/A5-PATTERNS.md §SetupWindow.tsx section — props pattern, no-local-state rule, aria-label list, test cases mapped to SPEC AC #1
    - .planning/phases/A5-voss-app-project-open/A5-SPEC.md Req-1 — setup surface visible on no-project startup
  </read_first>
  <behavior>
    - Test 1: Renders a button with `aria-label="Open project"` (text content also = OPEN_PROJECT_LABEL)
    - Test 2: Renders a button with `aria-label="Start without project"` (text = START_PROJECT_LESS_LABEL)
    - Test 3: With `recents: []`, the recents region is hidden (no element with aria-label starting with "Open recent")
    - Test 4: With `recents: ['/a', '/b', '/c']`, three buttons render with aria-label "Open recent: a", "Open recent: b", "Open recent: c" (basename only in the label; full path shown as text content or title attribute)
    - Test 5: Clicking the Open-project button calls `onOpenProject` exactly once; DOM does not change by itself (controlled-component contract; clone PresetSwitcher.test.tsx:139-152)
    - Test 6: Clicking the Start-without-project button calls `onStartProjectLess` exactly once
    - Test 7: Clicking a recent button calls `onOpenRecent(path)` with the exact path string for that row
    - Test 8: Rendered HTML contains no 'white' literal and no '#' hex color (clone PresetSwitcher.test.tsx:170-182)
    - Test 9: Rendered HTML contains none of the forbidden L2 tokens: 'agent', 'worktree', 'reviewer', 'model', 'cost', 'token' (case-insensitive grep on outerHTML; LAY-08-equivalent gate)
    - Test 10: Two snapshot-like assertions confirm element structure (heading text === RECENTS_HEADING when recents non-empty)
  </behavior>
  <action>
    Create `apps/voss-app/src/components/setup/SetupWindow.tsx`. Clone the structural pattern of `PresetSwitcher.tsx`:

    - Single default export, props type, no `createSignal` (controlled).
    - Import `{ For, Show }` from `solid-js` (matches PresetSwitcher).
    - Import copy constants from `../../project/projectStorage` (A5-03).
    - Render a centered card with three regions:
        1. Heading area — short title and explanatory line (planner discretion per CONTEXT line 53, but no L2 vocab).
        2. Action row — two buttons: Open project (primary) and Start without project (secondary).
        3. Recents block, gated by `<Show when={props.recents.length > 0}>` — heading text = `RECENTS_HEADING`, then a `<For each={props.recents}>` list of buttons.
    - Every button has `aria-label`:
        - "Open project" — opens folder picker
        - "Start without project" — accepts project-less
        - "Open recent: {basename}" — opens that recent path
    - Recents items display the full path as text content (or as a tooltip via `title`) but the aria-label uses only the basename so screen-reader output is short. Compute basename in-component as `path.split('/').pop() || path` (this is a presentation concern, not a Rust contract).
    - All colors via `var(--bg-0)`, `var(--bg-3)`, `var(--fg-0)`, `var(--fg-2)`, `var(--focus)`, `var(--border)`, `var(--accent-amber)` (planner picks from this PresetSwitcher palette; do not introduce new tokens).
    - No `data-tauri-drag-region` on this component — it is in the body slot, not the titlebar.
    - No imports of: `@tauri-apps/*`, `invoke`, `document.*`, `window.*`. The component is pure render + callbacks.

    Create `apps/voss-app/src/components/setup/__tests__/SetupWindow.test.tsx`. Clone `PresetSwitcher.test.tsx`:

    - mount/dispose helper (clone lines 30-41 verbatim).
    - aria-label query helpers: `openButton(root)`, `projectLessButton(root)`, `recentButton(root, path)`.
    - Cover the ten behavior cases above.
    - Token discipline: `expect(root.innerHTML.toLowerCase()).not.toContain('white');` and `expect(root.innerHTML).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);` (clone PresetSwitcher.test.tsx:170-182 structurally — adjusted regex for hex catching).
    - L2-vocab gate: a single `for (const token of ['agent', 'worktree', 'reviewer', 'model', 'cost', 'token']) expect(root.innerHTML.toLowerCase()).not.toContain(token);` assertion. (Note: `token` as a forbidden word will also trip on the literal CSS variable names if you spell `'--token'` in any style — keep all CSS vars from the PresetSwitcher palette and you will be safe. If a false positive surfaces, switch the assertion to whole-word boundaries via regex.)
    - Use Solid's `render` from `solid-js/web` (PresetSwitcher.test.tsx already imports from there).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/components/setup/__tests__/SetupWindow.test.tsx --reporter=dot 2>&1 | tail -30 && pnpm exec tsc --noEmit -p . 2>&1 | tail -10 && grep -q 'export type SetupWindowProps' src/components/setup/SetupWindow.tsx && grep -q 'onOpenProject' src/components/setup/SetupWindow.tsx && grep -q 'onStartProjectLess' src/components/setup/SetupWindow.tsx && grep -q 'onOpenRecent' src/components/setup/SetupWindow.tsx && grep -q 'aria-label' src/components/setup/SetupWindow.tsx && ! grep -nE 'invoke|@tauri-apps' src/components/setup/SetupWindow.tsx && ! grep -niE '\bwhite\b|#[0-9a-f]{3,8}\b' src/components/setup/SetupWindow.tsx | grep -v '^[[:space:]]*//' && echo SETUP_WINDOW_OK</automated>
  </verify>
  <acceptance_criteria>
    - SetupWindow exports the `SetupWindowProps` type matching the `<interfaces>` block exactly.
    - Three actions are present (Open project, Start without project, Open recent per path) with aria-labels.
    - Recents region hidden when `recents.length === 0`.
    - No `createSignal` inside the component (controlled-only contract).
    - No `@tauri-apps/*` or `invoke` imports (pure presentational).
    - No raw `white` literal and no hex color in source (token discipline).
    - Test 9 (L2-vocab gate) passes — no agent/worktree/reviewer/model/cost/token in DOM.
    - `pnpm vitest run src/components/setup/__tests__/SetupWindow.test.tsx` exits 0.
    - `pnpm exec tsc --noEmit -p .` exits 0.
    - `SETUP_WINDOW_OK` prints.
  </acceptance_criteria>
  <done>The setup surface is a self-contained, controlled, tokens-only, L1-vocab Solid component. A5-05 can mount it inside the `<Show fallback={...}>` branch in App.tsx.</done>
</task>

</tasks>

<verification>
Run `pnpm --filter voss-app test -- src/components/setup` and `pnpm --filter voss-app exec tsc --noEmit -p .`.
</verification>

<success_criteria>
- A5-05 can `import SetupWindow from './components/setup/SetupWindow'` and render it with four props.
- The component reads its locked copy from `projectStorage.ts` (single SSOT).
- LAY-08-equivalent rule holds: zero L2 vocab on the L1 setup surface.
- The Variant B token system is the only color source.
</success_criteria>

<output>
Create `.planning/phases/A5-voss-app-project-open/A5-04-SUMMARY.md` with: component line count vs. PresetSwitcher (sanity), screenshot or DOM dump of the rendered surface for the A5-06 visual checkpoint, and any new CSS tokens introduced (should be zero — palette is reused).
</output>
