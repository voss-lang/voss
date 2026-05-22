---
phase: F3-budget-token-visualization
plan: 02
status: done
---

# F3-02 Summary: Frontend Components + Transport

## What was built

### pty-ipc.ts (transport layer)
- `budget_update` variant added to `PtyEvent` union with all 5 fields
- `BudgetState` exported type alias
- `onBudgetUpdate` callback in `PtyTransportOpts`
- `budget_update` case in `handle()` switch — explicit field access (no spread)

### Popover.tsx (reusable primitive)
- Fixed-positioned anchor popover using `getBoundingClientRect()`
- Dismiss on Escape key + outside click (capture phase) — matches DotMenu pattern
- `onMount`/`onCleanup` lifecycle for listener management

### BudgetBar.tsx (inline header segment)
- Cost text with 3-tier formatting: 4dp (<$0.01), 2dp (<$100), 0dp (>=$100)
- Conditional progress bar via `<Show when={hasLimit()}>` (D-07)
- 3-tier fill colors: green <70%, amber 70-90%, red >=90% (D-08)
- Width clamped to 100% for over-budget
- Click passes button anchor to `onClickDetail` (D-09)
- `aria-label` with budget state text

### BudgetPopover.tsx (detail card)
- Wraps Popover primitive with `role="dialog"` + `aria-label`
- Header row + expanded progress bar (when limit set)
- 5 field rows: tokens, limit, model (24ch ellipsis), turns, cost

### CSS
- `.budget-bar-fill { transition: width 150ms ease-out }` in pane.css (D-13)
- `html.reduced-motion` override already applies globally

## Verification

| Check | Result |
|-------|--------|
| `npx tsc --noEmit` | clean (0 errors) |
| Popover tests | 4 passed |
| BudgetBar tests | 9 passed |
| Full suite | 525 passed (49 files, 0 failures) |

## Files modified/created
- `apps/voss-app/src/pane/pty-ipc.ts` (modified)
- `apps/voss-app/src/grid/Popover.tsx` (new)
- `apps/voss-app/src/grid/BudgetBar.tsx` (new)
- `apps/voss-app/src/grid/BudgetPopover.tsx` (new)
- `apps/voss-app/src/pane/pane.css` (modified — transition rule)
- `apps/voss-app/src/grid/__tests__/Popover.test.tsx` (new)
- `apps/voss-app/src/grid/__tests__/BudgetBar.test.tsx` (new)
