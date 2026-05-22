# Phase F3: Budget & Token Visualization — Research

**Researched:** 2026-05-21
**Domain:** OSC escape-sequence parsing in Rust PTY reader, Solid.js per-pane signals, Python harness emission, Tauri Channel<PtyEvent> extension
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: OSC escape sequences in PTY stream. Zero new IPC — reuses Channel<PtyEvent> with new BudgetUpdate variant.
- D-02: OSC 1337 with `voss-budget=` prefix. Format: `ESC]1337;voss-budget={json}BEL`.
- D-03: Cumulative totals payload — tokens_used, token_limit, cost_usd, iteration, model. No frontend accumulation.
- D-04: Emit after each LLM response at `end_iteration()` call site in `recorder.py`.
- D-05: Per-pane header bar (22px PaneHeader). Shell panes show nothing.
- D-06: Right-aligned cost + mini progress bar before `⋯` menu.
- D-07: Cost-only when `token_limit` is absent/unlimited.
- D-08: 3-tier thresholds — 0-70% = `--accent-green`, 70-90% = `--accent-amber`, 90-100% = `--accent-red`.
- D-09: Always-visible: cost + bar. Click budget segment → popover detail card.
- D-10: Reuses A10 `<Popover>` component (A10 D-04). One popover at a time. Dismiss on click-outside/Esc.
- D-11: No ADE-side persistence. Resets on restart; first OSC re-populates HUD.
- D-12: Per-pane local Solid signal (`createSignal<BudgetState | null>(null)`). No global store.
- D-13: 150ms CSS transition on bar width. `prefers-reduced-motion` kill switch.
- D-14: No debounce in Rust reader.

### Claude's Discretion
None declared — all gray areas resolved in D-01..D-14.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

F3 threads a budget telemetry signal from Python harness → PTY byte stream → Rust reader → Tauri Channel → Solid.js per-pane signal → 22px header HUD. The architecture reuses four established patterns without modification: the PTY reader's byte-streaming loop in `reader.rs`, the `PtyEvent` enum in `commands.rs`, the `Channel<PtyEvent>` transport, and the `agentConfig` prop gate on `PaneComponent`.

The key insight from codebase inspection: **PaneComponent does NOT currently use `PaneHeader.tsx`**. The component renders its own inline header JSX (lines 457-481 in `PaneComponent.tsx`). F3 must add the budget segment to that inline header — not to `PaneHeader.tsx`, which is imported by the grid layer but not by `PaneComponent`. This is the most important structural finding and changes the integration point.

The A10 `<Popover>` component does not yet exist — `src/status-bar/` is absent from the filesystem. F3's plan must either (a) create a minimal `<Popover>` primitive as Wave 0 scaffolding, or (b) implement the budget popover dismiss/position logic inline, structured to be replaced when A10 ships. The planner should choose option (a) — a thin, self-contained Popover component in `src/grid/` that is forward-compatible with A10's pattern.

**Primary recommendation:** Implement in five integration points with clear ownership: (1) OSC parser in `reader.rs`, (2) `BudgetUpdate` variant in `commands.rs` + TypeScript `pty-ipc.ts`, (3) `_emit_budget_osc()` helper in `recorder.py`, (4) `BudgetUpdate` routing in `PaneComponent.tsx`, (5) `BudgetBar` + `BudgetPopover` components in `src/grid/`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Budget data generation | Python harness (recorder.py) | — | Cost and token counts live inside the agent loop; harness owns them |
| OSC emission | Python harness stdout (sys.stdout.write) | — | Writing to own stdout is the correct channel from inside a PTY-hosted process |
| OSC parsing + stripping | Rust PTY reader (reader.rs) | — | The reader sees raw bytes before xterm; must strip before forwarding display bytes |
| PtyEvent routing | Rust→Frontend Channel | — | Existing Channel<PtyEvent> pattern; no new IPC needed |
| Per-pane state | Frontend (PaneComponent.tsx) | — | D-12: local signal, no global store |
| HUD rendering | Frontend (PaneComponent.tsx header area) | BudgetBar.tsx | BudgetBar is a child component; PaneComponent owns the signal and passes it as prop |
| Popover | Frontend (BudgetPopover.tsx) | Popover primitive | BudgetPopover contains the card layout; reusable Popover owns dismiss/positioning |
| Color thresholds | Frontend CSS | — | Pure CSS token lookup at render time; no Rust involvement |

---

## Standard Stack

### Core (no new packages — all existing)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `serde` + `serde_json` | existing | JSON parse/serialize in Rust for OSC payload | Already a Cargo.toml dependency via PtyEvent |
| `solid-js` | existing | Reactive signals (`createSignal`) for budget state | Project standard; per-pane budget signal uses same pattern as `focused`, `dot`, `proc` |
| `@tauri-apps/api/core` | existing | Channel<PtyEvent> transport | Established in pty-ipc.ts |

No new packages required. F3 is a pure extension of existing infrastructure.

### Installation

```bash
# No new packages to install
```

---

## Package Legitimacy Audit

> No external packages are added in this phase. All implementation uses existing dependencies.

| Package | Registry | Notes |
|---------|----------|-------|
| (none) | — | F3 adds zero new dependencies |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Python harness (inside PTY)
  recorder.py :: end_iteration()
        │
        ▼  sys.stdout.write(f"\x1b]1337;voss-budget={json}\\x07")
        │
  PTY byte stream (raw bytes via portable_pty master reader)
        │
        ▼
  reader.rs :: start_reader() read loop
        │  scan buf[..n] for ESC ] 1 3 3 7 ; v o s s - b u d g e t = ... BEL
        │  if found:
        │    → send PtyEvent::BudgetUpdate(BudgetData) on on_data channel
        │    → forward remaining display bytes as PtyEvent::Data
        │  else:
        │    → forward as PtyEvent::Data (unchanged path)
        │
  Channel<PtyEvent>  (Tauri IPC)
        │
        ▼
  pty-ipc.ts :: PtyTransport.handle()
        │  case 'budget_update': opts.onBudgetUpdate?.(ev)
        │
        ▼
  PaneComponent.tsx :: budget signal
        │  const [budget, setBudget] = createSignal<BudgetState | null>(null)
        │  transport = new PtyTransport({ ..., onBudgetUpdate: setBudget })
        │
        ▼
  PaneComponent.tsx header JSX
        │  <Show when={props.agentConfig != null && budget() != null}>
        │    <BudgetBar budget={budget()!} onClickDetail={openPopover} />
        │  </Show>
        │
        ▼
  BudgetBar.tsx (inline header segment)
  BudgetPopover.tsx (click-to-open detail card)
```

### Recommended Project Structure

```
crates/voss-app-core/src/pty/
├── reader.rs       # Add OSC 1337 parser (new fn parse_osc_1337)
├── commands.rs     # Add BudgetUpdate(BudgetData) variant + BudgetData struct

apps/voss-app/src/
├── pane/
│   ├── pty-ipc.ts          # Add 'budget_update' to PtyEvent union + onBudgetUpdate callback
│   └── PaneComponent.tsx   # Add budget signal + BudgetUpdate routing + BudgetBar mount
├── grid/
│   ├── BudgetBar.tsx        # New: inline header segment (cost + bar track + bar fill)
│   ├── BudgetPopover.tsx    # New: popover card (5 rows + expanded bar)
│   └── Popover.tsx          # New: thin reusable popover primitive (anchor-positioned)

voss/harness/
└── recorder.py     # Add _emit_budget_osc() + call at end_iteration()
```

### Pattern 1: OSC 1337 Parsing in Rust Reader

**What:** Scan the raw PTY read buffer for the OSC 1337 voss-budget sequence, extract it, and emit a typed event. Non-matching bytes pass through unchanged.

**What the current reader does (reader.rs lines 31-43):**
```rust
match reader.read(&mut buf) {
    Ok(0) => break, // EOF
    Ok(n) => {
        if on_data.send(PtyEvent::Data { bytes: buf[..n].to_vec() }).is_err() {
            break;
        }
    }
    Err(_) => break,
}
```
The reader sends every byte as `PtyEvent::Data` with no inspection. F3 adds a scan step before the send.

**Integration approach:** [ASSUMED — pattern derived from codebase analysis + OSC protocol knowledge]

```rust
// In reader.rs, replace the Ok(n) arm with:
Ok(n) => {
    let slice = &buf[..n];
    match extract_voss_osc(slice) {
        Some((json_bytes, display_bytes)) => {
            // Emit budget event first
            if let Ok(data) = serde_json::from_slice::<BudgetData>(&json_bytes) {
                let _ = on_data.send(PtyEvent::BudgetUpdate(data));
            }
            // Then emit remaining display bytes (may be empty)
            if !display_bytes.is_empty() {
                if on_data.send(PtyEvent::Data { bytes: display_bytes }).is_err() {
                    break;
                }
            }
        }
        None => {
            if on_data.send(PtyEvent::Data { bytes: slice.to_vec() }).is_err() {
                break;
            }
        }
    }
}
```

**OSC 1337 format (D-02):**
```
ESC ] 1 3 3 7 ; v o s s - b u d g e t = { json } BEL
 \x1b \x9d            ...                       \x07
```
- `ESC` = `0x1b`, `]` = `0x5d` (ST alternative: `\x9d`)
- Terminator: `BEL` = `0x07` OR `ST` = `0x1b 0x5c`
- Full prefix bytes: `[0x1b, 0x5d, 0x31, 0x33, 0x33, 0x37, 0x3b, ...]`

**Critical pitfall — buffer fragmentation:** A single PTY read can return a partial OSC sequence. The 8192-byte buffer is large enough that fragmentation is rare in practice (the JSON payload is ~100 bytes), but is theoretically possible. The simplest safe approach is to treat the buffer as a raw scan — if the OSC terminator is not found in the current read, treat the whole buffer as display bytes. Since the harness emits one OSC per LLM response (every 2-30 seconds), missed sequences are harmless (D-03: next emission has full cumulative state).

**`extract_voss_osc` pure function:**
```rust
/// Scans a PTY byte slice for one `ESC]1337;voss-budget=...BEL` sequence.
/// Returns Some((json_bytes, remaining_display_bytes)) if found, None otherwise.
/// Remaining bytes are everything before the ESC and everything after the BEL.
fn extract_voss_osc(data: &[u8]) -> Option<(Vec<u8>, Vec<u8>)> {
    const PREFIX: &[u8] = b"\x1b]1337;voss-budget=";
    let start = data.windows(PREFIX.len()).position(|w| w == PREFIX)?;
    let json_start = start + PREFIX.len();
    let end = data[json_start..].iter().position(|&b| b == 0x07)
        .map(|p| json_start + p)?;
    let json_bytes = data[json_start..end].to_vec();
    // Display bytes = everything before the ESC + everything after the BEL
    let mut display = data[..start].to_vec();
    display.extend_from_slice(&data[end + 1..]);
    Some((json_bytes, display))
}
```

**When to use:** Precisely for F3 and any future `voss-*` OSC namespace (D-02 specifies extensibility).

### Pattern 2: PtyEvent Enum Extension

**Current variants (commands.rs lines 16-21):** [VERIFIED: codebase read]
```rust
pub enum PtyEvent {
    Data { bytes: Vec<u8> },
    Exit { code: i32 },
    FgProcess { name: String },
    TitleChange { title: String },
}
```

**F3 additions:**
```rust
#[derive(serde::Serialize, serde::Deserialize, Clone)]
pub struct BudgetData {
    pub tokens_used: u64,
    pub token_limit: Option<u64>,
    pub cost_usd: f64,
    pub iteration: u32,
    pub model: String,
}

// Add to PtyEvent:
BudgetUpdate(BudgetData),
```

**Serde implications:** `PtyEvent` already derives `serde::Serialize` with `#[serde(tag = "type", rename_all = "snake_case")]`. The new variant serializes as `{ "type": "budget_update", ... }`. `BudgetData` fields need `serde::Serialize`; for the Rust-side parse step (reading from the harness JSON), it also needs `serde::Deserialize`. The TypeScript union type in `pty-ipc.ts` must add:
```typescript
| { type: 'budget_update'; tokens_used: number; token_limit: number | null; cost_usd: number; iteration: number; model: string }
```

**Existing consumers of PtyEvent** (no breakage — adding a variant to a non-exhaustive enum consumed by a `switch` in TS is additive): [VERIFIED: codebase read]
- `PtyTransport.handle()` in `pty-ipc.ts` — uses a `switch(ev.type)` with `case 'data'`, `case 'exit'`, `case 'fg_process'`, `case 'title_change'`. Adding `budget_update` with no default means it falls through silently until the new case is added.
- No Rust-side consumers of `PtyEvent` outside the test suite and reader.rs emit sites.

### Pattern 3: PaneComponent Header Integration

**Critical finding:** `PaneComponent.tsx` renders its own inline header at lines 457-481, NOT using the `PaneHeader.tsx` component. The header is:
```tsx
<div ref={headerRef} class={`pane-header${headerFlash() ? ' bell-flash' : ''}`}>
  <span class={`dot ${dot()}`}>●</span>
  ...
  <span class="spacer" />
  <button class="menu" title="menu" type="button">⋯</button>
</div>
```

The `PaneHeader.tsx` component is used by the **grid layer** (likely `GridRoot.tsx` or `SplitNode.tsx`), not by `PaneComponent.tsx`. F3 must modify the `PaneComponent.tsx` inline header, not `PaneHeader.tsx`.

**Budget signal and routing:**
```tsx
// In PaneComponent.tsx — add to existing signals block (after line 94):
const [budget, setBudget] = createSignal<BudgetState | null>(null);

// In PtyTransport constructor opts (around line 310-327):
onBudgetUpdate: (data) => setBudget(data),

// In header JSX (between spacer and menu button):
<span class="spacer" />
<Show when={props.agentConfig != null && budget() != null}>
  <BudgetBar budget={budget()!} onClickDetail={openPopover} />
</Show>
<button class="menu" ...>⋯</button>
```

**`agentConfig` prop gate:** [VERIFIED: codebase read] `PaneComponent` already receives `agentConfig?: AgentConfig` (line 44) and uses it at lines 210-223 (doSpawn) and lines 321-327 (transport opts). The gate `props.agentConfig != null` is already the pattern for agent-pane detection.

### Pattern 4: Harness OSC Emission

**Where `end_iteration()` is called (agent.py):** [VERIFIED: codebase read]

`end_iteration()` is called at three locations in `_run_turn_exec`:
1. Line 757 — done plan, low confidence (clarify exit)
2. Line 789 — done plan, normal termination
3. Line 832 — non-terminating iteration (continues loop)

All three sites have access to `iter_cost`, `iter_prompt_tokens`, `iter_completion_tokens`, `total_cost_usd`, `total_prompt_tokens`, `total_completion_tokens`, `iteration_index`, and `model`. The cumulative totals available at each call site:

| Field | Available at end_iteration call | Notes |
|-------|--------------------------------|-------|
| `tokens_used` | `total_prompt_tokens + total_completion_tokens + iter_prompt_tokens + iter_completion_tokens` | Must add current-iter to accumulated |
| `token_limit` | `token_budget` (parameter to `_run_turn_exec`) | Always available |
| `cost_usd` | `total_cost_usd + iter_cost` | Cumulative including current iter |
| `iteration` | `iteration_index + 1` | 1-based for display |
| `model` | `model` (local variable in `_run_turn_exec`) | Resolved at function entry |

**Implementation:** Add `_emit_budget_osc()` to `recorder.py`:

```python
import json
import sys

def _emit_budget_osc(
    *,
    tokens_used: int,
    token_limit: int | None,
    cost_usd: float,
    iteration: int,
    model: str,
) -> None:
    """Emit OSC 1337 voss-budget sequence to stdout (D-02).

    Caller is agent.py _run_turn_exec at each end_iteration() call site.
    The sequence is stripped by reader.rs before reaching xterm.
    """
    payload = json.dumps({
        "tokens_used": tokens_used,
        "token_limit": token_limit,
        "cost_usd": cost_usd,
        "iteration": iteration,
        "model": model,
    }, separators=(',', ':'))
    # ESC ] 1337 ; voss-budget= {json} BEL
    sys.stdout.write(f"\x1b]1337;voss-budget={payload}\x07")
    sys.stdout.flush()
```

**Where to call it in agent.py:** After each `rec.end_iteration(...)` call. The simplest approach is to add the call directly after the three `rec.end_iteration()` call sites in `_run_turn_exec`. To avoid repetition, extract into a helper that computes cumulative totals. Alternatively, add it inside `RunRecorder.end_iteration()` itself — but that introduces a UI concern into a data-recording class, which is a design smell. Prefer the call-site approach in `agent.py`.

**Important:** `_emit_budget_osc` belongs in `recorder.py` per D-04. However, the actual call must be in `agent.py` where cumulative totals are available. The simplest split: define `_emit_budget_osc` as a module-level function in `recorder.py` and import it into `agent.py`.

### Pattern 5: A10 Popover Dependency

**A10 `<Popover>` component does not exist yet.** [VERIFIED: filesystem check]
- `src/status-bar/` directory is absent
- No `.tsx` file containing "Popover" found anywhere in `src/`
- A10 has PLANS (4 wave plans) but has not been executed

F3 must provide its own popover implementation. The correct approach is to create a minimal `src/grid/Popover.tsx` that F3 uses and that A10 can later reuse or supersede.

**Minimal Popover component pattern (matches A10 D-04 contract):**
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

  // Position: below anchor, right-aligned
  const rect = props.anchor.getBoundingClientRect();

  return (
    <div
      ref={rootRef}
      style={{
        position: 'fixed',
        top: `${rect.bottom}px`,
        left: `${rect.right - 220}px`,  // 220px = popover width
        'z-index': 20,
        background: 'var(--bg-3)',
        border: '1px solid var(--border)',
      }}
    >
      {props.children}
    </div>
  );
}
```

**One-popover-at-a-time (A10 D-01):** Use a module-level signal in a shared `popoverState.ts` or implement locally in `PaneComponent.tsx`. Since `DotMenu.tsx` already implements a per-pane menu with dismiss-on-outside-click, the same pattern applies. A simple `createSignal<boolean>` per-pane for budget popover open/close is sufficient for F3.

### Anti-Patterns to Avoid

- **Don't parse OSC in the TypeScript layer.** The bytes flow through xterm which would interpret unknown OSC sequences unpredictably. Strip in Rust reader before any display bytes reach xterm.
- **Don't accumulate costs in the frontend.** D-03 explicitly requires cumulative totals in each payload. The frontend renders the latest payload as-is.
- **Don't add the budget signal to a global store.** D-12 is explicit: per-pane local signal. Each pane is independent.
- **Don't modify `PaneHeader.tsx` for the inline header slot.** As confirmed by codebase inspection, `PaneComponent.tsx` renders its own inline header — `PaneHeader.tsx` is not used here.
- **Don't use `sys.stderr` for OSC emission.** The PTY reads stdout; stderr goes to a separate stream that is NOT captured by the PTY reader. OSC MUST go to `sys.stdout`.
- **Don't omit `sys.stdout.flush()` after OSC emission.** Python's stdout is line-buffered by default in TTY mode but may be block-buffered when spawned as a subprocess. Always flush explicitly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON parse in Rust | Custom byte parser | `serde_json::from_slice` | Already in Cargo.toml; handles edge cases |
| CSS transitions | JS animation | CSS `transition: width 150ms ease-out` | D-13 explicitly specifies CSS; simpler, performant |
| Popover positioning | Complex layout engine | Simple `fixed` positioning with `getBoundingClientRect()` | Sufficient for the 22px header case; A10 can upgrade later |
| OSC byte scanning | Regex or complex state machine | Linear `windows()` scan for fixed prefix | Simpler, no regex crate needed, correct for this use case |

---

## Common Pitfalls

### Pitfall 1: PTY Read Buffer Fragmentation
**What goes wrong:** The 8192-byte read buffer in `reader.rs` may split an OSC sequence across two reads. If the JSON is truncated mid-value, `serde_json::from_slice` will fail silently.
**Why it happens:** The OS delivers PTY data in arbitrary chunk sizes. The OSC sequence is ~100 bytes. The buffer is 8192 bytes, so fragmentation is rare but possible.
**How to avoid:** Design `extract_voss_osc` to return `None` (pass through as display bytes) when no complete sequence (prefix + BEL) is found in the current buffer. Log a debug message but don't error. Since each emission is cumulative (D-03), the next iteration's emission will have the full state.
**Warning signs:** Budget HUD never updates despite harness running. Add a debug log when `serde_json::from_slice` fails.

### Pitfall 2: Harness Not Running in PTY Context
**What goes wrong:** When running `voss` from a non-PTY context (e.g., piped in CI), `sys.stdout` is block-buffered or directed to a file. The OSC sequence goes nowhere or appears in CI logs as garbage.
**Why it happens:** Python's stdout buffering depends on whether it's connected to a TTY.
**How to avoid:** Always call `sys.stdout.flush()` after OSC emission. This is harmless in PTY mode and ensures the sequence is not lost in buffered mode.
**Warning signs:** OSC sequences appear in CI test output or recorded session files as literal `\x1b]1337;...` strings.

### Pitfall 3: `token_limit = None` (Unlimited Budget) Breaks Bar
**What goes wrong:** If `token_limit` is `null` in the JSON payload, the bar tries to compute `tokens_used / null * 100` and gets `NaN` or `Infinity`.
**Why it happens:** D-07 explicitly allows `token_limit: null` for unlimited budgets. The threshold computation must guard for this.
**How to avoid:** `pct = token_limit != null ? (tokens_used / token_limit) * 100 : 0`. Then check `token_limit != null` before rendering the bar track.
**Warning signs:** Bar renders as 0% or full-width when running without budget cap.

### Pitfall 4: PaneHeader vs PaneComponent Header Confusion
**What goes wrong:** Developer modifies `PaneHeader.tsx` expecting to see changes in pane display, but nothing updates because `PaneComponent.tsx` renders its own inline header.
**Why it happens:** The project has two header patterns — `PaneHeader.tsx` (used by grid layer) and the inline header in `PaneComponent.tsx`. They diverged during A3.
**How to avoid:** F3 modifies `PaneComponent.tsx` lines 457-481 (the inline `<div class="pane-header">` block), not `PaneHeader.tsx`.
**Warning signs:** Budget bar added to `PaneHeader.tsx` but never appears in the running app.

### Pitfall 5: Solid.js Rendering Bug with `<Show when={condition && signal()}>` Double Access
**What goes wrong:** Inside `<Show when={props.agentConfig != null && budget() != null}>`, if `budget()` is null during the render of the `Show`'s children, accessing `budget()!` with a TypeScript non-null assertion will return null at runtime.
**Why it happens:** Solid.js evaluates the `when` condition reactively, but the `children` JSX is also a function. If the condition check and the `budget()!` access are in separate reactive contexts, they may not be synchronously consistent.
**How to avoid:** Pass `budget()` as a prop to `<BudgetBar>` from within the Show's children: `<Show when={...}>{(b) => <BudgetBar budget={b()} ... />}</Show>` is not how Solid Show works. Instead, use a memo: `const budgetMemo = () => budget()` and `<Show when={budgetMemo()}>{(b) => <BudgetBar budget={b} ... />}</Show>`. The `Show` component passes the truthy value to its children accessor.
**Warning signs:** TypeScript errors about `BudgetState | null` not assignable to `BudgetState`.

### Pitfall 6: One-Popover-at-a-Time Not Enforced
**What goes wrong:** Multiple budget popovers open simultaneously when clicking budget bars on different panes.
**Why it happens:** Each pane has its own `budget` signal and popover open/close state. Without coordination, multiple can be open.
**How to avoid:** Use a module-level signal `const [openPopoverPaneId, setOpenPopoverPaneId] = createSignal<string | null>(null)` in a shared module (e.g., `src/grid/activePopover.ts`). Each pane checks whether its ID is the open one. When a pane's budget bar is clicked, it sets the module-level signal to its pane ID.
**Warning signs:** Clicking budget bars on two panes shows two popovers simultaneously.

### Pitfall 7: OSC Emitted to sys.stderr in Test/CI Mode
**What goes wrong:** During harness tests, stdout may be captured by pytest but stderr is not. If the OSC emission accidentally goes to stderr, tests that capture stdout see nothing and tests that check stderr see garbage.
**Why it happens:** Accidental `print()` or `sys.stderr.write()` instead of `sys.stdout.write()`.
**How to avoid:** Explicitly test that `_emit_budget_osc` writes to `sys.stdout` using `monkeypatch` to capture stdout.
**Warning signs:** `test_emit_budget_osc` passes but budget HUD never updates in the real app.

---

## Code Examples

### OSC extraction in Rust (pure function)

```rust
// Source: F3 design, based on OSC escape sequence specification
/// Returns Some((json_bytes, display_bytes)) if an OSC 1337 voss-budget sequence
/// is found in `data`, else None (pass through unchanged).
fn extract_voss_osc(data: &[u8]) -> Option<(Vec<u8>, Vec<u8>)> {
    const PREFIX: &[u8] = b"\x1b]1337;voss-budget=";
    // Find the prefix
    let start = data.windows(PREFIX.len()).position(|w| w == PREFIX)?;
    let json_start = start + PREFIX.len();
    // Find BEL terminator (0x07) after the prefix
    let rel_end = data[json_start..].iter().position(|&b| b == 0x07)?;
    let end = json_start + rel_end;
    // Extract JSON bytes
    let json_bytes = data[json_start..end].to_vec();
    // Display bytes = before ESC + after BEL
    let mut display = data[..start].to_vec();
    display.extend_from_slice(&data[end + 1..]);
    Some((json_bytes, display))
}
```

### BudgetData Rust struct

```rust
// Source: F3 design, extending commands.rs
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct BudgetData {
    pub tokens_used: u64,
    pub token_limit: Option<u64>,
    pub cost_usd: f64,
    pub iteration: u32,
    pub model: String,
}
```

### Python OSC emission helper

```python
# Source: F3 design, for recorder.py
import json
import sys

def _emit_budget_osc(
    *,
    tokens_used: int,
    token_limit: int | None,
    cost_usd: float,
    iteration: int,
    model: str,
) -> None:
    """Emit OSC 1337 voss-budget sequence to stdout (D-02).

    Written to sys.stdout. Caller must ensure this runs inside a PTY context.
    The sequence is stripped by reader.rs before reaching xterm.
    """
    payload = json.dumps(
        {
            "tokens_used": tokens_used,
            "token_limit": token_limit,
            "cost_usd": cost_usd,
            "iteration": iteration,
            "model": model,
        },
        separators=(",", ":"),
    )
    sys.stdout.write(f"\x1b]1337;voss-budget={payload}\x07")
    sys.stdout.flush()
```

### Cost formatting (TypeScript)

```typescript
// Source: F3-UI-SPEC.md copywriting contract
function formatCostHeader(cost_usd: number): string {
  if (cost_usd < 0.01) return `$${cost_usd.toFixed(4)}`;
  if (cost_usd < 100)  return `$${cost_usd.toFixed(2)}`;
  return `$${Math.round(cost_usd)}`;
}

function formatCostPopover(cost_usd: number): string {
  if (cost_usd < 0.01) return `$${cost_usd.toFixed(4)}`;
  return `$${cost_usd.toFixed(2)}`;
}
```

### Bar fill color threshold computation

```typescript
// Source: F3-CONTEXT.md D-08 + F3-UI-SPEC.md threshold table
function barFillColor(pct: number): string {
  if (pct < 70) return 'var(--accent-green)';
  if (pct < 90) return 'var(--accent-amber)';
  return 'var(--accent-red)';
}

function barFillPct(tokens_used: number, token_limit: number | null): number {
  if (token_limit == null) return 0;
  return Math.min((tokens_used / token_limit) * 100, 100);
}
```

### BudgetBar component skeleton

```tsx
// Source: F3-UI-SPEC.md component inventory + layout contract
import type { BudgetState } from '../pane/pty-ipc';

interface BudgetBarProps {
  budget: BudgetState;
  onClickDetail: (anchor: HTMLElement) => void;
}

export default function BudgetBar(props: BudgetBarProps) {
  let buttonRef!: HTMLButtonElement;
  const pct = () => barFillPct(props.budget.tokens_used, props.budget.token_limit);
  const hasLimit = () => props.budget.token_limit != null;

  return (
    <button
      ref={buttonRef}
      type="button"
      style={{
        display: 'flex',
        'align-items': 'center',
        gap: '4px',
        background: 'transparent',
        border: 'none',
        padding: '0 4px',
        'flex-shrink': 0,
        cursor: 'default',
      }}
      aria-label={
        hasLimit()
          ? `Budget: ${formatCostHeader(props.budget.cost_usd)}, ${Math.round(pct())}% of ${props.budget.token_limit} tokens. Open detail`
          : `Budget: ${formatCostHeader(props.budget.cost_usd)}. Open detail`
      }
      onClick={() => props.onClickDetail(buttonRef)}
    >
      <span style={{ color: 'var(--fg-2)', 'font-size': '11px', 'max-width': '44px',
                     'white-space': 'nowrap', overflow: 'hidden' }}>
        {formatCostHeader(props.budget.cost_usd)}
      </span>
      <Show when={hasLimit()}>
        <div style={{ width: '48px', height: '4px', background: 'var(--bg-2)',
                      position: 'relative', 'flex-shrink': 0 }}>
          <div
            class="budget-bar-fill"
            style={{
              height: '4px',
              width: `${Math.max(pct(), 0)}%`,
              'min-width': pct() > 0 ? '2px' : '0',
              background: barFillColor(pct()),
            }}
          />
        </div>
      </Show>
    </button>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom IPC for telemetry data | Reuse PTY byte stream + OSC sequences | F3 design decision | Zero new IPC channels; harness stdout is already the PTY data path |
| Global stores for per-pane state | Per-pane local Solid signals | D-12 decision | N panes = N independent stores; no cross-pane coordination overhead |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_emit_budget_osc` belongs in `recorder.py` but is called from `agent.py` | Pattern 4: Harness Emission | Low — recorder.py is the logical owner; agent.py has the call sites. If CONTEXT.md is reread, D-04 says "recorder.py" but agent.py has the data. The split is the correct answer. |
| A2 | Buffer fragmentation is safely handled by silently passing through as display bytes | Pattern 1: OSC parsing | Low — since payloads are ~100 bytes and buffer is 8192 bytes, fragmentation probability is low. However, if the harness is running very fast (concurrent runs), the risk increases. |
| A3 | A10 Popover will be forward-compatible with the F3 thin `Popover.tsx` implementation | Pattern 5: Popover dependency | Medium — A10 may redesign its Popover differently. F3's BudgetPopover should use the Popover primitive loosely so it can be swapped. |
| A4 | `sys.stdout.write()` goes to the correct PTY stream even when harness is spawned via `spawn_agent` Tauri command | Pattern 4: Harness emission | Medium — `spawn_command_session` in mod.rs spawns the process with its own PTY; stdout IS the PTY stream. But if the harness redirects its own stdout for logging, this breaks. Inspect `agent.py` launch surface if issues arise. |

---

## Open Questions

1. **Which exact end_iteration call sites in agent.py should emit OSC?**
   - What we know: `end_iteration()` is called at lines ~757, ~789, ~832 in `_run_turn_exec`. All three have cumulative totals available.
   - What's unclear: Should the clarify-exit (line 757) also emit? The user may want cost tracking even for low-confidence terminations.
   - Recommendation: Emit at all three sites. D-04 says "emit after each LLM response" — all three paths close a completed LLM response. Consistent emission is better for the HUD.

2. **Should `_emit_budget_osc` be on `RunRecorder` or module-level in `recorder.py`?**
   - What we know: `RunRecorder.end_iteration()` doesn't have access to cumulative totals (it only knows the current iteration's `cost_usd`). The caller in `agent.py` accumulates `total_cost_usd` and `total_prompt_tokens` separately.
   - What's unclear: Whether to pass cumulative totals into `end_iteration()` or emit separately after calling it.
   - Recommendation: Keep `_emit_budget_osc` as a standalone module-level function in `recorder.py` and call it from `agent.py` after each `rec.end_iteration()`. Don't couple UI emission to the data recorder method signature.

3. **Is the PaneComponent header shared with the grid layer's PaneHeader.tsx, or is it a separate implementation?**
   - What we know: [VERIFIED by codebase read] `PaneComponent.tsx` renders its own inline header at lines 457-481. `PaneHeader.tsx` is a separate component used by the grid layer.
   - What's unclear: Whether A3 intended to eventually reconcile these, or whether the divergence is permanent.
   - Recommendation: Modify the inline header in `PaneComponent.tsx`. Note in the implementation that this divergence exists.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `serde_json` | Rust OSC JSON parse | ✓ | existing Cargo.toml | — |
| `vitest` + `jsdom` | Frontend unit tests | ✓ | existing vitest.config.ts | — |
| `pytest` + `.venv` | Python harness tests | ✓ | existing `.venv` | — |
| `cargo test` | Rust PTY reader tests | ✓ | existing | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Frontend framework | Vitest + jsdom (vitest.config.ts: `environment: 'jsdom'`) |
| Rust framework | `cargo test` (crates/voss-app-core) |
| Python framework | pytest (`.venv/bin/python -m pytest`) |
| Frontend quick run | `cd apps/voss-app && npm run test -- --reporter=dot` |
| Frontend full suite | `cd apps/voss-app && npm run test` |
| Rust quick run | `cd crates/voss-app-core && cargo test pty` |
| Python quick run | `.venv/bin/python -m pytest voss/harness/ -x -q` |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | File |
|-----|----------|-----------|-------------------|------|
| D-02 | `extract_voss_osc` correctly parses prefix + BEL, strips from display bytes | unit (Rust) | `cargo test osc` | `crates/voss-app-core/src/pty/tests.rs` — Wave 0 |
| D-02 | `extract_voss_osc` returns None for non-matching bytes (pass-through) | unit (Rust) | `cargo test osc` | same |
| D-02 | `extract_voss_osc` handles partial sequences (no BEL found) | unit (Rust) | `cargo test osc` | same |
| D-03 | `_emit_budget_osc` writes correct OSC format to stdout | unit (Python) | `.venv/bin/python -m pytest voss/harness/test_budget_osc.py -x` | `voss/harness/test_budget_osc.py` — Wave 0 |
| D-07 | `token_limit: None` → no bar track rendered | unit (TSX) | `npm run test -- BudgetBar` | `src/grid/__tests__/BudgetBar.test.tsx` — Wave 0 |
| D-08 | Color threshold logic: <70% green, 70-90% amber, ≥90% red | unit (TSX) | `npm run test -- BudgetBar` | same |
| D-08 | Bar fill width clamped to [0, 100]% | unit (TSX) | `npm run test -- BudgetBar` | same |
| D-09 | BudgetBar click opens popover; second click closes it | unit (TSX) | `npm run test -- BudgetBar` | same |
| D-10 | Popover dismisses on click-outside | unit (TSX) | `npm run test -- Popover` | `src/grid/__tests__/Popover.test.tsx` — Wave 0 |
| D-10 | Popover dismisses on Escape | unit (TSX) | `npm run test -- Popover` | same |
| D-12 | PaneComponent budget signal starts null; updates on BudgetUpdate event | unit (TSX) | `npm run test -- PaneComponent` | `src/pane/__tests__/pty-ipc.test.ts` — extend |
| D-13 | `.budget-bar-fill` has CSS transition; media query disables it | CSS audit | manual / vitest CSS check | `src/grid/BudgetBar.tsx` |
| — | Cost format: <$0.01 → 4dp, <$100 → 2dp, ≥$100 → 0dp | unit (TSX) | `npm run test -- BudgetBar` | same |

### Sampling Rate
- **Per task commit:** `cd apps/voss-app && npm run test -- --reporter=dot` + `cargo test pty -q`
- **Per wave merge:** Full vitest suite + full cargo test
- **Phase gate:** All suites green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `crates/voss-app-core/src/pty/tests.rs` — add `test_extract_voss_osc_*` tests (pure function, Tauri-free)
- [ ] `voss/harness/test_budget_osc.py` — new file, tests `_emit_budget_osc` stdout output
- [ ] `apps/voss-app/src/grid/__tests__/BudgetBar.test.tsx` — new file
- [ ] `apps/voss-app/src/grid/__tests__/Popover.test.tsx` — new file
- [ ] `apps/voss-app/src/grid/BudgetBar.tsx` — new component file
- [ ] `apps/voss-app/src/grid/BudgetPopover.tsx` — new component file
- [ ] `apps/voss-app/src/grid/Popover.tsx` — new popover primitive

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | OSC data is display data in an authenticated local PTY session |
| V3 Session Management | no | Budget state is per-PTY-session, no persistent auth |
| V4 Access Control | no | Local IPC only; no cross-origin or network boundary |
| V5 Input Validation | **yes** | `serde_json::from_slice` with typed struct; unknown fields silently rejected |
| V6 Cryptography | no | No secrets in budget payload; tokens/cost are non-sensitive metrics |

### Known Threat Patterns for OSC Parsing

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| OSC injection via terminal output (crafted process output mimicking `voss-budget=`) | Spoofing | Accept only from the harness process — but the PTY reader cannot distinguish source. Mitigation: payload is non-sensitive (cost/token counts only); injected fake data causes cosmetic HUD corruption, not security breach. No secrets in payload (D-03). |
| Large JSON payload in OSC sequence causing allocation spike | Denial of Service | `serde_json::from_slice` on a slice bounded by the 8192-byte read buffer. Max JSON size is 8192 bytes. No unbounded allocation. |
| Malformed JSON causing Rust panic | DoS | `serde_json::from_slice` returns `Result` — errors are silently discarded, not panicked. |
| XSS via model name field in popover | Tampering | Model name is rendered as text content in JSX, not `innerHTML`. Solid.js escapes text nodes. |

**Security summary:** The OSC payload contains only non-sensitive telemetry (token counts, cost, iteration count, model name). An attacker who can inject OSC sequences into the PTY stream can cause cosmetic HUD corruption but cannot escalate privileges, exfiltrate secrets, or cause crashes. The threat surface is acceptable for local developer tooling.

---

## Sources

### Primary (HIGH confidence)
- `crates/voss-app-core/src/pty/reader.rs` — exact reader loop implementation (lines 17-58)
- `crates/voss-app-core/src/pty/commands.rs` — exact PtyEvent enum (lines 14-21)
- `apps/voss-app/src/pane/PaneComponent.tsx` — inline header at lines 457-481, agentConfig prop at line 44, existing signals at lines 84-95
- `apps/voss-app/src/pane/pty-ipc.ts` — PtyEvent union (lines 12-15), AgentConfig (lines 17-21), PtyTransport.handle() (lines 62-96)
- `apps/voss-app/src/grid/PaneHeader.tsx` — confirmed NOT used by PaneComponent.tsx
- `voss/harness/recorder.py` — `end_iteration()` signature (lines 148-186)
- `voss/harness/agent.py` — `_run_turn_exec()` call sites for `end_iteration()` (lines 757, 789, 832)
- `apps/voss-app/src/styles/variant-b.css` — confirmed `--accent-green: #6fd28f`, `--accent-amber: #e8b86c`, `--accent-red: #e87b7b`
- `.planning/phases/F3-budget-token-visualization/F3-CONTEXT.md` — all decisions D-01..D-14
- `.planning/phases/F3-budget-token-visualization/F3-UI-SPEC.md` — component inventory, layout contract, typography, color

### Secondary (MEDIUM confidence)
- `.planning/phases/A10-voss-app-status-bar/A10-CONTEXT.md` — D-04 Popover component contract (confirms component should exist but filesystem shows it does not yet)
- `.planning/phases/F1-durable-session-persistence/F1-CONTEXT.md` — D-06 agentConfig prop definition
- `apps/voss-app/src/grid/DotMenu.tsx` — click-outside/Esc dismiss pattern reference for Popover

### Tertiary (LOW confidence — training knowledge)
- OSC escape sequence format and iTerm2 1337 namespace — well-documented protocol; BEL terminator at 0x07

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all existing infrastructure verified by direct codebase reads
- OSC parsing approach: HIGH — pure function, no state machine, verified buffer constants
- Harness emission point: HIGH — exact function signatures and call sites confirmed in agent.py and recorder.py
- PaneComponent integration: HIGH — exact JSX structure confirmed; critical finding that PaneHeader.tsx is NOT used here
- A10 Popover dependency: HIGH — filesystem confirms `src/status-bar/` does not exist; F3 must create its own

**Research date:** 2026-05-21
**Valid until:** 2026-06-21 (stable codebase; expires if reader.rs, commands.rs, or PaneComponent.tsx are modified)
