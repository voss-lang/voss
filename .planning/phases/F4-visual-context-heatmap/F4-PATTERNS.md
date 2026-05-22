# Phase F4: Visual Context Heatmap - Patterns

**Date:** 2026-05-22

## Files to Create/Modify

| File | Role | Closest Analog |
|------|------|----------------|
| `crates/voss-app-core/src/pty/commands.rs` | Add ContextData/FileContextEntry structs + PtyEvent::ContextUpdate | BudgetData + BudgetUpdate in same file |
| `crates/voss-app-core/src/pty/reader.rs` | Extend OSC parsing for `voss-context=` prefix | Existing `extract_voss_osc()` for `voss-budget=` |
| `crates/voss-app-core/src/pty/tests.rs` | Add context OSC parsing tests | Existing `test_extract_voss_osc_*` tests (lines 160-182) |
| `apps/voss-app/src/pane/pty-ipc.ts` | Add ContextData type + onContextUpdate callback | BudgetState type + onBudgetUpdate (lines 16-42) |
| `apps/voss-app/src/pane/PaneComponent.tsx` | Add context signal + onContextUpdate handler | Budget signal + onBudgetUpdate handler |
| `apps/voss-app/src/components/ContextPanel.tsx` | **NEW** — Side panel overlay component | BudgetPopover.tsx (data display pattern) |
| `apps/voss-app/src/components/ContextPanel.css` | **NEW** — Panel styles | `apps/voss-app/src/pane/pane.css` (token-only pattern) |
| `apps/voss-app/src/App.tsx` | Mount ContextPanel + ⌘I keybind + focused pane context routing | BudgetBar integration in PaneHeader |
| `apps/voss-app/src/components/StatusBar.tsx` | Add context panel toggle button | Existing status bar buttons |
| `voss/harness/recorder.py` | Add ContextTracker + `_emit_context_osc()` | `_emit_budget_osc()` (lines 22-46) |
| `voss/harness/agent.py` | Read pin file at iteration start + pass context tracker to recorder | Budget emission call site in agent loop |

## Key Patterns

### 1. OSC 1337 Parsing (Rust)
**Source:** `reader.rs:19-29` `extract_voss_osc()`
**Pattern:** Scan for prefix bytes → find BEL terminator → split into (json, display)
**F4 reuse:** Parameterize prefix. Call twice: once for budget, once for context.

### 2. PtyEvent Tagged Enum (Rust)
**Source:** `commands.rs:26-34`
**Pattern:** `#[serde(tag = "type", rename_all = "snake_case")]` — auto-discriminates on JS side
**F4 reuse:** Add `ContextUpdate(ContextData)` variant. JS receives `{ type: "context_update", ... }`.

### 3. Tauri Channel → Solid Signal (TypeScript)
**Source:** `pty-ipc.ts:105` budget_update case, `PaneComponent.tsx` setBudget
**Pattern:** PtyTransport switch/case → callback → createSignal setter
**F4 reuse:** Add `context_update` case → `onContextUpdate` → `setContext()`.

### 4. OSC Emission (Python)
**Source:** `recorder.py:22-46` `_emit_budget_osc()`
**Pattern:** `json.dumps(payload, separators=(',', ':'))` → `sys.stdout.write(f"\x1b]1337;voss-budget={payload}\x07")` → `flush()`
**F4 reuse:** Same pattern with `voss-context=` prefix and ContextTracker payload.

### 5. Settings Read (Rust → TypeScript)
**Source:** `apps/voss-app/src/appearance/` — `get_theme_overrides` reads `~/.config/voss-app/`
**Pattern:** Tauri command reads JSON file, returns HashMap/object. Frontend applies on mount.
**F4 reuse:** Read `contextPanel.open` boolean from same config path.

### 6. Component Overlay Pattern
**Source:** `apps/voss-app/src/grid/BudgetPopover.tsx` — absolute-positioned floating panel
**Pattern:** Solid.js `<Show when={...}>` + absolute positioning + z-index + click-outside dismiss
**F4 reuse:** ContextPanel is a persistent overlay (not dismissed on click-outside) but uses same positioning pattern.
