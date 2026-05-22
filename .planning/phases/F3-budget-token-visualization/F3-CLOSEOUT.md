---
phase: F3-budget-token-visualization
status: complete
completed: 2026-05-22
---

# F3 Closeout

F3 is complete as of 2026-05-22.

## Scope Closed

- F3-01: Python budget OSC emission, Rust PTY OSC parsing, `BudgetData`, and `BudgetUpdate`.
- F3-02: frontend `budget_update` transport, `Popover`, `BudgetBar`, and `BudgetPopover`.
- F3-03: `PaneComponent` local budget state, agent-pane-only HUD, popover wiring, and 150ms bar transition.

## Verification

| Gate | Result |
|---|---|
| `cargo test -p voss-app-core` | 132 passed |
| `python3 -m pytest voss/harness/test_budget_osc.py -q` | 4 passed |
| `cd apps/voss-app && npm run test -- --reporter=dot` | 525 passed (49 files) |
| `cd apps/voss-app && npx tsc --noEmit` | clean |
| `cd apps/voss-app && npm run build` | passed; existing large-chunk warning |
| `cargo build -p voss-app-core` | passed |

## Runtime Checkpoint

The original F3-03 plan requested a human live LLM-pane visual checkpoint. This closeout was performed by operator direction on 2026-05-22 using automated gates and source evidence; no independent live screenshot was captured in this session.

## Notes

The worktree also contains unrelated F4 PTY context-telemetry edits in `crates/voss-app-core/src/pty/commands.rs`, `reader.rs`, and `tests.rs`. They were not part of the F3 closeout docs commit.
