---
phase: F3-budget-token-visualization
plan: 02
type: execute
wave: 2
depends_on:
  - F3-01
files_modified:
  - apps/voss-app/src/pane/pty-ipc.ts
  - apps/voss-app/src/grid/Popover.tsx
  - apps/voss-app/src/grid/BudgetBar.tsx
  - apps/voss-app/src/grid/BudgetPopover.tsx
  - apps/voss-app/src/grid/__tests__/BudgetBar.test.tsx
  - apps/voss-app/src/grid/__tests__/Popover.test.tsx
autonomous: true
requirements:
  - D-06
  - D-07
  - D-08
  - D-09
  - D-10
  - D-13

must_haves:
  truths:
    - "pty-ipc.ts PtyEvent union includes budget_update variant with tokens_used, token_limit, cost_usd, iteration, model"
    - "PtyTransport.handle() routes budget_update events to onBudgetUpdate callback"
    - "BudgetBar renders cost text in $X.XX format and progress bar when token_limit is present"
    - "BudgetBar hides progress bar when token_limit is null (D-07)"
    - "BudgetBar fill color follows 3-tier thresholds: <70% accent-green, 70-90% accent-amber, >=90% accent-red (D-08)"
    - "BudgetBar click calls onClickDetail with the anchor element (D-09)"
    - "Popover dismisses on click-outside and Escape key (D-10)"
    - "BudgetPopover renders 5-row detail card with tokens, limit, model, turns, cost"
  artifacts:
    - path: "apps/voss-app/src/pane/pty-ipc.ts"
      provides: "BudgetState type + budget_update PtyEvent variant + onBudgetUpdate callback"
      contains: "budget_update"
    - path: "apps/voss-app/src/grid/Popover.tsx"
      provides: "Reusable anchor-positioned popover primitive with Esc/outside-click dismiss"
      exports: ["default"]
    - path: "apps/voss-app/src/grid/BudgetBar.tsx"
      provides: "Inline header segment: cost text + conditional bar track + bar fill"
      exports: ["default"]
    - path: "apps/voss-app/src/grid/BudgetPopover.tsx"
      provides: "Popover detail card with 5-row budget info"
      exports: ["default"]
    - path: "apps/voss-app/src/grid/__tests__/BudgetBar.test.tsx"
      provides: "9 unit tests for BudgetBar component"
      contains: "BudgetBar"
    - path: "apps/voss-app/src/grid/__tests__/Popover.test.tsx"
      provides: "4 unit tests for Popover dismiss behavior"
      contains: "Popover"
  key_links:
    - from: "apps/voss-app/src/grid/BudgetBar.tsx"
      to: "apps/voss-app/src/pane/pty-ipc.ts"
      via: "import type { BudgetState } from '../pane/pty-ipc'"
      pattern: "BudgetState"
    - from: "apps/voss-app/src/grid/BudgetPopover.tsx"
      to: "apps/voss-app/src/grid/Popover.tsx"
      via: "import Popover from './Popover'"
      pattern: "Popover"
---

<objective>
Build the frontend components and transport layer for budget visualization: extend pty-ipc.ts with the budget_update event type and callback, create a reusable Popover primitive, BudgetBar inline header segment, and BudgetPopover detail card. All components are tested independently before integration into PaneComponent (F3-03).

Purpose: These components implement D-06 through D-10 and D-13 — the visual presentation layer. They are designed as standalone imports so PaneComponent integration in F3-03 is pure wiring.

Output: 4 new/modified source files (pty-ipc.ts, Popover.tsx, BudgetBar.tsx, BudgetPopover.tsx) and 2 test files with 13 total tests.
</objective>

<execution_context>
@.planning/phases/F3-budget-token-visualization/F3-RESEARCH.md
@.planning/phases/F3-budget-token-visualization/F3-PATTERNS.md
@.planning/phases/F3-budget-token-visualization/F3-UI-SPEC.md
@.planning/phases/F3-budget-token-visualization/F3-CONTEXT.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From apps/voss-app/src/pane/pty-ipc.ts (lines 11-15 — existing PtyEvent union):
```typescript
export type PtyEvent =
  | { type: 'data'; bytes: number[] }
  | { type: 'exit'; code: number }
  | { type: 'fg_process'; name: string }
  | { type: 'title_change'; title: string };
```

From apps/voss-app/src/pane/pty-ipc.ts (lines 27-35 — existing PtyTransportOpts):
```typescript
export interface PtyTransportOpts {
  write: (data: Uint8Array, cb?: () => void) => void;
  onExit?: (code: number) => void;
  onFgProcess?: (name: string) => void;
  onTitle?: (title: string) => void;
  agentPaneId?: string;
  workspacePath?: string;
}
```

From apps/voss-app/src/pane/pty-ipc.ts (lines 62-96 — handle() switch):
```typescript
private handle(ev: PtyEvent): void {
    switch (ev.type) {
      case 'data': { /* coalescing */ break; }
      case 'exit':   this.opts.onExit?.(ev.code); break;
      case 'fg_process': this.opts.onFgProcess?.(ev.name); break;
      case 'title_change': this.opts.onTitle?.(ev.title); break;
    }
}
```

From apps/voss-app/src/grid/DotMenu.tsx (lines 50-63 — dismiss pattern for Popover):
```tsx
const onDocKey = (e: KeyboardEvent) => {
  if (e.key === 'Escape') props.onDismiss();
};
const onDocClick = (e: MouseEvent) => {
  if (root && !root.contains(e.target as Node)) props.onDismiss();
};
onMount(() => {
  document.addEventListener('keydown', onDocKey);
  document.addEventListener('click', onDocClick, true);  // capture phase
});
onCleanup(() => {
  document.removeEventListener('keydown', onDocKey);
  document.removeEventListener('click', onDocClick, true);
});
```

From apps/voss-app/src/grid/__tests__/RestoreBanner.test.tsx (mount helper pattern):
```tsx
let dispose: (() => void) | undefined;
function mount(ui: () => unknown) {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}
afterEach(() => { dispose?.(); dispose = undefined; document.body.innerHTML = ''; });
```

From apps/voss-app/src/styles/variant-b.css — semantic tokens for F3:
```
--bg-2: #171a23    (bar track)
--bg-3: #1f232e    (popover background)
--border: #262b38  (popover border)
--fg-2: #6a7080    (cost text, dim)
--fg-1: #aab0c0    (popover values)
--fg-3: #444a5a    (popover labels)
--accent-green: #6fd28f  (0-70% fill)
--accent-amber: #e8b86c  (70-90% fill)
--accent-red: #e87b7b    (90-100% fill)
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: pty-ipc.ts BudgetState type + budget_update event + Popover.tsx primitive</name>
  <files>apps/voss-app/src/pane/pty-ipc.ts, apps/voss-app/src/grid/Popover.tsx, apps/voss-app/src/grid/__tests__/Popover.test.tsx</files>
  <read_first>
    - apps/voss-app/src/pane/pty-ipc.ts (full file — 169 lines)
    - apps/voss-app/src/grid/DotMenu.tsx (lines 1-70 — dismiss pattern)
    - apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx (lines 1-30 for mount pattern, lines 155-175 for DotMenu dismiss tests)
    - .planning/phases/F3-budget-token-visualization/F3-PATTERNS.md (lines 217-278 for pty-ipc.ts, lines 506-577 for Popover.tsx, lines 692-773 for Popover.test.tsx)
    - .planning/phases/F3-budget-token-visualization/F3-UI-SPEC.md (lines 93-101 for popover structural constants)
  </read_first>
  <action>
    **pty-ipc.ts changes:**
    Add `| { type: 'budget_update'; tokens_used: number; token_limit: number | null; cost_usd: number; iteration: number; model: string }` to the `PtyEvent` union type.

    Add a new exported type alias AFTER the `PtyEvent` type and BEFORE `AgentConfig`:
    `export type BudgetState = { tokens_used: number; token_limit: number | null; cost_usd: number; iteration: number; model: string; };`

    Add `onBudgetUpdate?: (data: BudgetState) => void;` to `PtyTransportOpts` (after `onTitle`).

    Add a new case in `handle()` switch, after the `'title_change'` case:
    `case 'budget_update': this.opts.onBudgetUpdate?.({ tokens_used: ev.tokens_used, token_limit: ev.token_limit, cost_usd: ev.cost_usd, iteration: ev.iteration, model: ev.model }); break;`

    Use explicit field access (not spread) to strip the `type` discriminant from the event before passing to the callback.

    **Popover.tsx (new file per D-10):**
    Create `apps/voss-app/src/grid/Popover.tsx`. Import `onMount, onCleanup` from `solid-js` and `type JSX` from `solid-js`. Interface: `PopoverProps { anchor: HTMLElement; onClose: () => void; children: JSX.Element; }`. The component: declares `let rootRef!: HTMLDivElement`, captures `const rect = props.anchor.getBoundingClientRect()` (once at render), registers `onDocClick` (capture phase — `true` argument on addEventListener, matching DotMenu pattern) that calls `props.onClose()` when click target is outside `rootRef`, registers `onDocKey` that calls `props.onClose()` on Escape key. Uses `onMount`/`onCleanup` to add/remove listeners. Returns a `<div ref={rootRef}>` with `position: 'fixed'`, `top: rect.bottom + 2 + 'px'`, `left: rect.right - 220 + 'px'`, `z-index: 20`, `background: 'var(--bg-3)'`, `border: '1px solid var(--border)'`, `font-size: '11px'`, `min-width: '220px'`. Renders `{props.children}`.

    **Popover.test.tsx (new file):**
    Create `apps/voss-app/src/grid/__tests__/Popover.test.tsx`. Use the `mount` helper pattern from RestoreBanner.test.tsx. Import `fireEvent` from `@testing-library/dom`. 4 tests:
    1. renders children — mount Popover with a `<span data-testid="content">hello</span>` child, assert `querySelector('[data-testid="content"]')` is truthy
    2. calls onClose on Escape keydown (D-10) — mount with `vi.fn()` onClose, fire Escape on document, assert called
    3. calls onClose on outside click (D-10) — mount, create an outside div, click it, assert onClose called
    4. does NOT call onClose on click inside popover — mount with inner button, click it, assert onClose NOT called
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx tsc --noEmit 2>&1 | tail -5 && npm run test -- Popover --reporter=dot 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `npx tsc --noEmit` exits 0 (no type errors from new BudgetState type or Popover component)
    - `npm run test -- Popover` shows 4 tests passing
    - `grep -c "budget_update" apps/voss-app/src/pane/pty-ipc.ts` returns at least 2 (union member + case)
    - `grep -c "BudgetState" apps/voss-app/src/pane/pty-ipc.ts` returns at least 2 (type + opts)
    - `grep -c "onBudgetUpdate" apps/voss-app/src/pane/pty-ipc.ts` returns at least 2 (opts + case)
    - Popover.tsx file exists and exports a default function
    - Popover.test.tsx file exists with 4 test cases
  </acceptance_criteria>
  <done>pty-ipc.ts has BudgetState type, budget_update PtyEvent variant, onBudgetUpdate in opts, and budget_update case in handle(). Popover.tsx is a reusable anchor-positioned popover with Esc/outside-click dismiss. 4 Popover tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: BudgetBar.tsx + BudgetPopover.tsx components + BudgetBar tests</name>
  <files>apps/voss-app/src/grid/BudgetBar.tsx, apps/voss-app/src/grid/BudgetPopover.tsx, apps/voss-app/src/grid/__tests__/BudgetBar.test.tsx</files>
  <read_first>
    - apps/voss-app/src/grid/PaneHeader.tsx (full file — component structure and styling patterns)
    - apps/voss-app/src/grid/DotMenu.tsx (full file — popover card content pattern)
    - apps/voss-app/src/grid/__tests__/RestoreBanner.test.tsx (mount helper + afterEach)
    - apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx (lines 1-30 for imports, fireEvent pattern)
    - .planning/phases/F3-budget-token-visualization/F3-PATTERNS.md (lines 342-431 for BudgetBar, lines 444-502 for BudgetPopover, lines 584-688 for BudgetBar.test.tsx)
    - .planning/phases/F3-budget-token-visualization/F3-UI-SPEC.md (lines 155-230 for layout, lines 280-350 for popover content, lines 355-390 for copywriting)
  </read_first>
  <action>
    **BudgetBar.tsx (new file per D-06, D-07, D-08, D-09, D-13):**
    Create `apps/voss-app/src/grid/BudgetBar.tsx`. Import `Show` from `solid-js` and `type BudgetState` from `../pane/pty-ipc`.

    Three helper functions (module-level, not exported, testable via component rendering):
    - `barFillPct(tokens_used: number, token_limit: number | null): number` — returns `token_limit == null ? 0 : Math.min((tokens_used / token_limit) * 100, 100)`. Clamps to [0,100].
    - `barFillColor(pct: number): string` — returns `'var(--accent-green)'` when pct < 70, `'var(--accent-amber)'` when pct < 90, `'var(--accent-red)'` otherwise. (D-08 exact thresholds.)
    - `formatCost(cost_usd: number): string` — returns `$X.XXXX` when cost_usd < 0.01 (4dp), `$X.XX` when cost_usd < 100 (2dp), `$N` when cost_usd >= 100 (0dp, Math.round). Always $ prefix.

    Interface: `BudgetBarProps { budget: BudgetState; onClickDetail: (anchor: HTMLElement) => void; }`.

    Component: `export default function BudgetBar(props: BudgetBarProps)`. Declares `let buttonRef!: HTMLButtonElement`. Reactive accessors: `const pct = () => barFillPct(...)` and `const hasLimit = () => props.budget.token_limit != null`. Returns a `<button ref={buttonRef} type="button">` with inline styles: `display: 'flex', 'align-items': 'center', gap: '4px', background: 'transparent', border: 'none', padding: '0 4px', 'flex-shrink': 0, cursor: 'default'`. onClick calls `props.onClickDetail(buttonRef)`. Add `aria-label` with budget state text per UI-SPEC accessibility section — include percentage when limit exists, cost-only when no limit. Contains: (1) cost text `<span>` with `color: 'var(--fg-2)', 'font-size': '11px', 'max-width': '44px', 'white-space': 'nowrap', overflow: 'hidden'` showing `formatCost(props.budget.cost_usd)`. (2) `<Show when={hasLimit()}>` wrapping a 48px-wide, 4px-tall bar track div (`background: 'var(--bg-2)'`) containing a `.budget-bar-fill` div with `height: '4px'`, `width: pct() + '%'`, `min-width: pct() > 0 ? '2px' : '0'`, `background: barFillColor(pct())`.

    Add a CSS rule for the bar fill transition. Either add to `apps/voss-app/src/pane/pane.css` or add inline in the component (prefer a `<style>` block or import a small CSS file). The `.budget-bar-fill` class needs `transition: width 150ms ease-out` (D-13). The `html.reduced-motion` global rule from A8 already applies `transition: none !important` to all elements — no F3-specific override needed. If adding to pane.css, just add the one `.budget-bar-fill { transition: width 150ms ease-out; }` rule.

    **BudgetPopover.tsx (new file per D-09, D-10):**
    Create `apps/voss-app/src/grid/BudgetPopover.tsx`. Import `Show` from `solid-js`, `type BudgetState` from `../pane/pty-ipc`, and `Popover` from `./Popover`. Interface: `BudgetPopoverProps { budget: BudgetState; anchor: HTMLElement; onClose: () => void; }`.

    Component wraps `<Popover anchor={props.anchor} onClose={props.onClose}>` with card content. Card has:
    - Header row: "Budget Detail" heading, 11px weight 500, color var(--fg-2), background var(--bg-3), 24px height, 8px horizontal padding.
    - Expanded progress bar row: `<Show when={props.budget.token_limit != null}>` containing an 8px-tall full-width bar track with fill matching the threshold logic.
    - 5 field rows at 24px height each. Label in var(--fg-3) 11px, value in var(--fg-1) 12px:
      - `tokens:` — `{tokens_used.toLocaleString()} / {token_limit.toLocaleString()}` (Show only when token_limit non-null; when null show just `{tokens_used.toLocaleString()}`)
      - `limit:` — `{token_limit.toLocaleString()} tokens` (hidden when token_limit null)
      - `model:` — raw model string, truncated to 24 chars with ellipsis via CSS text-overflow
      - `turns:` — integer iteration count
      - `cost:` — full precision: 4dp when < $0.01, 2dp otherwise

    All text uses var(--font-mono). Row separator: `border-bottom: 1px solid var(--border)`. No border-radius (Variant B rule). Add `role="dialog"` and `aria-label="Budget Detail"` on the popover root for a11y.

    **BudgetBar.test.tsx (new file):**
    Create `apps/voss-app/src/grid/__tests__/BudgetBar.test.tsx`. Use mount helper from RestoreBanner pattern. Import `fireEvent` from `@testing-library/dom`. Define a `BASE: BudgetState` fixture: `{ tokens_used: 500, token_limit: 1000, cost_usd: 0.05, iteration: 3, model: 'claude-3' }`. 9 tests:

    1. renders cost text — assert `el.textContent` contains `$0.05`
    2. renders bar track when token_limit is set — assert `.budget-bar-fill` exists
    3. does not render bar track when token_limit is null (D-07) — assert `.budget-bar-fill` is null
    4. bar fill color is accent-green below 70% (D-08) — 500/1000=50%, assert fill style contains `var(--accent-green)`
    5. bar fill color is accent-amber at 80% (D-08) — tokens_used=800, assert `var(--accent-amber)`
    6. bar fill color is accent-red at 95% (D-08) — tokens_used=950, assert `var(--accent-red)`
    7. calls onClickDetail with button element on click (D-09) — vi.fn spy, fireEvent.click, assert called with HTMLButtonElement
    8. cost format: <$0.01 shows 4dp — cost_usd=0.0012, assert text contains `$0.0012`
    9. bar width clamped to 100% when over-limit — tokens_used=1500/1000, assert fill style width <= 100
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx tsc --noEmit 2>&1 | tail -5 && npm run test -- BudgetBar --reporter=dot 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `npx tsc --noEmit` exits 0
    - `npm run test -- BudgetBar` shows 9 tests passing
    - BudgetBar.tsx exists and has `export default function BudgetBar`
    - BudgetPopover.tsx exists and has `export default function BudgetPopover`
    - `grep -c "var(--accent-green)" apps/voss-app/src/grid/BudgetBar.tsx` >= 1
    - `grep -c "var(--accent-amber)" apps/voss-app/src/grid/BudgetBar.tsx` >= 1
    - `grep -c "var(--accent-red)" apps/voss-app/src/grid/BudgetBar.tsx` >= 1
    - `grep "budget-bar-fill" apps/voss-app/src/grid/BudgetBar.tsx` returns at least 1 line
    - `grep "Popover" apps/voss-app/src/grid/BudgetPopover.tsx` returns at least 1 line (import)
    - `grep 'role="dialog"' apps/voss-app/src/grid/BudgetPopover.tsx` returns 1 line
  </acceptance_criteria>
  <done>BudgetBar renders cost text (4dp/2dp/0dp formatting), conditional progress bar with 3-tier color thresholds, and click-to-detail anchor. BudgetPopover renders a 5-row detail card using the Popover primitive. 9 BudgetBar tests pass covering D-06, D-07, D-08, D-09 and cost formatting.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Channel<PtyEvent> → PtyTransport.handle() | Typed event from Rust; switch-case routes to callbacks |
| BudgetState → BudgetBar/BudgetPopover render | Data rendered as text nodes (JSX escaping); no innerHTML |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-F3-05 | Tampering | BudgetBar/BudgetPopover XSS via model name | mitigate | Model name rendered via JSX text interpolation `{props.budget.model}` — Solid.js auto-escapes text nodes. No `innerHTML`. |
| T-F3-06 | DoS | BudgetBar pct computation | mitigate | `Math.min(pct, 100)` clamp prevents CSS overflow; `token_limit == null` guard prevents NaN/Infinity. |
| T-F3-SC | Tampering | npm/pip/cargo installs | accept | F3 adds zero new dependencies. |
</threat_model>

<verification>
- `cd apps/voss-app && npx tsc --noEmit` — zero type errors
- `cd apps/voss-app && npm run test -- Popover BudgetBar --reporter=dot` — 13 tests pass (4 Popover + 9 BudgetBar)
- All 4 new component files exist under src/grid/ and src/pane/
</verification>

<success_criteria>
pty-ipc.ts routes budget_update events to a typed callback. Popover primitive handles anchor positioning and dismiss. BudgetBar renders cost text and a 3-tier threshold progress bar. BudgetPopover renders a 5-row detail card inside a Popover. All 13 component tests pass.
</success_criteria>

<output>
Create `.planning/phases/F3-budget-token-visualization/F3-02-SUMMARY.md` when done
</output>
