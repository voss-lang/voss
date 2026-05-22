---
phase: F3-budget-token-visualization
plan: 03
type: execute
wave: 3
depends_on:
  - F3-01
  - F3-02
files_modified:
  - apps/voss-app/src/pane/PaneComponent.tsx
  - apps/voss-app/src/pane/pane.css
autonomous: false
requirements:
  - D-05
  - D-11
  - D-12

must_haves:
  truths:
    - "PaneComponent has a local budget signal initialized to null (D-12)"
    - "PtyTransport onBudgetUpdate callback sets the budget signal"
    - "BudgetBar renders in PaneComponent header between spacer and menu button, visible only for agent panes with non-null budget (D-05)"
    - "BudgetPopover opens on BudgetBar click and dismisses on Esc/outside-click (D-09/D-10)"
    - "Shell panes show no budget HUD (D-05)"
    - "Budget state resets to null on pane mount — no persistence (D-11)"
    - "Bar fill has 150ms CSS transition with reduced-motion kill switch (D-13)"
  artifacts:
    - path: "apps/voss-app/src/pane/PaneComponent.tsx"
      provides: "Budget signal, transport callback, BudgetBar/BudgetPopover integration"
      contains: "BudgetBar"
    - path: "apps/voss-app/src/pane/pane.css"
      provides: ".budget-bar-fill transition rule"
      contains: "budget-bar-fill"
  key_links:
    - from: "apps/voss-app/src/pane/PaneComponent.tsx"
      to: "apps/voss-app/src/grid/BudgetBar.tsx"
      via: "import BudgetBar from '../grid/BudgetBar'"
      pattern: "BudgetBar"
    - from: "apps/voss-app/src/pane/PaneComponent.tsx"
      to: "apps/voss-app/src/grid/BudgetPopover.tsx"
      via: "import BudgetPopover from '../grid/BudgetPopover'"
      pattern: "BudgetPopover"
    - from: "apps/voss-app/src/pane/PaneComponent.tsx"
      to: "apps/voss-app/src/pane/pty-ipc.ts"
      via: "onBudgetUpdate callback in PtyTransport constructor"
      pattern: "onBudgetUpdate"
---

<objective>
Wire the budget visualization into PaneComponent: add local budget signal, connect PtyTransport's onBudgetUpdate callback, mount BudgetBar in the inline header, mount BudgetPopover on click, and add the CSS transition rule. Verify the full pipeline with a human checkpoint.

Purpose: This is the integration plan that connects the Rust/Python backend (F3-01) and the frontend components (F3-02) into the live application. After this plan, budget data flows from harness through PTY reader to the visual HUD.

Output: Modified PaneComponent.tsx with budget integration, pane.css with transition rule, and human-verified live HUD.
</objective>

<execution_context>
@.planning/phases/F3-budget-token-visualization/F3-RESEARCH.md
@.planning/phases/F3-budget-token-visualization/F3-PATTERNS.md
@.planning/phases/F3-budget-token-visualization/F3-UI-SPEC.md
@.planning/phases/F3-budget-token-visualization/F3-CONTEXT.md
@.planning/phases/F3-budget-token-visualization/F3-01-SUMMARY.md
@.planning/phases/F3-budget-token-visualization/F3-02-SUMMARY.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From apps/voss-app/src/pane/PaneComponent.tsx (lines 84-94 — existing signals block):
```typescript
const [focused, setFocused] = createSignal(true);
const [dot, setDot] = createSignal<DotState>('loading');
const [proc, setProc] = createSignal('');
const [pendingPaste, setPendingPaste] = createSignal<string | null>(null);
const [showFind, setShowFind] = createSignal(false);
const [exitCode, setExitCode] = createSignal<number | null>(null);
const [appearance, setAppearance] = createSignal<AppearanceSettings>(DEFAULT_APPEARANCE_SETTINGS);
const [bellBadge, setBellBadge] = createSignal(false);
const [headerFlash, setHeaderFlash] = createSignal(false);
```

From apps/voss-app/src/pane/PaneComponent.tsx (lines 310-327 — transport constructor):
```typescript
transport = new PtyTransport({
  write: (data, cb) => t.write(data, cb),
  onExit: (code) => { setDot('exited'); setExitCode(code); },
  onFgProcess: (name) => setProc(name),
  onTitle: (title) => { lastOscTitleAt = Date.now(); setProc(title); },
  ...(props.agentConfig ? { agentPaneId: props.id, workspacePath: props.workspacePath } : {}),
});
```

From apps/voss-app/src/pane/PaneComponent.tsx (lines 456-481 — inline header JSX):
```tsx
<div ref={headerRef} class={`pane-header${headerFlash() ? ' bell-flash' : ''}`}>
  <span class={`dot ${dot()}`}>●</span>
  <span class="sep">·</span>
  <span class="idx">{props.index ?? 1}</span>
  ...
  <Show when={bellBadge()}>...</Show>
  <span class="spacer" />
  <button class="menu" title="menu" type="button">⋯</button>
</div>
```

From apps/voss-app/src/pane/pty-ipc.ts (F3-02 additions):
```typescript
export type BudgetState = {
  tokens_used: number; token_limit: number | null;
  cost_usd: number; iteration: number; model: string;
};
// PtyTransportOpts now includes:
onBudgetUpdate?: (data: BudgetState) => void;
```

From apps/voss-app/src/grid/BudgetBar.tsx (F3-02):
```typescript
export default function BudgetBar(props: { budget: BudgetState; onClickDetail: (anchor: HTMLElement) => void; })
```

From apps/voss-app/src/grid/BudgetPopover.tsx (F3-02):
```typescript
export default function BudgetPopover(props: { budget: BudgetState; anchor: HTMLElement; onClose: () => void; })
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: PaneComponent budget signal + transport wiring + header integration + CSS transition</name>
  <files>apps/voss-app/src/pane/PaneComponent.tsx, apps/voss-app/src/pane/pane.css</files>
  <read_first>
    - apps/voss-app/src/pane/PaneComponent.tsx (full file — 509 lines)
    - apps/voss-app/src/pane/pane.css (full file — for CSS rule placement)
    - apps/voss-app/src/pane/pty-ipc.ts (verify BudgetState export exists from F3-02)
    - apps/voss-app/src/grid/BudgetBar.tsx (verify export default exists from F3-02)
    - apps/voss-app/src/grid/BudgetPopover.tsx (verify export default exists from F3-02)
    - .planning/phases/F3-budget-token-visualization/F3-PATTERNS.md (lines 281-338 — PaneComponent pattern)
    - .planning/phases/F3-budget-token-visualization/F3-RESEARCH.md (lines 276-305 — Pattern 3: PaneComponent integration, Pitfall 5: Solid.js Show accessor)
  </read_first>
  <action>
    **PaneComponent.tsx changes — 5 surgical insertions:**

    1. **Imports (top of file):** Add `import BudgetBar from '../grid/BudgetBar';` and `import BudgetPopover from '../grid/BudgetPopover';` and `import type { BudgetState } from './pty-ipc';` (BudgetState type import alongside the existing `PtyTransport, type AgentConfig` import on line 10).

    2. **Signals (after line 94, after `headerFlash` signal):** Add two new signals:
       `const [budget, setBudget] = createSignal<BudgetState | null>(null);` — per-pane local budget state (D-12). Starts null — no persistence (D-11).
       `const [budgetPopoverAnchor, setBudgetPopoverAnchor] = createSignal<HTMLElement | null>(null);` — controls popover open/close state (null = closed).
       Add two helpers:
       `const openBudgetPopover = (anchor: HTMLElement) => setBudgetPopoverAnchor(prev => prev === anchor ? null : anchor);` — toggle behavior (D-09: click when open closes it).
       `const closeBudgetPopover = () => setBudgetPopoverAnchor(null);`

    3. **Transport opts (around line 318, after `onTitle` callback):** Add `onBudgetUpdate: (data) => setBudget(data),` inside the PtyTransport constructor opts object. Place it BEFORE the spread `...(props.agentConfig ? ...)` block.

    4. **Header JSX (between `<span class="spacer" />` and `<button class="menu">`, around lines 477-478):** Insert:
       ```
       <Show when={props.agentConfig != null}>
         <Show when={budget()}>
           {(b) => <BudgetBar budget={b()} onClickDetail={(anchor) => openBudgetPopover(anchor)} />}
         </Show>
       </Show>
       ```
       The outer Show gates on agent pane (shell panes never show budget — D-05). The inner Show uses Solid's accessor children pattern: `{(b) => ...}` receives the truthy BudgetState value, avoiding the null-assertion pitfall (RESEARCH Pitfall 5). This pattern is consistent with how PaneComponent already uses `<Show when={proc()}>`.

    5. **Popover mount (after the `<Show when={exitCode() !== null}>` block, around line 506):** Add:
       ```
       <Show when={budgetPopoverAnchor() != null && budget() != null}>
         <BudgetPopover
           budget={budget()!}
           anchor={budgetPopoverAnchor()!}
           onClose={closeBudgetPopover}
         />
       </Show>
       ```
       Non-null assertions are safe here because the `when` condition checks both are non-null.

    **pane.css change (D-13):**
    Add at the end of the file:
    ```css
    .budget-bar-fill {
      transition: width 150ms ease-out;
    }
    ```
    No `prefers-reduced-motion` override needed — the global `html.reduced-motion *` rule from A8 applies `transition: none !important` universally.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx tsc --noEmit 2>&1 | tail -5 && npm run test -- --reporter=dot 2>&1 | tail -15 && grep -c "BudgetBar" src/pane/PaneComponent.tsx && grep -c "onBudgetUpdate" src/pane/PaneComponent.tsx && grep "budget-bar-fill" src/pane/pane.css</automated>
  </verify>
  <acceptance_criteria>
    - `npx tsc --noEmit` exits 0 — no type errors
    - Full vitest suite passes with no regressions
    - `grep -c "BudgetBar" apps/voss-app/src/pane/PaneComponent.tsx` returns at least 2 (import + JSX)
    - `grep -c "BudgetPopover" apps/voss-app/src/pane/PaneComponent.tsx` returns at least 2 (import + JSX)
    - `grep -c "onBudgetUpdate" apps/voss-app/src/pane/PaneComponent.tsx` returns at least 1
    - `grep -c "budget" apps/voss-app/src/pane/PaneComponent.tsx` returns at least 5 (signal + setter + accessor + Show + popover)
    - `grep "budget-bar-fill" apps/voss-app/src/pane/pane.css` returns 1 line with `transition: width 150ms ease-out`
    - `grep "props.agentConfig" apps/voss-app/src/pane/PaneComponent.tsx | grep -c "Show"` returns at least 1 (agent gate on budget)
  </acceptance_criteria>
  <done>PaneComponent has a local budget signal, PtyTransport routes BudgetUpdate events to it, BudgetBar renders in the inline header for agent panes only, BudgetPopover opens/closes on click, and .budget-bar-fill has 150ms CSS transition. Shell panes show nothing. Budget state starts null on mount.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    Full F3 budget visualization pipeline: Python harness emits OSC 1337 voss-budget= sequences at each agent iteration → Rust PTY reader parses and strips them → BudgetUpdate event flows through Channel → PaneComponent budget signal → BudgetBar renders cost + progress bar in 22px header → BudgetPopover shows detail on click.
  </what-built>
  <how-to-verify>
    1. Build the app: `cd apps/voss-app && pnpm tauri dev`
    2. Open an **agent pane** (Agents button or command palette — the pane must have `agentConfig` prop)
    3. Let the agent run an LLM iteration
    4. **Verify inline HUD:** After the first LLM response, the pane header should show a cost figure (e.g. `$0.0847`) right-aligned before the `⋯` menu. If a token budget is set, a 48px progress bar should appear next to the cost.
    5. **Verify progress bar colors:** At < 70% budget consumed, bar fill is green (`#6fd28f`). At 70-90%, amber (`#e8b86c`). At 90%+, red (`#e87b7b`).
    6. **Verify bar transition:** Watch the bar width update on subsequent iterations — it should animate smoothly over ~150ms.
    7. **Verify popover:** Click the cost/bar segment. A popover card should appear below with 5 rows: tokens (used/limit), limit, model, turns, cost. Click outside or press Esc to dismiss.
    8. **Verify shell pane:** Open a regular shell pane — no budget HUD should appear.
    9. **Verify no-limit display:** If the agent has no token_limit, only cost text should show (no bar).
    10. Run all test suites: `cargo test -p voss-app-core` + `cd apps/voss-app && npm run test` + `.venv/bin/python -m pytest voss/harness/test_budget_osc.py -x` — all green.
  </how-to-verify>
  <resume-signal>Type "approved" if the budget HUD displays correctly. Describe any visual issues or functional problems if not.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| PtyTransport → PaneComponent signal | Typed callback updates Solid signal; data rendered via JSX text nodes |
| BudgetBar click → Popover mount | User interaction opens popover; dismiss on Esc/outside-click |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-F3-07 | Spoofing | PaneComponent budget signal | accept | Budget data from PTY stream; spoofing requires PTY control. Cosmetic-only impact (token counts). |
| T-F3-08 | Info Disclosure | BudgetPopover model name | accept | Model name is not sensitive; displayed to the pane owner only (local app). |
| T-F3-SC | Tampering | npm/pip/cargo installs | accept | F3 adds zero new dependencies. |
</threat_model>

<verification>
- `cd apps/voss-app && npx tsc --noEmit` — zero type errors
- `cd apps/voss-app && npm run test` — full suite green, no regressions
- `cargo test -p voss-app-core` — all PTY tests pass
- `.venv/bin/python -m pytest voss/harness/test_budget_osc.py -x` — 4 Python tests pass
- Human verification: agent pane shows cost + bar, shell pane shows nothing
</verification>

<success_criteria>
Budget data flows from Python harness through Rust reader to the frontend HUD. Agent panes display cost text and conditional progress bar in the 22px header. Clicking the budget segment opens a detail popover. Shell panes show no budget HUD. Bar fill transitions smoothly at 150ms. All automated tests pass across Rust, Python, and TypeScript.
</success_criteria>

<output>
Create `.planning/phases/F3-budget-token-visualization/F3-03-SUMMARY.md` when done
</output>
