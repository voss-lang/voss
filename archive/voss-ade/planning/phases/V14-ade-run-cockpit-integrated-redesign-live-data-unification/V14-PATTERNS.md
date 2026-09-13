# Phase V14: ADE Run Cockpit (Integrated Redesign + Live Data Unification) - Pattern Map

**Mapped:** 2026-06-08
**Files analyzed:** 16 new/modified (13 TS/TSX + 1 Rust + 2 refactors)
**Analogs found:** 16 / 16 (all have in-repo analogs — this is a recomposition phase)

> Recomposition phase over the BUILT V11 org view. Almost every new file copies an existing in-repo pattern. The research (`V14-RESEARCH.md`) already cites file:line analogs; this map turns those into concrete copy-from excerpts the planner pastes into plan actions.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/org/model/normalized.ts` | model (types) | transform | `src/org/types.ts` | role-match (pure type module) |
| `src/org/model/adapters.ts` | utility (pure) | transform | `src/org/boardDerive.ts` | exact (pure, no Solid, fixture-tested) |
| `src/org/model/bridge.ts` | utility (pure) | transform | `src/org/boardDerive.ts` + `src/pane/budgetRegistry.ts` | exact (pure resolver + signal map) |
| `src/org/selection.ts` | store | event-driven | `src/org/orgStore.ts` (module-level `createSignal`) | exact |
| `src/org/attention/attentionQueue.ts` | store/aggregator | pub-sub | `src/pane/budgetRegistry.ts` (signal + immutable update) | role-match |
| `src/org/cockpit/CockpitShell.tsx` | component (shell) | request-response | `src/org/OrgViewShell.tsx` | exact (replaces it; lift load/picker, drop tabs) |
| `src/org/cockpit/RunCommandBar.tsx` | component | request-response | `src/components/modal/AgentLaunchModal.tsx` (config assembly) + `pty-ipc.ts spawnAgent` | role-match (new surface, nearest = launch-config builder) |
| `src/org/cockpit/CardDrawer.tsx` | component (composer) | request-response | `src/org/OrgViewShell.tsx:211-248` (panel prop-wiring) | role-match (composes existing panel bodies) |
| `src/org/cockpit/GateBar.tsx` | component | request-response | `src/org/panels/BoardPanel.tsx:24-30,127-135` (budget color/bar) | role-match |
| `src/org/live/sseClient.ts` | service | streaming | `sdk/typescript/src/client/sse.ts` (`subscribeToEvents`) | exact (consume, don't re-implement) |
| `src/org/swarmReconcile.ts` | utility (pure) | transform | `src/org/boardDerive.ts` (`cardsFromRunData`) | exact (manifest→cards adapter) |
| `src/components/modal/AgentLaunchModal.tsx` | component (modal) | request-response | itself (refactor; strip config-heavy bits per D-09) | exact (in-place) |
| `src/components/modal/AdoptAgentModal.tsx` | component (modal) | request-response | `src/components/modal/AgentLaunchModal.tsx` (backdrop/focus/Esc/⌘↵ shell) | exact (modal scaffold) |
| `src-tauri/src/lib.rs` (`spawn_managed_agent`) | command (Tauri) | event-driven | `src-tauri/src/lib.rs:183-220` (`spawn_agent`) | exact (clone + sandbox-wrap argv) |
| `crates/voss-app-core/src/pty/mod.rs` (sandbox wrap) | utility (Rust) | file-I/O | `pty/mod.rs:189-245` (`spawn_command_session_with_env`) | exact (wrap `cmd_binary`/`cmd_args`) |
| `src/App.tsx` (`handleLaunchAgent` wire + Live/Review) | integration | event-driven | `src/App.tsx:268-272` (stub) + `:1183,1263` (`display:none` swap) | exact (complete the stub) |

---

## Pattern Assignments

### `src/org/model/adapters.ts` (utility, transform) — VCKP-01

**Analog:** `src/org/boardDerive.ts` (pure module, no Solid imports, fixture-testable)

**Pure-module convention** (`boardDerive.ts:1-15`): header comment states "No Solid imports, no produce/structuredClone — plain reads + object literals." **Copy this discipline exactly** — keeps adapters fixture-testable and avoids the `produce`/`DATA_CLONE_ERR` footgun (Pitfall 5).

**Snapshot-spine derivation to mirror** (`boardDerive.ts:44-58`):
```typescript
export function cardsFromRunData(data: RunData | null): BoardCard[] {
  if (!data) return [];
  return data.session_tree.nodes
    .filter((n) => n.parent_run_id !== null)
    .map((n) => ({
      id: n.id, title: n.scope ?? n.id, role: n.role,
      risk: deriveRisk(n), column: deriveColumn(n),
      spent: n.envelope.spent, limit: n.envelope.limit,
    }));
}
```
`buildModel()` takes this card list as the **spine** and overlays live fields. The snapshot card `id` IS the `sessionNodeId` (`boardDerive.ts:48` uses `n.id`).

**Live-plane overlay source — registry shape** (`crates/voss-app-core/src/agent_registry.rs:23-31`, serialized camelCase in `App.tsx:108-117`):
```typescript
interface AgentEntry { paneId; sessionId; cliBinary; cliArgs; cwd; status; lastSeen }
```
Fetched via `invoke<AgentEntry[]>('get_active_agents', { workspacePath })` (`App.tsx:122`). Live budget overlay source = `budgetByPaneId()` (`budgetRegistry.ts:39`), keyed by `paneId`, value `BudgetEntry = BudgetState & { lastSeenMs }`.

**Anti-pattern (Pitfall 2):** do NOT add live fields to `RunData` or edit `guards.ts` — the overlay lives only in the new normalized model. `guards.ts:26-43 assertRunData` must stay green.

---

### `src/org/model/bridge.ts` (utility, transform) — VCKP-02 [KEYSTONE]

**Analog:** `src/org/boardDerive.ts` (pure resolver) + `src/pane/budgetRegistry.ts` (signal-backed id map with immutable updates)

**The keystone is RESOLVED in research** — two distinct bridges (RESEARCH "Keystone" §). `resolveCard` is the pure contract:
```typescript
// from RESEARCH Code Examples — copy verbatim as the contract
export interface BridgeMaps {
  cardToPane: Record<string, string>;        // terminal agents (client-minted)
  cardToSessionNode: Record<string, string>; // native runs (harness sessionID) + snapshot node ids
}
export function resolveCard(maps: BridgeMaps, cardId: string):
  { paneId?: string; sessionNodeId?: string } {
  return {
    paneId: maps.cardToPane[cardId],
    sessionNodeId: maps.cardToSessionNode[cardId] ?? cardId, // snapshot: card id === node id
  };
}
```

**Signal-map storage pattern** (copy `budgetRegistry.ts:10-37` — module-level signal + immutable spread update, NO `produce`):
```typescript
const [budgetByPaneId, setBudgetByPaneId] = createSignal<Record<string, BudgetEntry>>({});
export function registerPaneBudget(paneId, data) {
  setBudgetByPaneId((prev) => { /* dedup */ return { ...prev, [paneId]: {...data, lastSeenMs: Date.now()} }; });
}
```
The `cardToPane` map is a `createSignal<Record<string,string>>({})` updated the same way.

**Bridge B convention (terminal agents, zero Rust change):** mint `cardId = crypto.randomUUID()` client-side and **pass it as the `sessionId` arg** to `spawnAgent` (the `session_id` column already exists — `spawn_agent` at `lib.rs:190,216`; `spawnAgent` arg at `pty-ipc.ts:174-184`). Then store `cardToPane[cardId] = paneId`.

**Bridge A convention (native runs):** store the V13.1 `createSession` response `id` as `cardToSessionNode[cardId]`; every SSE event carries that same `sessionID` (PROTOCOL §6). Verify A1 (native id == node id) against a real `.voss/sessions` tree in W0.

**Pitfall 1:** `registry.session_id ≠ SessionTreeNode.id` today — never join them directly.

---

### `src/org/selection.ts` (store) — VCKP-01/05

**Analog:** `src/org/orgStore.ts` (module-level `createSignal` global-signal pattern)

**Copy this exact pattern** (`orgStore.ts:11-15`):
```typescript
import { createSignal } from 'solid-js';
export const [runData, setRunData] = createSignal<RunData | null>(null);
export const [currentRunId, setCurrentRunId] = createSignal<string | null>(null);
```
→ becomes:
```typescript
// src/org/selection.ts
export const [selectedCardId, setSelectedCardId] = createSignal<string | null>(null);
export const [selectedRunId, setSelectedRunId] = createSignal<string | null>(null);
```
**Hoist** the currently-local `selectedCardId` out of `OrgViewShell.tsx:70` into this module so Board + drawer + timeline + gate bar all read one signal (the VCKP-05 single-selection acceptance). This is the only change needed to make the acceptance test pass: select once → ≥2 surfaces observe it.

---

### `src/org/attention/attentionQueue.ts` (store/aggregator) — VCKP-04

**Analog:** `src/pane/budgetRegistry.ts` (signal + dedup'd immutable update)

**Aggregator signal** mirrors `budgetRegistry.ts:10-28` (module signal, immutable spread, dedup-on-equal). Queue items come from two planes:
- **Snapshot decisions:** Blocked column via `boardDerive.deriveColumn` (→ `'Blocked'`), sign-off via `RunFinal.sign_off` (`types.ts:99-116`), `unsupported_claims` (`types.ts:182` on `AuditReport`).
- **Live SSE events:** `permission.updated` / `gate.updated` / `budget.updated` / `confidence.updated` / `session.idle` — typed as `AgentEvent` from `sdk/typescript/src/client/sse.ts:6` (`components["schemas"]["EventEnvelope"]["event"]`).

Each item deep-links via `resolveCard` (bridge) to its card/session. **Pitfall 6:** for adopted external agents, queue copy must NOT promise per-tool gating (tier C).

---

### `src/org/cockpit/CockpitShell.tsx` (component shell) — VCKP-05 [replaces OrgViewShell, D-01]

**Analog:** `src/org/OrgViewShell.tsx` (the file being replaced)

**LIFT verbatim** the run-load + run-picker logic (`OrgViewShell.tsx:74-110`): `onMount` auto-load most-recent run (`:74-80`), the `pickerOpen`/`pickRun` picker (`:107-110`), the document keydown/click cleanup (`:82-103`), and the loading/error `<Show>` wrappers (`:184-209`).

**REMOVE** (D-01/D-02): `ORG_TABS` (`:45-56`), `activeTab` signal (`:68`), the `org-tab-bar` (`:168-181`), and the one-panel-at-a-time `<Show when={activeTab()===...}>` switch (`:211-248`).

**REPLACE WITH** a 4-region layout. The panel-prop wiring to copy is already in the tab switch — the panels accept `data` + `onCardSelect` + `selectedCardId` (`OrgViewShell.tsx:214-219`):
```tsx
<BoardPanel data={data()} onCardSelect={setSelectedCardId} selectedCardId={selectedCardId()} />
```
In the cockpit, `setSelectedCardId`/`selectedCardId` come from `src/org/selection.ts` (global), not local state. Board spine = `BoardPanel`; drawer composes `Audit/Verdict/Diff/Scope/Budget/Blocked` bodies; rail = `SessionTreePanel + ReplayPanel`; gate bar = new `GateBar`. All panels reused verbatim (D-02).

---

### `src/org/cockpit/RunCommandBar.tsx` (component) — VCKP-03 [NEW surface]

**Analog (config assembly):** `src/components/modal/AgentLaunchModal.tsx:99-152` (`buildConfig` → `{cliBinary, cliArgs, taskPrompt}`)
**Analog (terminal launch path):** `src/pane/pty-ipc.ts:167-186` (`spawnAgent`)

**Config-assembly pattern to mirror** (`AgentLaunchModal.tsx:99-152`): build a typed config object from segmented-control state. RunCommandBar assembles `{goal, mode, team, scope, budget, target: 'native'|'terminal'}`.

**Terminal start** invokes the existing path — `spawnAgent` (`pty-ipc.ts:174-184`), passing the minted `cardId` as `sessionId` (Bridge B). In `App.tsx` this currently dead-ends at the `handleLaunchAgent` stub (`:268-272`) — that stub must be completed (see App.tsx entry below).

**Native start** calls the V13.1 SDK `createSession` (fixture/mock in V14; gated). Store the returned `id` into `bridge.cardToSessionNode` (Bridge A).

**Validation rule (acceptance):** Auto mode with no budget OR no scope is blocked with a visible reason — mirror the disabled-with-reason discipline from `decisionActions.ts:1-11` (never a silent no-op). **Mode never hidden in placeholder** (segmented control, like `AgentLaunchModal.tsx:218-229`).

**Segmented-control markup to reuse** (`AgentLaunchModal.tsx:218-229` `modal-segmented` / `modal-segmented__btn--active`).

---

### `src/org/cockpit/CardDrawer.tsx` (component composer) — VCKP-05

**Analog:** `src/org/OrgViewShell.tsx:211-248` (panel prop-wiring)

Composes existing panel bodies as drawer sections, all reading the global `selectedCardId()`. Reuse the exact prop signatures the tab switch already passes (`OrgViewShell.tsx:224-245`):
```tsx
<AuditPanel data={data()} /> <VerdictPanel data={data()} />
<DiffPanel data={data()} selectedCardId={selectedCardId()} onCardSelect={setSelectedCardId} />
<ScopePanel data={data()} /> <BudgetPanel data={data()} /> <BlockedPanel data={data()} />
```
**D-07 live-pane peek:** the drawer shows a read-only pane peek + an "Open in grid" button that flips `orgViewOpen` (`App.tsx:240`). **D-08:** persistent drawer with a no-selection empty state (mirror the `<Show ... fallback={empty}>` idiom in `BoardPanel.tsx:149-155`).

---

### `src/org/cockpit/GateBar.tsx` (component) — VCKP-05

**Analog:** `src/org/panels/BoardPanel.tsx:24-30` (`budgetColor`) + `:127-135` (budget bar) + `BudgetPanel`/`ScopePanel` bodies

**Budget threshold coloring to copy** (`BoardPanel.tsx:24-30`):
```typescript
function budgetColor(pct: number): string {
  return pct >= 90 ? 'var(--accent-red)' : pct >= 70 ? 'var(--accent-amber)' : 'var(--accent-green)';
}
```
Gate bar reflects the selected card's envelope (`SessionTreeNode.envelope` `{limit, spent}` — `types.ts:10-13,84-95`). **Per-card field check (constraint):** per-card confidence is a LIVE SSE event, not a snapshot field — render it only from the live overlay, never from `RunData`. Monospace numerics via `var(--font-mono)` (`BoardPanel.tsx:76`).

---

### `src/org/live/sseClient.ts` (service, streaming) — VCKP-06 [GATED V13.1]

**Analog:** `sdk/typescript/src/client/sse.ts` (`subscribeToEvents` — SHIPPED, consume verbatim)

**Consume, do not re-implement** (`sse.ts:12-67`): async-generator over `fetch` + `EventSourceParserStream`, sets `Authorization: Bearer ${token}`, handles `AbortSignal`. Wrapper pattern:
```typescript
const ac = new AbortController();
(async () => {
  for await (const ev of subscribeToEvents(baseUrl, sessionId, token, ac.signal)) {
    // route ev by type into attentionQueue + model overlay, matched by ev.sessionID
  }
})();
```
**Anti-pattern:** never use raw `EventSource` (can't set Bearer header — `sse.ts:20`). **Pitfall 4:** the webview CANNOT start `voss serve` (`launcher.ts` imports `node:child_process`); V14 only *consumes* — fixture/mock the stream. Render a `live`/`snapshot` label based on whether a stream is active for the selected run.

---

### `src/org/swarmReconcile.ts` (utility, transform) — VCKP-07 [GATED A13]

**Analog:** `src/org/boardDerive.ts` `cardsFromRunData` (manifest→cards adapter)

Pure adapter: `.voss/swarm/manifest.json` agents → roster rows + board cards; per-agent swarm status (pending/running/complete) maps to board columns. Rust side already exists: `write_swarm_files`/`watch_swarm_results` (`lib.rs:603,635`) + `voss://swarm-result-added` event (`lib.rs:558`). Absent `.voss/swarm/` degrades to "no swarm" — mirror the `if (!data) return []` null-tolerance of `boardDerive.ts:46`.

---

### `src/components/modal/AgentLaunchModal.tsx` (REFACTOR) — VCKP-11 [D-09]

**Analog:** itself — refactor in place.

**KEEP:** the modal scaffold — backdrop click-out (`:158-162`), Esc + ⌘↵ keymap (`:164-173`), focus-first-on-mount (`:94-97`), `modal-segmented` controls, CLI list (`CLI_TABS:7-14`).

**REMOVE (D-09):** the raw-command Custom field (`:336-356`), the effort/reasoning matrices (`CLI_PROFILES:24-50`, `:233-250`), the Skip-Permissions toggle and explainer, the task `<textarea>` placeholder explainer copy (`:273`).

**ADD:** CLI preset cards each showing the user's **default model** (e.g. "Claude Code · sonnet-4-6"); one optional "what should it work on?" prompt; working-dir + pane placement (Right/Below/New tab). Preset resolves the configured CLI command/model (reuse the `binaryMap` idea `:124-129`). **Managed-launch toggle (VCKP-13)** surfaces capability tier A/B/C here.

---

### `src/components/modal/AdoptAgentModal.tsx` (NEW) — VCKP-12 [D-10]

**Analog:** `src/components/modal/AgentLaunchModal.tsx` (modal scaffold only)

Copy the modal shell (backdrop/focus/Esc/⌘↵, `:158-188`). Sections per D-10: "Add it to / As the task / Limits / From now on, Voss will"; CTA "Hand to Voss". **Copy rule (constraint):** NO `cage`/`Voss-native`/`PermissionGate`/`session-tree`/`partial lineage`/`pane` in UI strings. Role/risk pre-inferred + editable (D-12). Where no harness adopt write-path exists, render disabled-with-reason — mirror `decisionActions.ts:1-11` honesty. Adopt is always tier C (no per-tool-gate promise, D-11).

---

### `src-tauri/src/lib.rs` `spawn_managed_agent` (NEW Tauri command) — VCKP-13

**Analog:** `src-tauri/src/lib.rs:183-220` (`spawn_agent`)

**Clone `spawn_agent` verbatim** and insert the sandbox wrap before `spawn_command_session_with_env`. The existing body to copy (`:196-219`): `ensure_registry` → `env_for_embedded_cli` → `spawn_command_session_with_env(&cli_binary, &cli_args, &env, ...)` → `registry.insert` → `start_reader` → `register_agent`. The managed variant wraps `cli_binary`/`cli_args` (see pty/mod.rs entry) and writes the tier into the registry.

---

### `crates/voss-app-core/src/pty/mod.rs` (sandbox wrap) — VCKP-13a

**Analog:** `pty/mod.rs:189-245` (`spawn_command_session_with_env`, `portable_pty::CommandBuilder`)

**The spawn site to wrap** (`pty/mod.rs:212-213`):
```rust
let mut cmd = CommandBuilder::new(cmd_binary);
cmd.args(cmd_args);
```
**Sandbox wrap (RESEARCH §VCKP-13a):** prepend the sandbox launcher so `cmd_binary` becomes `sandbox-exec` (macOS) / `bwrap` (Linux) and the real CLI moves into args:
```rust
// macOS: sandbox-exec -f <profile.sb> <cli> <args...>
// Linux: bwrap --ro-bind / / --bind <scope> <scope> <cli> <args...>
```
Generate `profile.sb` per-run from the scope chip (deny `file-write*`, allow `(subpath "<scope>")` + `/tmp`). **Security (V5):** canonicalize scope paths via the existing `is_safe_run_id` discipline (`lib.rs:1066`) before building the profile; start from `deny`, never `allow default`. **Budget-kill (VCKP-13c):** route `budget_update` PtyEvent (`pty-ipc.ts:16,122-130`) → `invoke('pty_kill')` (`pty-ipc.ts:201-205`) at the limit.

---

### `src/App.tsx` — `handleLaunchAgent` wire + Live/Review toggle — VCKP-03/08

**Analog:** the stub itself + the existing `display:none` swap

**Complete the stub** (`App.tsx:268-272`) — currently only splits a pane, never spawns:
```typescript
const handleLaunchAgent = (_config) => {
  setAgentModalOpen(false);
  gridController()?.splitFocused('H');
  // Agent spawn will be wired to the new pane in a future plan  ← V14 wires this
};
```
Wire it to `spawnAgent` (`pty-ipc.ts`), passing the minted `cardId` as `sessionId` (Bridge B).

**Live↔Review toggle (VCKP-08, Pitfall 3):** EXTEND the existing `orgViewOpen` + `display:none` swap — do NOT conditionally mount the grid (kills PTY panes). The grid stays mounted via `display: orgViewOpen() ? 'none' : 'flex'` (`App.tsx:1183`) while the cockpit renders behind `<Show when={orgViewOpen()}>` (`:1263`). The code comment at `:1262` documents this contract explicitly. ⌘⇧O toggle (`:1008-1010`) must not regress.

---

## Shared Patterns

### Module-level Solid signal as global store
**Source:** `src/org/orgStore.ts:11-15` · also `src/pane/budgetRegistry.ts:10`
**Apply to:** `selection.ts`, `bridge.ts` (cardToPane map), `attentionQueue.ts`
```typescript
export const [x, setX] = createSignal<T>(initial);  // module scope = global, read anywhere
```

### Immutable update, NO produce/structuredClone (Pitfall 5)
**Source:** `src/pane/budgetRegistry.ts:14-37`
**Apply to:** every map/tree mutation in `bridge.ts`, `attentionQueue.ts`, `adapters.ts`
```typescript
setMap((prev) => { if (/* unchanged */) return prev; return { ...prev, [k]: v }; });
```
Project memory footgun: `produce` drafts are Proxies → `DATA_CLONE_ERR`. Hand-spread only.

### Pure, fixture-testable module (no Solid imports)
**Source:** `src/org/boardDerive.ts:1-3` (header comment) — keeps logic unit-testable
**Apply to:** `adapters.ts`, `bridge.ts` (`resolveCard`), `swarmReconcile.ts`

### D-02 snapshot contract — keep green, never extend in place
**Source:** `src/org/guards.ts:26-43` (`assertRunData`)
**Apply to:** ALL VCKP-01 work — overlay lives in the new normalized model, never in `RunData`. Pitfall 2.

### Disabled-with-reason, never a silent no-op
**Source:** `src/org/decisionActions.ts:1-11` (documents why reject/unblock are disabled)
**Apply to:** RunCommandBar Auto-block (VCKP-03), feedback write-path (VCKP-09), adopt where no harness path (VCKP-12)

### Modal scaffold (backdrop / focus / Esc / ⌘↵)
**Source:** `src/components/modal/AgentLaunchModal.tsx:94-97,158-188`
**Apply to:** `AdoptAgentModal.tsx`, the refactored `AgentLaunchModal.tsx`

### A12 token-only styling (VCKP-10 constraint)
**Source:** `src/org/panels/BoardPanel.tsx:16-48,76` — `var(--accent-red/amber/green)`, `var(--font-mono)`, `var(--role-*)`, `var(--focus)`, `var(--bg-*)`
**Apply to:** all new cockpit components. Token grep gate asserts no new `--xxx` vs `themes/bundled/voss-ignite.json`.

### Tauri invoke wrapper (data + PTY commands)
**Source:** `src/org/orgStore.ts:34` (`invoke<RunData>('load_run', ...)`) · `src/pane/pty-ipc.ts:174` (`invoke<string>('spawn_agent', ...)`)
**Apply to:** `spawn_managed_agent` invoke, `get_active_agents` fetch in adapters

---

## No Analog Found

None. Every V14 file has a close in-repo analog — this is a recomposition phase. The three "new" surfaces (RunCommandBar, AttentionQueue, AdoptAgentModal) have strong role-match analogs (config-builder, signal-aggregator, modal-scaffold respectively).

**Partial-analog risk (verify at build, not blockers):**

| File | Role | Data Flow | Reason / Residual |
|------|------|-----------|-------------------|
| `src/org/live/sseClient.ts` | service | streaming | First SSE consumer in the org view; consumer analog is solid (`sse.ts`), but the `{port,token}` handshake source in-webview is unresolved (Pitfall 4) — mock in V14. |
| `crates/.../pty/mod.rs` sandbox wrap | utility | file-I/O | `sandbox-exec`/`bwrap` argv pattern is cited from docs, not yet exercised in this repo (MEDIUM confidence per RESEARCH). Spawn-site analog is exact; the wrapper argv is the new part. |

## Metadata

**Analog search scope:** `apps/voss-app/src/org/{,model,panels}`, `apps/voss-app/src/pane/`, `apps/voss-app/src/components/{modal,sidebar,StatusBar}`, `apps/voss-app/src-tauri/src/lib.rs`, `crates/voss-app-core/src/{agent_registry,pty}.rs`, `sdk/typescript/src/client/sse.ts`
**Files scanned:** 14 read in full/targeted + grep across App.tsx, lib.rs, agent_registry.rs
**Pattern extraction date:** 2026-06-08
