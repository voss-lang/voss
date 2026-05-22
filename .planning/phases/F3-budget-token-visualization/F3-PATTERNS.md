# Phase F3: Budget & Token Visualization — Pattern Map

**Mapped:** 2026-05-21
**Files analyzed:** 11 (6 new, 5 modified)
**Analogs found:** 10 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `crates/voss-app-core/src/pty/reader.rs` | streaming-transformer | event-driven | self (existing) | modify-in-place |
| `crates/voss-app-core/src/pty/commands.rs` | model/enum | event-driven | self (existing) | modify-in-place |
| `crates/voss-app-core/src/pty/tests.rs` | test | unit | self (existing) | modify-in-place |
| `apps/voss-app/src/pane/pty-ipc.ts` | transport/service | event-driven | self (existing) | modify-in-place |
| `apps/voss-app/src/pane/PaneComponent.tsx` | component | event-driven | self (existing) | modify-in-place |
| `apps/voss-app/src/grid/BudgetBar.tsx` | component | request-response | `apps/voss-app/src/grid/PaneHeader.tsx` | role-match |
| `apps/voss-app/src/grid/BudgetPopover.tsx` | component | request-response | `apps/voss-app/src/grid/DotMenu.tsx` | role-match |
| `apps/voss-app/src/grid/Popover.tsx` | primitive/utility | request-response | `apps/voss-app/src/grid/DotMenu.tsx` | partial (dismiss logic) |
| `apps/voss-app/src/grid/__tests__/BudgetBar.test.tsx` | test | unit | `apps/voss-app/src/grid/__tests__/RestoreBanner.test.tsx` + `PaneChrome.test.tsx` | role-match |
| `apps/voss-app/src/grid/__tests__/Popover.test.tsx` | test | unit | `apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx` (DotMenu dismiss tests) | role-match |
| `voss/harness/test_budget_osc.py` | test | unit | `tests/harness/conftest.py` + `tests/packaging/test_npm_shim_logic.py` | partial |

---

## Pattern Assignments

---

### `crates/voss-app-core/src/pty/reader.rs` (streaming-transformer, event-driven)

**Analog:** self — modify the existing `Ok(n)` arm in `start_reader`

**Existing read loop** (`reader.rs` lines 26-44):
```rust
tokio::task::spawn_blocking(move || {
    let mut buf = [0u8; 8192];
    loop {
        if let Ok(true) = pause_rx.try_recv() {
            while pause_rx.blocking_recv() != Some(false) {}
        }
        match reader.read(&mut buf) {
            Ok(0) => break, // EOF — child exited
            Ok(n) => {
                if on_data
                    .send(PtyEvent::Data {
                        bytes: buf[..n].to_vec(),
                    })
                    .is_err()
                {
                    break; // channel closed (pane gone)
                }
            }
            Err(_) => break,
        }
    }
    // ...exit cleanup...
```

**What F3 changes:** Replace the `Ok(n)` arm body with a call to `extract_voss_osc`, emitting `PtyEvent::BudgetUpdate` when found and `PtyEvent::Data` for remaining display bytes. The `is_err()` break pattern and the `buf` size are unchanged.

**New pure function to add above `start_reader`:**
```rust
/// Scans `data` for one complete `ESC]1337;voss-budget={json}BEL` sequence.
/// Returns Some((json_bytes, display_bytes)) if the full sequence (prefix + BEL)
/// is present; None passes through the buffer unchanged as display bytes.
/// Buffer fragmentation: returns None silently — next emission has cumulative state (D-03).
fn extract_voss_osc(data: &[u8]) -> Option<(Vec<u8>, Vec<u8>)> {
    const PREFIX: &[u8] = b"\x1b]1337;voss-budget=";
    let start = data.windows(PREFIX.len()).position(|w| w == PREFIX)?;
    let json_start = start + PREFIX.len();
    let rel_end = data[json_start..].iter().position(|&b| b == 0x07)?;
    let end = json_start + rel_end;
    let json_bytes = data[json_start..end].to_vec();
    let mut display = data[..start].to_vec();
    display.extend_from_slice(&data[end + 1..]);
    Some((json_bytes, display))
}
```

**Modified `Ok(n)` arm pattern** (replaces lines 33-41):
```rust
Ok(n) => {
    let slice = &buf[..n];
    match extract_voss_osc(slice) {
        Some((json_bytes, display_bytes)) => {
            if let Ok(data) = serde_json::from_slice::<BudgetData>(&json_bytes) {
                let _ = on_data.send(PtyEvent::BudgetUpdate(data));
            }
            // Forward remaining display bytes (may be empty after stripping OSC).
            if !display_bytes.is_empty()
                && on_data.send(PtyEvent::Data { bytes: display_bytes }).is_err()
            {
                break;
            }
        }
        None => {
            if on_data.send(PtyEvent::Data { bytes: slice.to_vec() }).is_err() {
                break; // channel closed
            }
        }
    }
}
```

**Import to add at top of file:** `use crate::pty::commands::BudgetData;` (already imports `PtyEvent`).

---

### `crates/voss-app-core/src/pty/commands.rs` (model/enum, event-driven)

**Analog:** self — add variant + struct to the existing `PtyEvent` enum

**Existing enum** (`commands.rs` lines 14-21):
```rust
#[derive(serde::Serialize, Clone)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum PtyEvent {
    Data { bytes: Vec<u8> },
    Exit { code: i32 },
    FgProcess { name: String },
    TitleChange { title: String },
}
```

**Serde convention:** `#[serde(tag = "type", rename_all = "snake_case")]` — the new variant serializes as `{ "type": "budget_update", ... }`. Match this exactly.

**F3 additions — insert before the closing `}`:**
```rust
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct BudgetData {
    pub tokens_used: u64,
    pub token_limit: Option<u64>,
    pub cost_usd: f64,
    pub iteration: u32,
    pub model: String,
}

// In PtyEvent enum, add:
BudgetUpdate(BudgetData),
```

Note: `BudgetData` needs both `Serialize` (for Tauri Channel to TypeScript) and `Deserialize` (for `serde_json::from_slice` when parsing the OSC JSON in `reader.rs`). Existing variants only derive `Serialize` — this is intentional; `BudgetData` is unique in needing both.

---

### `crates/voss-app-core/src/pty/tests.rs` (test, unit)

**Analog:** self — the existing test file uses `spawn_session` (Tauri-free) for integration tests. F3 adds pure-function unit tests that need no PTY at all.

**Existing test structure** (`tests.rs` lines 1-10 + test pattern):
```rust
//! PTY core tests (A2-02). Drive `spawn_session` directly (Tauri-free) so no
//! `AppHandle`/`Channel` is required.
use std::io::Read;
use std::sync::mpsc;
use std::time::Duration;
use crate::pty::writer::validate_write;
use crate::pty::{spawn_session, PtyRegistry};

#[test]
fn test_pty_write_validation() {
    assert!(validate_write(b"").is_err(), "empty must reject");
    // ...
}
```

**Pattern for F3 pure-function tests:** No `spawn_session` needed — `extract_voss_osc` is a module-level `fn`. Import it directly (make it `pub(crate)` or move test into `reader.rs` as an inline `#[cfg(test)]` block).

**F3 test structure to add:**
```rust
// Add to tests.rs (or as inline #[cfg(test)] mod in reader.rs):
use crate::pty::reader::extract_voss_osc;
use crate::pty::commands::BudgetData;

#[test]
fn test_extract_voss_osc_parses_well_formed() {
    let payload = br#"{"tokens_used":100,"token_limit":1000,"cost_usd":0.005,"iteration":1,"model":"claude-3"}"#;
    let mut data = b"\x1b]1337;voss-budget=".to_vec();
    data.extend_from_slice(payload);
    data.push(0x07); // BEL
    let result = extract_voss_osc(&data);
    let (json, display) = result.expect("should find the sequence");
    assert_eq!(json, payload.to_vec());
    assert!(display.is_empty());
}

#[test]
fn test_extract_voss_osc_strips_surrounding_display_bytes() {
    let before = b"hello ";
    let after = b" world";
    let osc = b"\x1b]1337;voss-budget={\"tokens_used\":1,\"token_limit\":null,\"cost_usd\":0.0,\"iteration\":1,\"model\":\"m\"}\x07";
    let mut data = before.to_vec();
    data.extend_from_slice(osc);
    data.extend_from_slice(after);
    let (_, display) = extract_voss_osc(&data).expect("found");
    assert_eq!(display, b"hello  world");
}

#[test]
fn test_extract_voss_osc_returns_none_for_partial_sequence() {
    // No BEL terminator — buffer fragmentation case; pass through as display.
    let data = b"\x1b]1337;voss-budget={\"tokens_used\":1";
    assert!(extract_voss_osc(data).is_none());
}

#[test]
fn test_extract_voss_osc_returns_none_for_unrelated_bytes() {
    let data = b"normal terminal output \x1b[32mgreen text\x1b[0m";
    assert!(extract_voss_osc(data).is_none());
}
```

---

### `apps/voss-app/src/pane/pty-ipc.ts` (transport/service, event-driven)

**Analog:** self — add `budget_update` to the `PtyEvent` union and `onBudgetUpdate` callback to `PtyTransportOpts`

**Existing `PtyEvent` union** (`pty-ipc.ts` lines 11-15):
```typescript
export type PtyEvent =
  | { type: 'data'; bytes: number[] }
  | { type: 'exit'; code: number }
  | { type: 'fg_process'; name: string }
  | { type: 'title_change'; title: string };
```

**Existing `PtyTransportOpts` interface** (`pty-ipc.ts` lines 27-35):
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

**Existing switch-case pattern in `handle()`** (`pty-ipc.ts` lines 62-95):
```typescript
private handle(ev: PtyEvent): void {
    switch (ev.type) {
      case 'data': { /* ...coalescing... */ break; }
      case 'exit':   this.opts.onExit?.(ev.code); /* ...agent registry... */ break;
      case 'fg_process': this.opts.onFgProcess?.(ev.name); break;
      case 'title_change': this.opts.onTitle?.(ev.title); break;
    }
}
```

**F3 additions — copy the `onTitle` callback pattern:**
```typescript
// Add to PtyEvent union:
| { type: 'budget_update'; tokens_used: number; token_limit: number | null; cost_usd: number; iteration: number; model: string }

// Add type alias (placed before PtyTransportOpts):
export type BudgetState = {
  tokens_used: number;
  token_limit: number | null;
  cost_usd: number;
  iteration: number;
  model: string;
};

// Add to PtyTransportOpts:
onBudgetUpdate?: (data: BudgetState) => void;

// Add to handle() switch — after 'title_change' case:
case 'budget_update':
  this.opts.onBudgetUpdate?.({ ...ev });
  break;
```

The spread `{ ...ev }` strips the `type` discriminant from the payload passed to the callback, matching the `BudgetState` shape.

---

### `apps/voss-app/src/pane/PaneComponent.tsx` (component, event-driven)

**Analog:** self — three surgical insertions: signal declaration, transport opts, and header JSX

**Signal declaration block** (`PaneComponent.tsx` lines 84-94 — copy the `bellBadge`/`headerFlash` pattern):
```typescript
const [focused, setFocused] = createSignal(true);
const [dot, setDot] = createSignal<DotState>('loading');
// ...
const [bellBadge, setBellBadge] = createSignal(false);
const [headerFlash, setHeaderFlash] = createSignal(false);
// ADD after line 94:
const [budget, setBudget] = createSignal<BudgetState | null>(null);
```

**Transport opts** (`PaneComponent.tsx` lines 310-327 — insert `onBudgetUpdate` alongside `onTitle`):
```typescript
transport = new PtyTransport({
  write: (data, cb) => t.write(data, cb),
  onExit: (code) => { setDot('exited'); setExitCode(code); },
  onFgProcess: (name) => setProc(name),
  onTitle: (title) => { lastOscTitleAt = Date.now(); setProc(title); },
  onBudgetUpdate: (data) => setBudget(data),   // ADD THIS
  ...(props.agentConfig ? { agentPaneId: props.id, workspacePath: props.workspacePath } : {}),
});
```

**Header JSX insertion** (`PaneComponent.tsx` lines 477-480 — between `<span class="spacer" />` and `<button class="menu">`):
```tsx
<span class="spacer" />
{/* F3: budget HUD — agent panes only, hidden until first OSC emission */}
<Show when={props.agentConfig != null}>
  <Show when={budget()}>
    {(b) => <BudgetBar budget={b()} onClickDetail={(anchor) => openBudgetPopover(anchor)} />}
  </Show>
</Show>
<button class="menu" title="menu" type="button">⋯</button>
```

The `Show when={budget()}` accessor pattern passes the truthy `BudgetState` value to children as `b()`, avoiding the Solid.js null-assertion pitfall documented in RESEARCH.md Pitfall 5.

**`openBudgetPopover` helper** (add alongside existing ref declarations near line 80):
```typescript
const [budgetPopoverAnchor, setBudgetPopoverAnchor] = createSignal<HTMLElement | null>(null);
const openBudgetPopover = (anchor: HTMLElement) => setBudgetPopoverAnchor(anchor);
const closeBudgetPopover = () => setBudgetPopoverAnchor(null);
```

**Popover mount** (after the `<Show when={exitCode() ...}>` block near line 504):
```tsx
<Show when={budgetPopoverAnchor() != null && budget() != null}>
  <BudgetPopover
    budget={budget()!}
    anchor={budgetPopoverAnchor()!}
    onClose={closeBudgetPopover}
  />
</Show>
```

---

### `apps/voss-app/src/grid/BudgetBar.tsx` (component, request-response)

**Analog:** `apps/voss-app/src/grid/PaneHeader.tsx`

**Imports pattern** (`PaneHeader.tsx` lines 1-1):
```typescript
import { Show } from 'solid-js';
```

**Component structure pattern** (`PaneHeader.tsx` lines 37-127 — functional component with inline `style={{}}` objects, semantic CSS vars, `Show` for conditional segments):
```tsx
export default function PaneHeader(props: PaneHeaderProps) {
  const exited = () => props.dotState === 'exited';
  const dotClass = () => (exited() ? 'text-accent-red' : 'text-accent-green');
  return (
    <div
      class={`font-mono ${props.focused ? 'bg-bg-2' : 'bg-bg-1'}`}
      style={{ display: 'flex', 'align-items': 'center', height: '22px', ... }}
    >
      <Show when={props.process}>
        <Pipe />
        <span class={primary()} style={{ 'white-space': 'nowrap' }}>{props.process}</span>
      </Show>
      <span style={{ flex: 1 }} />
      <button type="button" class={secondary()} style={{ background: 'transparent', border: 'none', ... }} onClick={...}>⋯</button>
    </div>
  );
}
```

**CSS token pattern** — use `var(--fg-2)`, `var(--accent-green)`, `var(--accent-amber)`, `var(--accent-red)`, `var(--bg-2)`. No raw hex values in component code (variant-b.css rule).

**F3 BudgetBar structure:**
```tsx
// src/grid/BudgetBar.tsx
import { Show } from 'solid-js';
import type { BudgetState } from '../pane/pty-ipc';

interface BudgetBarProps {
  budget: BudgetState;
  onClickDetail: (anchor: HTMLElement) => void;
}

function barFillPct(tokens_used: number, token_limit: number | null): number {
  if (token_limit == null) return 0;
  return Math.min((tokens_used / token_limit) * 100, 100);
}

function barFillColor(pct: number): string {
  if (pct < 70) return 'var(--accent-green)';
  if (pct < 90) return 'var(--accent-amber)';
  return 'var(--accent-red)';
}

function formatCost(cost_usd: number): string {
  if (cost_usd < 0.01) return `$${cost_usd.toFixed(4)}`;
  if (cost_usd < 100) return `$${cost_usd.toFixed(2)}`;
  return `$${Math.round(cost_usd)}`;
}

export default function BudgetBar(props: BudgetBarProps) {
  let buttonRef!: HTMLButtonElement;
  const pct = () => barFillPct(props.budget.tokens_used, props.budget.token_limit);
  const hasLimit = () => props.budget.token_limit != null;
  return (
    <button
      ref={buttonRef}
      type="button"
      style={{ display: 'flex', 'align-items': 'center', gap: '4px',
               background: 'transparent', border: 'none', padding: '0 4px',
               'flex-shrink': 0, cursor: 'default' }}
      onClick={() => props.onClickDetail(buttonRef)}
    >
      <span style={{ color: 'var(--fg-2)', 'font-size': '11px' }}>
        {formatCost(props.budget.cost_usd)}
      </span>
      <Show when={hasLimit()}>
        <div style={{ width: '48px', height: '4px', background: 'var(--bg-2)',
                      position: 'relative', 'flex-shrink': 0 }}>
          <div
            class="budget-bar-fill"
            style={{ height: '4px', width: `${pct()}%`,
                     background: barFillColor(pct()) }}
          />
        </div>
      </Show>
    </button>
  );
}
```

**CSS transition for `.budget-bar-fill`** (add to `pane.css` or a new `budget.css`):
```css
.budget-bar-fill {
  transition: width 150ms ease-out;
}
html.reduced-motion .budget-bar-fill {
  transition: none;
}
```

---

### `apps/voss-app/src/grid/BudgetPopover.tsx` (component, request-response)

**Analog:** `apps/voss-app/src/grid/DotMenu.tsx`

**DotMenu structure pattern** (`DotMenu.tsx` lines 12-122 — anchored absolutely, `onDocClick`/`onDocKey` dismiss, `onMount`/`onCleanup` lifecycle):
```tsx
export default function DotMenu(props: { ...; onDismiss: () => void }) {
  let root!: HTMLDivElement;
  const onDocKey = (e: KeyboardEvent) => { if (e.key === 'Escape') props.onDismiss(); };
  const onDocClick = (e: MouseEvent) => {
    if (root && !root.contains(e.target as Node)) props.onDismiss();
  };
  onMount(() => {
    document.addEventListener('keydown', onDocKey);
    document.addEventListener('click', onDocClick, true);
  });
  onCleanup(() => {
    document.removeEventListener('keydown', onDocKey);
    document.removeEventListener('click', onDocClick, true);
  });
  return (
    <div ref={root} class="font-mono bg-bg-3"
      style={{ position: 'absolute', top: '22px', right: 0,
               border: '1px solid var(--border)', 'z-index': 10 }}>
      {/* content */}
    </div>
  );
}
```

**BudgetPopover adapts DotMenu pattern** with `position: 'fixed'` (anchored to button `getBoundingClientRect()`) instead of `absolute`, and informational rows instead of action items.

**BudgetPopover structure:**
```tsx
// src/grid/BudgetPopover.tsx
import { onMount, onCleanup } from 'solid-js';
import type { BudgetState } from '../pane/pty-ipc';
import Popover from './Popover';

interface BudgetPopoverProps {
  budget: BudgetState;
  anchor: HTMLElement;
  onClose: () => void;
}

export default function BudgetPopover(props: BudgetPopoverProps) {
  const b = () => props.budget;
  const pct = () => b().token_limit != null
    ? Math.min((b().tokens_used / b().token_limit!) * 100, 100)
    : 0;

  return (
    <Popover anchor={props.anchor} onClose={props.onClose}>
      {/* 5-row detail card using var(--fg-*) and var(--accent-*) tokens */}
    </Popover>
  );
}
```

---

### `apps/voss-app/src/grid/Popover.tsx` (primitive/utility, request-response)

**Analog:** `apps/voss-app/src/grid/DotMenu.tsx` — copy the `onDocClick`/`onDocKey`/`onMount`/`onCleanup` dismiss pattern

**Key pattern from DotMenu** (`DotMenu.tsx` lines 50-63):
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

**Popover primitive** — adapts DotMenu's dismiss logic, uses `fixed` positioning via `getBoundingClientRect()`:
```tsx
// src/grid/Popover.tsx
import { onMount, onCleanup } from 'solid-js';
import type { JSX } from 'solid-js';

interface PopoverProps {
  anchor: HTMLElement;
  onClose: () => void;
  children: JSX.Element;
}

export default function Popover(props: PopoverProps) {
  let rootRef!: HTMLDivElement;
  const rect = props.anchor.getBoundingClientRect();

  const onDocClick = (e: MouseEvent) => {
    if (!rootRef.contains(e.target as Node)) props.onClose();
  };
  const onDocKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') props.onClose();
  };

  onMount(() => {
    document.addEventListener('click', onDocClick, true);
    document.addEventListener('keydown', onDocKey);
  });
  onCleanup(() => {
    document.removeEventListener('click', onDocClick, true);
    document.removeEventListener('keydown', onDocKey);
  });

  return (
    <div
      ref={rootRef}
      style={{
        position: 'fixed',
        top: `${rect.bottom + 2}px`,
        left: `${rect.right - 220}px`,
        'z-index': 20,
        background: 'var(--bg-3)',
        border: '1px solid var(--border)',
        'font-size': '11px',
        'min-width': '220px',
      }}
    >
      {props.children}
    </div>
  );
}
```

**z-index note:** DotMenu uses `z-index: 10`; Popover uses `z-index: 20` to float above pane chrome.

---

### `apps/voss-app/src/grid/__tests__/BudgetBar.test.tsx` (test, unit)

**Analog:** `apps/voss-app/src/grid/__tests__/RestoreBanner.test.tsx` (component render + DOM query pattern) and `PaneChrome.test.tsx` (fireEvent interaction pattern)

**Mount helper pattern** (from `RestoreBanner.test.tsx` lines 15-26):
```tsx
import { describe, it, expect, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import RestoreBanner from '../RestoreBanner';

let dispose: (() => void) | undefined;
function mount(ui: () => unknown) {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}
afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
});
```

**fireEvent interaction pattern** (from `PaneChrome.test.tsx` lines 4-5, 69):
```tsx
import { fireEvent } from '@testing-library/dom';
// ...
fireEvent.click(el.querySelector('[aria-label="Pane menu"]')!);
```

**BudgetBar test structure:**
```tsx
// src/grid/__tests__/BudgetBar.test.tsx
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';
import BudgetBar from '../BudgetBar';
import type { BudgetState } from '../../pane/pty-ipc';

let dispose: (() => void) | undefined;
function mount(ui: () => unknown) {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}
afterEach(() => { dispose?.(); dispose = undefined; document.body.innerHTML = ''; });

const BASE: BudgetState = { tokens_used: 500, token_limit: 1000, cost_usd: 0.05, iteration: 3, model: 'claude-3' };

describe('BudgetBar', () => {
  it('renders cost text', () => {
    const el = mount(() => <BudgetBar budget={BASE} onClickDetail={() => {}} />);
    expect(el.textContent).toContain('$0.05');
  });

  it('renders bar track when token_limit is set', () => {
    const el = mount(() => <BudgetBar budget={BASE} onClickDetail={() => {}} />);
    expect(el.querySelector('.budget-bar-fill')).toBeTruthy();
  });

  it('does not render bar track when token_limit is null (D-07)', () => {
    const el = mount(() => <BudgetBar budget={{ ...BASE, token_limit: null }} onClickDetail={() => {}} />);
    expect(el.querySelector('.budget-bar-fill')).toBeNull();
  });

  it('bar fill color is accent-green below 70% (D-08)', () => {
    // 500/1000 = 50% → green
    const el = mount(() => <BudgetBar budget={BASE} onClickDetail={() => {}} />);
    const fill = el.querySelector('.budget-bar-fill') as HTMLElement;
    expect(fill.style.background).toContain('var(--accent-green)');
  });

  it('bar fill color is accent-amber at 80% (D-08)', () => {
    const el = mount(() => <BudgetBar budget={{ ...BASE, tokens_used: 800 }} onClickDetail={() => {}} />);
    const fill = el.querySelector('.budget-bar-fill') as HTMLElement;
    expect(fill.style.background).toContain('var(--accent-amber)');
  });

  it('bar fill color is accent-red at 95% (D-08)', () => {
    const el = mount(() => <BudgetBar budget={{ ...BASE, tokens_used: 950 }} onClickDetail={() => {}} />);
    const fill = el.querySelector('.budget-bar-fill') as HTMLElement;
    expect(fill.style.background).toContain('var(--accent-red)');
  });

  it('calls onClickDetail with the button element on click (D-09)', () => {
    const spy = vi.fn();
    const el = mount(() => <BudgetBar budget={BASE} onClickDetail={spy} />);
    fireEvent.click(el.querySelector('button')!);
    expect(spy).toHaveBeenCalledWith(expect.any(HTMLButtonElement));
  });

  it('cost format: <$0.01 → 4dp', () => {
    const el = mount(() => <BudgetBar budget={{ ...BASE, cost_usd: 0.0012 }} onClickDetail={() => {}} />);
    expect(el.textContent).toContain('$0.0012');
  });

  it('bar width clamped to 100% when over-limit', () => {
    const el = mount(() => <BudgetBar budget={{ ...BASE, tokens_used: 1500, token_limit: 1000 }} onClickDetail={() => {}} />);
    const fill = el.querySelector('.budget-bar-fill') as HTMLElement;
    expect(parseFloat(fill.style.width)).toBeLessThanOrEqual(100);
  });
});
```

---

### `apps/voss-app/src/grid/__tests__/Popover.test.tsx` (test, unit)

**Analog:** `apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx` — specifically the DotMenu dismiss tests using `fireEvent.keyDown` and `fireEvent.click`

**DotMenu Escape dismiss test pattern** (`PaneChrome.test.tsx` lines 162-164):
```tsx
fireEvent.keyDown(document, { key: 'Escape' });
expect(ops.closeFocused).not.toHaveBeenCalled();
expect(keep).toHaveBeenCalled();
```

**Outside-click dismiss pattern** (`DotMenu.tsx` lines 53-55 — what the test exercises):
```tsx
const onDocClick = (e: MouseEvent) => {
  if (root && !root.contains(e.target as Node)) props.onDismiss();
};
document.addEventListener('click', onDocClick, true); // capture phase
```

**Popover test structure:**
```tsx
// src/grid/__tests__/Popover.test.tsx
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';
import Popover from '../Popover';

let dispose: (() => void) | undefined;
function mount(ui: () => unknown) {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}
afterEach(() => { dispose?.(); dispose = undefined; document.body.innerHTML = ''; });

describe('Popover', () => {
  it('renders children', () => {
    const anchor = document.createElement('button');
    document.body.appendChild(anchor);
    const el = mount(() => (
      <Popover anchor={anchor} onClose={() => {}}>
        <span data-testid="content">hello</span>
      </Popover>
    ));
    expect(el.querySelector('[data-testid="content"]')).toBeTruthy();
  });

  it('calls onClose on Escape keydown (D-10)', () => {
    const close = vi.fn();
    const anchor = document.createElement('button');
    document.body.appendChild(anchor);
    mount(() => <Popover anchor={anchor} onClose={close}><div /></Popover>);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(close).toHaveBeenCalled();
  });

  it('calls onClose on outside click (D-10)', () => {
    const close = vi.fn();
    const anchor = document.createElement('button');
    document.body.appendChild(anchor);
    mount(() => <Popover anchor={anchor} onClose={close}><div /></Popover>);
    const outside = document.createElement('div');
    document.body.appendChild(outside);
    fireEvent.click(outside);
    expect(close).toHaveBeenCalled();
  });

  it('does NOT call onClose on click inside the popover', () => {
    const close = vi.fn();
    const anchor = document.createElement('button');
    document.body.appendChild(anchor);
    const el = mount(() => (
      <Popover anchor={anchor} onClose={close}>
        <button data-testid="inner">inside</button>
      </Popover>
    ));
    fireEvent.click(el.querySelector('[data-testid="inner"]')!);
    expect(close).not.toHaveBeenCalled();
  });
});
```

---

### `voss/harness/test_budget_osc.py` (test, unit)

**Analog:** No existing `test_*.py` in `voss/harness/`. Closest pattern is `tests/packaging/test_npm_shim_logic.py` for the `from __future__ import annotations` + `pytest` function test style, and `tests/harness/conftest.py` for `monkeypatch` usage.

**Python test conventions from the codebase:**
```python
# from tests/packaging/test_npm_shim_logic.py
from __future__ import annotations
import pytest

def test_something():
    assert condition, "message"
```

**`monkeypatch` for stdout capture pattern** (from `tests/harness/conftest.py` lines 28-31 — `monkeypatch.setenv` idiom; same object used for `monkeypatch.setattr`):
```python
@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
```

**F3 test file structure:**
```python
# voss/harness/test_budget_osc.py
"""F3: tests for _emit_budget_osc OSC 1337 stdout emission (D-02/D-04)."""
from __future__ import annotations

import io
import json

import pytest

from voss.harness.recorder import _emit_budget_osc


def test_emit_budget_osc_writes_to_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    """_emit_budget_osc writes OSC 1337 voss-budget= sequence to sys.stdout."""
    buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", buf)
    _emit_budget_osc(
        tokens_used=500,
        token_limit=1000,
        cost_usd=0.05,
        iteration=3,
        model="claude-3-5-sonnet",
    )
    out = buf.getvalue()
    assert out.startswith("\x1b]1337;voss-budget="), "must start with OSC 1337 prefix"
    assert out.endswith("\x07"), "must end with BEL terminator"


def test_emit_budget_osc_payload_is_valid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", buf)
    _emit_budget_osc(tokens_used=100, token_limit=None, cost_usd=0.001, iteration=1, model="m")
    out = buf.getvalue()
    prefix = "\x1b]1337;voss-budget="
    json_str = out[len(prefix):-1]  # strip prefix + BEL
    data = json.loads(json_str)
    assert data["tokens_used"] == 100
    assert data["token_limit"] is None
    assert data["cost_usd"] == pytest.approx(0.001)
    assert data["iteration"] == 1
    assert data["model"] == "m"


def test_emit_budget_osc_unlimited_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    """token_limit=None serializes as JSON null (D-07 unlimited budget case)."""
    buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", buf)
    _emit_budget_osc(tokens_used=0, token_limit=None, cost_usd=0.0, iteration=0, model="m")
    out = buf.getvalue()
    assert '"token_limit": null' in out or '"token_limit":null' in out


def test_emit_budget_osc_not_to_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    """OSC must NOT go to stderr (PTY only reads stdout) (D-04 anti-pattern)."""
    import sys
    stderr_buf = io.StringIO()
    stdout_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_buf)
    monkeypatch.setattr("sys.stderr", stderr_buf)
    _emit_budget_osc(tokens_used=1, token_limit=None, cost_usd=0.0, iteration=1, model="m")
    assert stderr_buf.getvalue() == "", "nothing should go to stderr"
    assert stdout_buf.getvalue() != "", "output must go to stdout"
```

---

## Shared Patterns

### `onMount`/`onCleanup` document event listeners

**Source:** `apps/voss-app/src/grid/DotMenu.tsx` lines 50-63
**Apply to:** `Popover.tsx`, `BudgetPopover.tsx`

```tsx
onMount(() => {
  document.addEventListener('keydown', onDocKey);
  document.addEventListener('click', onDocClick, true); // capture phase — required
});
onCleanup(() => {
  document.removeEventListener('keydown', onDocKey);
  document.removeEventListener('click', onDocClick, true);
});
```

Critical: use `true` (capture phase) for `click`, matching DotMenu. Without capture, clicks on child elements may not bubble to the document listener before the popover content handles them.

---

### CSS semantic tokens (Variant B)

**Source:** `apps/voss-app/src/styles/variant-b.css` lines 1-51
**Apply to:** `BudgetBar.tsx`, `BudgetPopover.tsx`, `Popover.tsx`

Relevant tokens for F3:
```css
--bg-2: #171a23;   /* bar track background */
--bg-3: #1f232e;   /* popover background */
--border: #262b38; /* popover border */
--fg-2: #6a7080;   /* cost text (dim) */
--accent-green: #6fd28f;  /* 0–70% fill */
--accent-amber: #e8b86c;  /* 70–90% fill */
--accent-red:   #e87b7b;  /* 90–100% fill */
```

Rule: never use raw hex in component code. Always `var(--token-name)`.

---

### Solid.js `Show` with accessor children (null-safety)

**Source:** `apps/voss-app/src/pane/PaneComponent.tsx` lines 467-470 (`<Show when={proc()}>`) and RESEARCH.md Pitfall 5
**Apply to:** Budget HUD mount in `PaneComponent.tsx`

When the `when` value needs to be passed to children as non-null, use the accessor form:
```tsx
<Show when={budget()}>
  {(b) => <BudgetBar budget={b()} onClickDetail={...} />}
</Show>
```
This guarantees `b()` is `BudgetState` (not `BudgetState | null | false`) inside the children function.

---

### Reduced-motion CSS kill switch

**Source:** `apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx` lines 335-351 (A8-04 test contract)
**Apply to:** `.budget-bar-fill` CSS transition

```css
html.reduced-motion *, html.reduced-motion *::before, html.reduced-motion *::after {
  transition: none !important;
  animation: none !important;
}
```

The `html.reduced-motion` class is applied by `applyAppearanceSettings()` in `settings.ts` when the user enables reduced motion. The budget bar's 150ms transition is automatically killed by this global rule — no F3-specific override needed.

---

### Tauri `Channel<PtyEvent>` serde convention

**Source:** `apps/voss-app/src/pane/pty-ipc.ts` lines 11-15 + `crates/voss-app-core/src/pty/commands.rs` lines 14-21
**Apply to:** `BudgetUpdate` variant in `commands.rs`, `budget_update` case in `pty-ipc.ts`

The Rust enum uses `#[serde(tag = "type", rename_all = "snake_case")]`. Every variant becomes `{ "type": "<snake_case_variant_name>", ...fields }`. TypeScript union discriminates on `type`. The pattern is: add a Rust variant → add the matching TypeScript union member → add the `case` in `handle()`.

---

### Python `monkeypatch` stdout capture for side-effect tests

**Source:** `tests/harness/conftest.py` lines 28-31 (monkeypatch pattern)
**Apply to:** `voss/harness/test_budget_osc.py`

```python
def test_something(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", buf)
    # call function under test
    assert buf.getvalue() == expected
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `voss/harness/test_budget_osc.py` | test | unit | No existing `test_*.py` in `voss/harness/`. The `tests/harness/` directory has conftest.py and integration tests, but no direct analog for a module-level Python unit test using stdout capture. Use the pytest `monkeypatch` pattern from `conftest.py` + the `from __future__ import annotations` + function-test style from `tests/packaging/test_npm_shim_logic.py`. |

---

## Metadata

**Analog search scope:** `crates/voss-app-core/src/pty/`, `apps/voss-app/src/pane/`, `apps/voss-app/src/grid/`, `apps/voss-app/src/grid/__tests__/`, `voss/harness/`, `tests/harness/`, `tests/packaging/`
**Files scanned:** 17
**Pattern extraction date:** 2026-05-21
