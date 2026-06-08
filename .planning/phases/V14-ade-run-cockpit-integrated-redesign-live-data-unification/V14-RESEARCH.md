# Phase V14: ADE Run Cockpit (Integrated Redesign + Live Data Unification) — Research

**Researched:** 2026-06-08
**Domain:** SolidJS desktop UI recomposition · two-plane data unification · Tauri/Rust PTY + SQLite registry · SSE client wiring · OS sandboxing (Seatbelt/Landlock) · CLI permission proxies
**Confidence:** HIGH for the in-repo facts (keystone, data planes, panel reuse, SSE client status); MEDIUM for external enforcement (sandbox-exec / Claude hooks / OpenCode config — cited from official docs, not yet exercised in this repo)

> This is an integrated-redesign phase over an already-built surface (V11). The research focus is **what exists vs. what must be built** and the **keystone id-bridge**, not greenfield library selection. No new external runtime packages are introduced for the core path (VCKP-01..10), so the Package Legitimacy Audit is minimal; VCKP-13 enforcement uses OS-native tooling (no package install).

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Cockpit-only. The `OrgViewShell` `ORG_TABS`/`activeTab` tab switcher (`org/OrgViewShell.tsx:45,68`) is **removed**. The cockpit (Board spine + Card detail drawer + Timeline/replay rail + bottom gate bar) is the single Run Review surface.
- **D-02:** The 10 existing panel components (`org/panels/*.tsx`) are reused as drawer/rail sections, NOT as tabs. Replay and Audit become drawer/rail sections. No legacy tab "escape hatch" kept.
- **D-03:** RunCommandBar is an **always-on top strip** above the work surface, present in BOTH Live Work and Run Review modes (Warp universal-input style). Not ⌘K-invoked.
- **D-04:** The existing `AgentSidebar` Quick-Launch flow **coexists** as the fast per-CLI spawn path; RunCommandBar is the richer run-intake path. Do not remove Quick-Launch.
- **D-05:** AttentionQueue surface = **StatusBar count pill + dockable queue panel** (reuses StatusBar agent-pill pattern; clicking opens the dockable panel). Non-modal by default.
- **D-06:** Blocking items (permission request, sign-off available) **pulse the pill**; they do not hard-modal the cockpit. Per-pane permission prompts in the live grid are unchanged.
- **D-07:** Clicking a board card bound to a LIVE pane **stays in the cockpit**: detail drawer shows an embedded **read-only live-pane peek** plus an explicit **"Open in grid"** button that flips `orgViewOpen` (`App.tsx:240`). Jump-to-grid is opt-in, never automatic.
- **D-08:** The detail drawer is **persistent** with a defined **no-selection empty state**. Selection is the single global `selectedCard` store driving Board highlight + drawer + timeline + gate bar together.
- **D-09 (VCKP-11):** Quick-launch modal — sparse/premium. CLI preset cards each show the user's **default model**; one optional "what should it work on?" prompt; working dir + pane placement (Right/Below/New tab). **Removed: raw-command field + "terminal agent" explainer block.**
- **D-10 (VCKP-12):** "Manage with Voss" adopt flow — plain language. Title "Let Voss manage this agent"; sections "Add it to / As the task / Limits / From now on, Voss will". CTA "Hand to Voss". **No** `cage`/`Voss-native`/`PermissionGate`/`session-tree`/`partial lineage`/`pane` in UI copy.
- **D-11:** Adoption is forward-only + best-effort. Keep the running work; audit node marked `partial_lineage`; pre-adoption activity excluded. **Engineering limit locked:** external CLI agent is PTY-only — Voss cannot intercept its internal tool loop, so adoption gives cost-tracking + transcript-audit + budget-monitor + review-before-done + **advisory** scope, NOT per-tool PermissionGate.
- **D-12:** Role/Risk on adopt pre-inferred (risk from scope/budget, role from CLI) but **editable** — visible by default.
- **D-13 (VCKP-13):** Mitigate external-CLI gating at the launch boundary. "Managed launch" spawns under enforcement from t0: (a) OS scope-sandbox (sandbox-exec / Landlock-bubblewrap / writable-scope bind-mount) — CLI-agnostic floor; (b) permission proxy for hook-capable CLIs → approvals into AttentionQueue — per-CLI best-effort; (c) budget-kill — universal. UI shows capability tier A/B/C. Adopt of a running agent is always tier C.

### Claude's Discretion

- id-bridge correlation mechanism (card id → live `paneId`/`sessionNodeId`). **This is the keystone risk — resolve before the binding wave.** (See **Keystone** section — researcher has resolved the concrete mechanism below.)
- Adapter shapes (`snapshot→model`, `registry→model overlay`) and selection-store implementation (Solid signals vs store) — planner's call, consistent with `org/orgStore.ts` signal style.
- Exact cockpit CSS/region sizing + collapse behavior — within A12 Ignite tokens.
- Roster IA (Voss-native team + A13 swarm + external terminal agents grouping) — default sectioned single roster.
- Gate bar exact field set + card-vs-run reactivity — planner's call within VCKP-05.

### Deferred Ideas (OUT OF SCOPE)

- Freeform/Studio investigation canvas.
- Embedded browser / VerificationArtifact panel (needs webview infra).
- Replay rollback / re-run (replay stays inspect-only).
- Reject/Unblock full write actions (blocked on harness write path; VCKP-09 best-effort only).
- Custom board columns (columns stay the orchestrator state machine).
- Retroactive audit/budget of pre-adoption activity (forward-only; `partial_lineage`).
- Per-tool PermissionGate on adopted/already-running external CLI agents (tier C — impossible from PTY).
- New harness contracts / new SSE event types / new emit points (V14 is a PROTOCOL v1 client).
- Real `voss serve` end-to-end live verification (fixture/mock-verified here; real-server rides V13.1).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VCKP-01 | Normalized UI data model + adapters + single selection store | Snapshot plane (`orgStore.ts` `runData()` signal, `RunData` in `types.ts:202`) and live plane (`AgentEntry` from `get_active_agents`, `budgetByPaneId` signal) both exist as Solid signals. Adapter is a pure function merging them; selection store mirrors `createSignal` pattern already in `orgStore.ts`. **No `Agent` type in `types.ts` today — must be added.** See Architecture Patterns §1–2. |
| VCKP-02 | Card ↔ session/pane binding via shared id map | **KEYSTONE RESOLVED.** No shared key exists today (registry `session_id` is app-minted, unrelated to `SessionTreeNode.id`). Two-tier resolution: native runs bind via harness `sessionID` (`uuid4().hex[:12]`, returned by `POST /session`); terminal-agent runs require minting a correlation id at launch. See **Keystone** section. |
| VCKP-03 | RunCommandBar intake (terminal + Voss-native start) | Terminal start path exists (`spawn_agent` Tauri cmd → `spawnAgent` in `pty-ipc.ts:167`). Native start path exists in V13.1 TS SDK (`createVossClient().createSession` — see SDK status). `handleLaunchAgent` (`App.tsx:268`) is currently a stub that only splits a pane — wiring must be completed. |
| VCKP-04 | AttentionQueue from snapshot decisions + live events | Sources: snapshot (Blocked column from `boardDerive.deriveColumn`, sign-off from `RunFinal.sign_off`, `unsupported_claims` in `AuditReport`) + live SSE (`permission.updated`, `gate.updated`, `budget.updated`, `confidence.updated`, `session.idle` — all in PROTOCOL §6). StatusBar pill pattern exists (`App.tsx:1271` `agentCount`/`totalCost` props). |
| VCKP-05 | Integrated cockpit layout recomposing 10 panels | Panels already accept `data` + `onCardSelect`/`selectedCardId` props (`BoardPanel.tsx:140`, `DiffPanel`, `OrgViewShell.tsx:215-241`) — recompose-friendly. Replace the tab shell, hoist selection to a global store. |
| VCKP-06 | Live SSE wiring via V13.1 (best-effort) | V13.1 TS SSE client SHIPPED: `sdk/typescript/src/client/sse.ts` `subscribeToEvents()` (async-generator, EventSource-style fetch). **Webview constraint:** the launcher uses `node:child_process` (Node-only) — cannot start `voss serve` from the Tauri webview; only the SSE *consumer* is browser-safe. See Pitfall 4. |
| VCKP-07 | Swarm reconciliation (best-effort) | `.voss/swarm/{manifest.json,tasks/,results/}` file protocol exists; Rust `write_swarm_files`/`watch_swarm_results` (`lib.rs:602,634`) + `voss://swarm-result-added` event. Manifest→roster/board is a pure adapter. |
| VCKP-08 | Live↔Review mode toggle preserving grid | Existing `orgViewOpen` signal + `display:none` swap (`App.tsx:1183,1263`) keeps PTY panes mounted. Extend, don't replace. |
| VCKP-09 | Feedback write-path (best-effort, harness-gated) | One write path only (`decisionActions.ts` `voss audit <id> --approve`). No per-card follow-up write path exists in the harness today → render disabled-with-reason. PROTOCOL §5 `POST /session/:id/message` exists for *native* sessions only. |
| VCKP-10 | Dense/keyboard/a11y pass on A12 tokens | A12 token set in `themes/bundled/voss-ignite.json` (see token list). Existing panels already use `var(--...)` tokens + monospace numerics (`BoardPanel.tsx:76`). Grep gate against new tokens is straightforward. |
| VCKP-11 | Sparse quick-launch modal | `AgentLaunchModal.tsx` exists but is config-heavy (CLI tabs + effort levels + likely raw-command). Refactor to preset cards. CLI presets already enumerated (`AgentLaunchModal.tsx:6-14`). |
| VCKP-12 | "Manage with Voss" adopt flow | Live plane tracks cost (`budgetByPaneId`), status, paneId. Adopt = mint a card, bind to paneId, apply advisory budget/scope, start a `partial_lineage` transcript-audit node. **No harness adopt path exists** → where the harness write path is absent, render disabled-with-reason. |
| VCKP-13 | Managed launch + enforcement tiers | PTY spawn site is `spawn_command_session_with_env` (`pty/mod.rs:189`, `portable_pty::CommandBuilder`). Sandbox = wrap `cmd_binary`/`cmd_args` with `sandbox-exec -f profile.sb` (macOS) / `bwrap` (Linux). Permission proxy = Claude Code `PreToolUse` hook / OpenCode `permission` config. See Security Domain. |
</phase_requirements>

## Summary

V14 is a recomposition + unification phase over a fully-built surface. The 10 V11 panel components (`org/panels/*.tsx`) are already prop-driven (`data` + `onCardSelect`/`selectedCardId`) and require no internal rewrite — the work is replacing the tab shell with a four-region cockpit driven by one hoisted `selectedCard` signal, plus three genuinely new surfaces (RunCommandBar, AttentionQueue, the adopt/managed-launch flows). The two data planes both already exist as Solid signals (snapshot: `runData()`; live: `get_active_agents` + `budgetByPaneId`), so VCKP-01 is a pure adapter layer, not new infrastructure.

**The keystone (VCKP-02) is resolved and is the single highest-risk item.** Today there is **no shared key** correlating a live PTY pane/registry agent to a snapshot `SessionTreeNode`/board card. The registry's `session_id` column (`agent_registry.rs:28`) is **passed in from the frontend** at spawn (`pty-ipc.ts:181`) and is the app's own pane/session identifier — it is **not** the harness `SessionTreeNode.id` (which is the filename stem of `.voss/sessions/<run>/*.json`, surfaced by `load_run` at `lib.rs:1112`). For **Voss-native** runs the bridge is achievable cleanly: the harness mints `sessionID = uuid4().hex[:12]` server-side and returns it from `POST /session` (PROTOCOL §10/§11), and every SSE event carries that `sessionID` — so the cockpit binds card→session by storing the create-response id. For **terminal-agent** runs there is no harness session at all; the only viable bridge is to mint a correlation id at launch (RunCommandBar/Quick-launch stamps a `cardId`, the app stores `cardId ↔ paneId` client-side). These are two distinct mechanisms and the plan must treat them separately.

**Primary recommendation:** Build VCKP-01 (adapter + selection store) and the VCKP-02 id-bridge as a pure-TS data layer first, with both bridge mechanisms (native `sessionID` echo, terminal `cardId↔paneId` client map) defined against fixtures before any layout work. Reuse all 10 panels verbatim as drawer/rail sections. Consume the already-shipped V13.1 TS SSE client (`subscribeToEvents`) behind a feature-detect with snapshot fallback. For VCKP-13, wrap the existing `portable_pty` spawn site with `sandbox-exec`/`bwrap` (CLI-agnostic floor) and layer Claude-hook / OpenCode-config permission proxies as per-CLI best-effort; render the correct A/B/C tier honestly.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Normalized model + adapters (VCKP-01) | Frontend (SolidJS, pure TS) | — | Pure view-layer merge of two existing signals; no Rust/IPC change. |
| Selection store (VCKP-01) | Frontend (Solid signal) | — | Mirrors `orgStore.ts` `createSignal` global-signal pattern. |
| Card↔session bridge — native (VCKP-02) | Frontend (store id from create-response) | Harness (mints `sessionID`) | Harness owns id generation; app records the mapping. |
| Card↔session bridge — terminal (VCKP-02) | Frontend (client `cardId↔paneId` map) | Rust registry (stores app `session_id`/`pane_id`) | No harness session exists; app must mint + persist correlation. |
| RunCommandBar terminal start (VCKP-03) | Rust (`spawn_agent` PTY) | Frontend (`spawnAgent` IPC) | PTY lifecycle is Rust-owned. |
| RunCommandBar native start (VCKP-03) | Backend (`voss serve` REST) | Frontend (V13.1 SDK client) | Session create is a harness REST endpoint. |
| AttentionQueue (VCKP-04) | Frontend (aggregator signal) | Backend (SSE events) | Aggregates snapshot decisions + live events into one queue. |
| Cockpit layout (VCKP-05) | Frontend (component composition) | — | Pure recomposition of existing panels. |
| Live SSE consume (VCKP-06) | Frontend (V13.1 SSE client in webview) | Backend (`voss serve`) | Consumer is browser-safe `fetch`; server start is NOT (Node-only launcher). |
| Swarm reconcile (VCKP-07) | Frontend (manifest adapter) | Rust (`write_swarm_files`/`watch_swarm_results`) | File protocol already Rust-backed; UI maps it. |
| Live↔Review toggle (VCKP-08) | Frontend (`orgViewOpen` + `display:none`) | — | Extends existing CSS-swap pattern; PTY stays mounted. |
| OS sandbox (VCKP-13a) | Rust (PTY spawn wrap) | OS kernel (Seatbelt/Landlock) | Enforcement happens at the kernel; Rust chooses the wrapper argv. |
| Permission proxy (VCKP-13b) | Rust/External (CLI hook config) | Frontend (AttentionQueue surface) | CLI's own hook writes a file/calls back; app reads + surfaces. |
| Budget-kill (VCKP-13c) | Frontend (cost meter) → Rust (`pty_kill`) | — | Cost arrives via `budget_update` PtyEvent; kill is `pty_kill`. |

---

## Keystone — The id Bridge (VCKP-01 / VCKP-02) [HIGHEST RISK, RESOLVED]

> The make-or-break dependency. Resolved concretely below with file:line citations.

### Current state: NO shared key exists [VERIFIED: codebase]

Two id namespaces, never correlated:

1. **Snapshot plane — `SessionTreeNode.id`** is the **filename stem** of a node JSON file under `<cwd>/.voss/sessions/<run_id>/<node>.json`. `load_run` reads these files directly (`lib.rs:1112-1119`) and the board derives one card per non-root node, using `node.id` as the card id (`boardDerive.ts:48`). This id is **written by the harness**, never by the app.

2. **Live plane — registry `session_id`** is a column in `agent_sessions` (`agent_registry.rs:28`, schema `:84-100`) whose value is **passed in from the frontend** at spawn: `spawnAgent({... sessionId ...})` → `invoke('spawn_agent', { sessionId, paneId })` (`pty-ipc.ts:174-184`) → `register_agent(conn, &pane_id, &session_id, ...)` (`lib.rs:216`). The PRIMARY KEY is `pane_id`; `session_id` is just whatever string the app handed it.

**Conclusion:** `registry.session_id ≠ SessionTreeNode.id`. There is no field today that joins a live pane to a board card. `org/types.ts` has no `Agent` type and `CardSnapshot` (`types.ts:212`) has no `paneId`/`sessionNodeId`. This matches the SPEC keystone warning exactly.

### Resolution — two distinct bridges

**Bridge A — Voss-native runs (achievable cleanly, harness-blessed):**
- The harness mints `sessionID = uuid4().hex[:12]` **server-side** at `POST /session` and returns `{id}` (PROTOCOL §10 line 152, §11 line 159). [CITED: PROTOCOL.md §10/§11]
- Every Voss-native SSE event carries `sessionID` (`budget.updated`/`confidence.updated`/`gate.updated`/`session.idle` — PROTOCOL §6 lines 114-118). [CITED: PROTOCOL.md §6]
- **Mechanism:** when RunCommandBar starts a native run via the V13.1 SDK `createSession`, store the returned `id` as the card's `sessionNodeId`. The id flows: create-response → card → SSE event match (by `sessionID`). The `.voss/sessions/<id>.json` persisted record (PROTOCOL §10) later becomes the snapshot node, so the **same id** appears in both planes for native runs. **This is the join key.**

**Bridge B — terminal-agent runs (must mint a client-side correlation id):**
- A terminal agent (Claude/Codex/etc.) has **no harness session** — it never calls `POST /session`. Its PTY is tracked only by app `pane_id`.
- **Mechanism:** when the cockpit creates/binds a card to a terminal agent (at launch via RunCommandBar, or at adopt via VCKP-12), mint a `cardId` client-side (`crypto.randomUUID()` is available in the webview) and store a **client-side `cardId ↔ paneId` map** (a Solid signal in the selection/bridge store). The existing `session_id` arg to `spawn_agent` can carry this `cardId` so it survives a registry round-trip and orphan sweep — i.e. **pass `cardId` as `sessionId`** when spawning a cockpit-bound terminal agent (no Rust change needed; the column already exists). `resolveCard(cardId)` then returns `{ paneId }` from the client map (and `{ sessionNodeId }` is absent — terminal agents have no recorded session node).

**`resolveCard(id) → { paneId?, sessionNodeId? }` contract:**
- Native run card: `{ sessionNodeId: <harness id>, paneId: <if also shown live> }`.
- Terminal agent card: `{ paneId: <from cardId↔paneId map> }`, no `sessionNodeId`.
- Snapshot-only card (historical, no live pane): `{ sessionNodeId: <node.id> }`, no `paneId` → click falls back to detail-open (acceptance criterion).

### What must be BUILT for the keystone
1. Add `Agent`, and extend `Card`, with `paneId?`/`sessionNodeId?` in the normalized model (extends `types.ts`, do not edit the D-02-guarded `RunData`).
2. A bridge store: `cardId ↔ paneId` client map (Solid signal) + a `cardId → sessionNodeId` map populated from native create-responses.
3. `resolveCard` + `resolvePane` (reverse) pure functions, fixture-tested per acceptance.
4. Convention: cockpit-launched terminal agents pass their `cardId` as the `spawn_agent` `sessionId` arg (zero Rust change).

### What must NOT be done
- Do **not** edit `RunData`/`guards.ts` to add live fields — that regresses the D-02 snapshot contract (constraint). Live overlay lives in the normalized model layered *on top* of the snapshot.
- Do **not** assume the registry `session_id` already equals a node id — it does not.

---

## Standard Stack

**No new external runtime packages are required for VCKP-01..12 core.** The phase is built on the existing in-repo stack. VCKP-13 enforcement uses OS-native tooling (no install).

### Core (already in repo — verified present)
| Library / Module | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `solid-js` | (repo-pinned) | Reactive signals/stores for selection + adapters | Already the app's UI runtime; `createSignal` global-signal pattern established in `orgStore.ts`. |
| `@tauri-apps/api` | (repo-pinned) | `invoke()` IPC for PTY + data commands | Existing data path (`spawn_agent`, `load_run`, `get_active_agents`). |
| `vitest` | 4.1.6 | Test runner (`vitest run`) | `apps/voss-app/package.json:10`, `vitest.config.ts` present. [VERIFIED: package.json] |
| V13.1 TS SDK (`sdk/typescript`) | in-repo, shipped | REST `createVossClient` + SSE `subscribeToEvents` + permission `replyPermission` | The native-run start + live SSE consumer. SHIPPED per STATE.md V13.1 plan 03. [VERIFIED: STATE.md, sdk/typescript/src/] |
| `portable_pty` | (repo-pinned) | PTY spawn via `CommandBuilder` (`pty/mod.rs:18`) | The spawn site VCKP-13 wraps. |
| `rusqlite` | (repo-pinned) | Agent registry SQLite (`agent_registry.rs`) | Existing live-plane store. |

### Supporting (V13.1 SDK transitive — already vendored)
| Library | Purpose | When to Use |
|---------|---------|-------------|
| `eventsource-parser` | SSE frame parsing in `subscribeToEvents` (`sse.ts:1`) | Live wiring (VCKP-06) — already imported by the SDK; consume the SDK, don't re-import. |
| `openapi-fetch` | Typed REST client base (V13.1 plan 03) | Native-run start; consume via `createVossClient`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reusing `subscribeToEvents` (V13.1) | Raw `EventSource` in the webview | `EventSource` cannot set `Authorization` headers; the SDK's `fetch`+`eventsource-parser` stream does. Use the SDK. [CITED: sse.ts uses Bearer header] |
| Solid global signals for selection | Solid `createStore` | Signals match the existing `orgStore.ts` style and the SPEC discretion note. Stores risk the `produce`/`structuredClone` proxy footgun noted in project memory (voss-app Solid produce). Prefer signals + hand-built immutable updates (as `budgetRegistry.ts` already does). |
| `sandbox-exec` (macOS) | Container/VM | sandbox-exec is the lightest CLI-agnostic floor and matches Codex/Gemini CLI's own approach; containers are out of scope. |

**Installation:** None for core. (V13.1 SDK is in-repo; OS sandbox tools ship with macOS/Linux.)

**Version verification:**
```bash
# vitest confirmed in apps/voss-app/package.json (4.1.6)
# V13.1 SDK confirmed present at sdk/typescript/src/ (rest.ts, sse.ts, permission.ts)
```

## Package Legitimacy Audit

> No new external packages are installed by the V14 core path. All runtime deps are already in `package.json`/`Cargo.toml` from prior phases. slopcheck not run because no install occurs.

| Package | Registry | Disposition |
|---------|----------|-------------|
| (none — V14 introduces no new runtime dependency) | — | N/A |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*If the planner discovers a need for a new package (e.g. a focus-trap a11y helper for VCKP-10), it must run the Package Legitimacy Gate before adding it and gate the install behind a `checkpoint:human-verify` task.*

---

## Architecture Patterns

### System Architecture Diagram

```
                         ┌──────────────────────────────────────────────┐
   user goal ──────────► │  RunCommandBar (NEW, always-on)  D-03         │
                         │  goal · mode · team · scope · budget · NV/TA  │
                         └───────────┬──────────────────────┬───────────┘
                       Voss-native   │                      │  terminal-agent
                  (V13.1 createSession)                     │ (spawn_agent PTY)
                                     ▼                      ▼
                       ┌─────────────────────┐   ┌────────────────────────┐
                       │ harness sessionID    │   │ app cardId (minted)    │
                       │ uuid4().hex[:12]     │   │ passed as session_id   │
                       └──────────┬──────────┘   └───────────┬────────────┘
                                  │                           │
        ┌─────────────────────────┴───────────────────────────┴──────────┐
        │              ID-BRIDGE STORE  (NEW, VCKP-02)                     │
        │   cardId ↔ sessionNodeId (native)  ·  cardId ↔ paneId (terminal)│
        └────────────┬───────────────────────────────────┬───────────────┘
                     │                                     │
   snapshot plane ───┤                                     ├─── live plane
   load_run() ──────►│   NORMALIZED MODEL ADAPTER (NEW, VCKP-01)          │
   runData() signal  │   snapshot→model  +  registry/budget→overlay       │◄── get_active_agents()
                     └────────────────────┬──────────────────────────────┘    budgetByPaneId() signal
                                          │                                    SSE subscribeToEvents() (VCKP-06)
                          selectedCard / selectedRun (NEW global signal, D-08)
                                          │
        ┌──────────────┬──────────────────┼───────────────────┬──────────────┐
        ▼              ▼                   ▼                    ▼              ▼
   Board spine    Detail drawer     Timeline/replay rail   Gate bar     AttentionQueue (NEW, VCKP-04)
   (BoardPanel)   (Audit/Verdict/   (SessionTree+Replay)   (Budget/     StatusBar pill (D-05)
                   Diff/Scope/                              Scope/        ← snapshot decisions
                   Budget/Blocked)                          unsupported)  + live SSE events
```

### Recommended Project Structure (additive — extends `src/org/`)
```
src/org/
├── model/
│   ├── normalized.ts      # NEW: { Run, Card, Agent, SessionNode, Evidence, Decision } extending types.ts
│   ├── adapters.ts        # NEW: snapshotToModel() + registryOverlay()
│   └── bridge.ts          # NEW: cardId↔paneId / cardId↔sessionNodeId maps + resolveCard/resolvePane
├── selection.ts           # NEW: selectedRun/selectedCard global signals (mirrors orgStore.ts)
├── attention/
│   └── attentionQueue.ts  # NEW: aggregator signal (snapshot decisions + live events)
├── cockpit/
│   ├── CockpitShell.tsx   # NEW: replaces OrgViewShell tab shell (D-01) — 4 regions
│   ├── RunCommandBar.tsx  # NEW (VCKP-03)
│   ├── CardDrawer.tsx     # NEW: composes existing Audit/Verdict/Diff/Scope/Budget/Blocked bodies
│   └── GateBar.tsx        # NEW (VCKP-05)
├── panels/*.tsx           # REUSED verbatim (D-02) — already prop-driven
├── live/
│   └── sseClient.ts       # NEW (VCKP-06): wraps V13.1 subscribeToEvents + feature-detect
└── ... (existing orgStore.ts, boardDerive.ts, guards.ts unchanged)
src/components/modal/
├── AgentLaunchModal.tsx   # REFACTOR (VCKP-11): preset cards, drop raw-command/explainer
└── AdoptAgentModal.tsx    # NEW (VCKP-12): "Let Voss manage this agent"
src-tauri/src/lib.rs       # EXTEND (VCKP-13): managed-launch spawn wrapper
```

### Pattern 1: Pure adapter merging two existing signals (VCKP-01)
**What:** A pure function that takes the snapshot (`RunData`) as the spine and overlays live registry/budget fields by the bridge.
**When to use:** VCKP-01 core; keep it pure (no Solid imports) so it's fixture-testable like `boardDerive.ts`.
```typescript
// Source: pattern mirrors boardDerive.ts (pure, no Solid imports) + budgetRegistry.ts immutability
// src/org/model/adapters.ts
export function buildModel(
  snapshot: RunData | null,
  liveAgents: AgentEntry[],         // from get_active_agents
  budgets: Record<string, BudgetEntry>, // from budgetByPaneId()
  bridge: BridgeMaps,
): Run {
  const cards = cardsFromRunData(snapshot).map((c) => ({
    ...c,
    paneId: bridge.paneIdForCard(c.id),
    sessionNodeId: c.id,                       // snapshot card id IS the node id
    liveBudget: budgets[bridge.paneIdForCard(c.id) ?? '']?.cost_usd,
    liveStatus: /* derive from budget freshness / registry status */,
  }));
  return { /* Run fields */, cards };
}
```

### Pattern 2: Hoisted selection signal driving N surfaces (VCKP-01/05)
**What:** Move `selectedCardId` out of `OrgViewShell` (where it's local, `OrgViewShell.tsx:70`) into a module-level signal so Board + drawer + timeline + gate bar all read it.
```typescript
// Source: mirrors orgStore.ts module-level createSignal pattern
// src/org/selection.ts
import { createSignal } from 'solid-js';
export const [selectedCardId, setSelectedCardId] = createSignal<string | null>(null);
export const [selectedRunId, setSelectedRunId] = createSignal<string | null>(null);
```

### Pattern 3: SSE consume with snapshot fallback + live label (VCKP-06)
**What:** Feature-detect a live server; consume `subscribeToEvents`; fall back to snapshot.
```typescript
// Source: sdk/typescript/src/client/sse.ts subscribeToEvents (SHIPPED)
import { subscribeToEvents } from 'voss-sdk'; // or relative path to sdk/typescript
const ac = new AbortController();
(async () => {
  for await (const ev of subscribeToEvents(baseUrl, sessionId, token, ac.signal)) {
    // route by ev type into attentionQueue + overlay updates, matched by ev.sessionID
  }
})();
// label = live when a stream is active for the selected run, else snapshot
```

### Anti-Patterns to Avoid
- **Editing `RunData`/`guards.ts` to carry live fields:** regresses D-02. Overlay lives in the normalized model.
- **Using `EventSource` directly:** can't set the `Authorization: Bearer` header the harness requires. Use the SDK stream.
- **Starting `voss serve` from the webview:** the V13.1 launcher uses `node:child_process` (Node-only). The webview can only *consume* SSE, not spawn the server (see Pitfall 4).
- **`produce`/`structuredClone` on tree-shaped model state from render code:** Solid `produce` drafts are Proxies → `DATA_CLONE_ERR` (project memory: voss-app Solid produce). Build immutable updates by hand, as `budgetRegistry.ts` does.
- **Promising per-tool gating on adopted external agents:** PTY-only; impossible (D-11). Copy + tier must say tier C.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE framing/parsing | Custom byte/line SSE parser | V13.1 `subscribeToEvents` (`sse.ts`) | Already handles `eventsource-parser`, abort, Bearer auth, error detail. |
| Native session create + permission reply | Hand-rolled fetch | V13.1 `createVossClient` + `replyPermission` | Typed against the OpenAPI snapshot; maps non-2xx to `VossApiError`. |
| Snapshot contract validation | New guard | Existing `assertRunData` (`guards.ts`) | D-02 boundary — keep green, don't duplicate. |
| Board column derivation | New column logic | `boardDerive.ts` `deriveColumn`/`deriveRisk` | Mirrors the verified harness algorithm exactly; reuse. |
| OS filesystem blast-radius control | App-level path checks | `sandbox-exec` (macOS Seatbelt) / `bwrap`/Landlock (Linux) | Kernel-enforced; survives any tool the CLI invokes. App-level checks can't see an external CLI's tool loop. |
| Per-CLI permission interception | Wrapping the PTY stream | Claude Code `PreToolUse` hook / OpenCode `permission` config | The CLI exposes a real decision hook; PTY scraping is fragile and can't gate. |
| Cost tracking for agents | New meter | `budgetByPaneId` signal (`budgetRegistry.ts`) fed by `budget_update` PtyEvent | Already wired from the PTY reader. |

**Key insight:** Almost everything V14 needs already exists in some plane — the value is *correlating and recomposing*, not rebuilding. The only genuinely new infrastructure is the id-bridge store, the AttentionQueue aggregator, and the VCKP-13 spawn wrappers.

## Runtime State Inventory

> V14 is primarily additive UI + a data-correlation layer, not a rename/migration. But it introduces a new id-correlation convention and touches the registry's `session_id` semantics — inventory below.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `agent_sessions` SQLite table (`.voss/agent-registry.sqlite`) — `session_id` column currently holds an app-minted value. V14 proposes overloading it to carry a cockpit `cardId` for cockpit-bound terminal agents. | **Code edit only** (no schema change — column exists). Existing rows remain valid; new cockpit-launched agents write `cardId` there. No data migration needed. |
| Live service config | None — V14 starts no new external services. `voss serve` (for VCKP-06) is gated on V13.1 and not started by the webview. | None. |
| OS-registered state | VCKP-13 managed launch will spawn CLIs under `sandbox-exec`/`bwrap`. No persistent OS registration (transient per-process wrapper). | None persistent; verify wrapper argv at spawn. |
| Secrets/env vars | V13.1 handshake token (`{v,port,token}`) for native SSE — held in memory, not persisted by V14. | None. |
| Build artifacts | None new. | None. |

**Nothing found in category:** Live service config / OS-registered (persistent) / Secrets / Build artifacts — verified by reading `lib.rs`, `agent_registry.rs`, and the V13.1 launcher.

## Common Pitfalls

### Pitfall 1: Assuming the registry `session_id` already joins to a board card
**What goes wrong:** Planner writes `resolveCard` joining `agent_sessions.session_id` to `SessionTreeNode.id` and it never matches.
**Why it happens:** Both are called "session id" but one is app-minted (`pty-ipc.ts:181`) and one is harness-minted (filename stem).
**How to avoid:** Use the two-bridge design (native `sessionID` echo vs terminal `cardId↔paneId` map). Fixture-test both before layout.
**Warning signs:** Empty `resolveCard` results for live terminal agents; "card not found" on click.

### Pitfall 2: Regressing the D-02 snapshot contract
**What goes wrong:** Adding `paneId`/live fields to `RunData` to "make merging easier" trips `assertRunData` or breaks V11 tests.
**Why it happens:** Tempting to extend the loaded type in place.
**How to avoid:** Keep `RunData`/`guards.ts` frozen; build the normalized model as a separate type that *wraps* the snapshot.
**Warning signs:** `org/__tests__/guards.test.ts` fails; V11 panel tests fail.

### Pitfall 3: Breaking the grid/PTY on the Live↔Review toggle
**What goes wrong:** Unmounting `GridRoot` on toggle kills live PTY panes.
**Why it happens:** Replacing the `display:none` swap with conditional mount.
**How to avoid:** Extend the existing `orgViewOpen` + `display:none` pattern (`App.tsx:1183,1263`) — grid stays mounted (the code comment at `:1261` calls this out explicitly).
**Warning signs:** Terminal scrollback lost after toggling back; existing grid tests fail.

### Pitfall 4: Trying to start `voss serve` from the webview (VCKP-06)
**What goes wrong:** Native-run start or live wiring fails because the webview can't `spawn` a process.
**Why it happens:** The V13.1 launcher (`sdk/typescript/src/launcher/launcher.ts`) imports `node:child_process` — Node-only, not available in the Tauri webview runtime.
**How to avoid:** The webview can **consume** SSE (`subscribeToEvents` is pure `fetch`) but must obtain the `{port, token}` handshake another way (e.g. a Tauri Rust command that launches `voss serve`, or a server the user already started). For V14, fixture/mock the stream (the SPEC defers real-server to V13.1) — the consumer path is what's tested. Real spawn is a Rust-side concern, not webview JS.
**Warning signs:** `node:child_process` import error in the bundle; `process is not defined` in the webview.

### Pitfall 5: Solid `produce`/`structuredClone` on the tree-shaped model
**What goes wrong:** `DATA_CLONE_ERR` when cloning a `produce` draft Proxy of `SessionNode`/`Card` tree state.
**Why it happens:** Documented project footgun (memory: voss-app Solid produce).
**How to avoid:** Hand-built immutable updates (spread), as `budgetRegistry.ts`/`agentPaneRegistry.ts` already do. No `produce` on model state called from render.
**Warning signs:** Runtime `DATA_CLONE_ERR` in dev.

### Pitfall 6: Adopt UI overstating control on external agents (VCKP-12)
**What goes wrong:** Copy implies per-tool approval ("ask before risky edits") for an adopted external CLI it can't actually gate.
**Why it happens:** Reusing Voss-native gate copy.
**How to avoid:** Tier C copy: budget-stop + transcript-audit + review-before-done + advisory scope only. No `cage`/`PermissionGate`/per-tool language (D-10/D-11 spawn-UX copy rule).
**Warning signs:** Copy mentions "tool" approval or "block" on an adopted agent.

## Code Examples

### Resolve a card to its live pane / session node (VCKP-02)
```typescript
// Source: derived from agent_registry.rs schema + PROTOCOL §10/§11 sessionID + boardDerive.ts
// src/org/model/bridge.ts
export interface BridgeMaps {
  cardToPane: Record<string, string>;       // terminal agents (client-minted)
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

### Managed-launch spawn wrapper (VCKP-13a — Rust)
```rust
// Source: spawn site pty/mod.rs:189 spawn_command_session_with_env (portable_pty CommandBuilder)
// Wrap the CLI binary with a sandbox profile so OUT-OF-SCOPE WRITES FAIL AT THE KERNEL.
// macOS: sandbox-exec -f <profile.sb> <cli> <args...>   (Seatbelt)  [CITED: sandbox-exec docs]
// Linux: bwrap --ro-bind / / --bind <scope> <scope> <cli> <args...> (bubblewrap/Landlock)
// The profile.sb is generated from the run's scope chip (writable subpath allowlist).
```
```scheme
; profile.sb (generated per-run from scope) — deny writes outside scope
; [CITED: 7402.org sandboxing-of-folder + michaelneale/agent-seatbelt-sandbox]
(version 1)
(allow default)
(deny file-write*)
(allow file-write* (subpath "/abs/path/to/scope"))   ; e.g. tests/**
(allow file-write* (subpath "/tmp"))
```

### Permission proxy for hook-capable CLIs (VCKP-13b)
```jsonc
// Claude Code: a PreToolUse hook routes the decision; deny > ask > allow.
// [CITED: code.claude.com/docs/en/hooks] — hookSpecificOutput.permissionDecision ∈ allow|deny|ask
// settings.json (written by Voss at managed launch, pointing the hook at a Voss callback)
{ "hooks": { "PreToolUse": [ { "matcher": "*", "hooks": [
  { "type": "command", "command": "<voss-permission-bridge>" } ] } ] } }
```
```jsonc
// OpenCode: permission config (allow|ask|deny, first match wins).
// [CITED: opencode.ai/docs/permissions] — opencode.json "permission" key
{ "$schema": "https://opencode.ai/config.json",
  "permission": { "edit": "ask", "bash": { "*": "ask", "git status": "allow" } } }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Org view = 10 tabs, one active (`OrgViewShell.tsx`) | One cockpit, one selection drives 4 regions | V14 (D-01/D-02) | Tab shell removed; panels reused as sections. |
| Snapshot-only, manual refresh (`orgStore.refreshRun`) | Live SSE overlay with snapshot fallback | V14 (VCKP-06, gated V13.1) | First SSE consumer in the org view. |
| Agent registry + snapshot are disjoint | Normalized model + id-bridge | V14 (VCKP-01/02) | Card↔pane↔session correlation. |
| External CLI agents run unsandboxed | Managed launch under Seatbelt/Landlock + permission proxy | V14 (VCKP-13) | Kernel-enforced scope floor + per-CLI gate. |

**Deprecated/outdated:**
- `OrgViewShell` `ORG_TABS`/`activeTab` (`:45,68`): removed by D-01. The component's data-load + run-picker logic (`:74-110`) should be lifted into the cockpit shell.
- Local `selectedCardId` in `OrgViewShell` (`:70`): hoisted to a global signal (VCKP-01).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The harness-persisted native session record (`.voss/sessions/<id>.json`, PROTOCOL §10) surfaces with the **same id** as `SessionTreeNode.id` in `load_run`, joining the native create-response id to the snapshot node id. | Keystone Bridge A | If the on-disk node id differs from the create-response `id`, native card↔snapshot binding needs a second lookup. Mitigate: fixture-test against a real native run before W2. (PROTOCOL §10 says id is the session id and the file is `<id>.json`, but `load_run` reads `<run_id>/<node>.json` per-node — the run vs node id relationship should be confirmed.) |
| A2 | Overloading `agent_sessions.session_id` to carry a cockpit `cardId` for cockpit-launched terminal agents has no adverse effect on existing registry consumers (`get_active_agents`, orphan sweep). | Runtime State Inventory | Low — `session_id` is not used as a join key today (only `pane_id` is the PK). Verify no consumer assumes a specific `session_id` format. |
| A3 | Claude Code `PreToolUse` hook and OpenCode `permission` config can be pointed at a Voss callback at managed-launch time via written config files. | Security Domain / VCKP-13b | Per-CLI best-effort by design (tier B fallback if proxy unavailable). Low phase risk — sandbox (tier A floor) still applies. Versions of these CLIs may change the hook schema; confirm at build. |
| A4 | The Tauri webview's `crypto.randomUUID()` is available for client-side `cardId` minting. | Keystone Bridge B | Very low — standard in all modern WebViews. |
| A5 | `voss serve` provides the `POST /session` create endpoint returning `{id}` as PROTOCOL §11 describes, and the V13.1 SDK `createSession` wraps it. | VCKP-03 native start | Gated/best-effort (V13.1). Fixture-mock-verified in V14; real-server deferred. |

## Open Questions

1. **Native `run_id` vs `sessionID` vs node `id` relationship**
   - What we know: native sessions persist to `.voss/sessions/<id>.json` (PROTOCOL §10); `load_run` reads `<run_id>/<node>.json` per node and uses node filename stems as ids (`lib.rs:1112`); `enumerate_runs` lists run *directories*.
   - What's unclear: whether a single native turn's `sessionID` equals the run-dir name, a node id, both, or neither in the V4+ session-tree layout. The org snapshot is a *tree of nodes per run*; a native single session may be one node.
   - Recommendation: before W2, run one real native session (or inspect a fixture run dir) and confirm exactly which id the create-response equals. The id-bridge design tolerates this (A1) but the planner should add a W0 task to verify it against a real `.voss/sessions` tree.

2. **Does any harness write path exist for per-card follow-up (VCKP-09)?**
   - What we know: only `voss audit <id> --approve` is non-interactive (`decisionActions.ts`); PROTOCOL §5 `POST /session/:id/message` exists for *native* sessions.
   - What's unclear: whether routing an inline comment to a *snapshot* card has any CLI/REST surface.
   - Recommendation: VCKP-09 is best-effort — render disabled-with-reason for snapshot cards; for live native sessions, `POST message` via V13.1 is the only candidate. Confirm at build; default to disabled-with-reason.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node/Vitest | All TS tests | ✓ (assumed) | vitest 4.1.6 | — |
| V13.1 TS SDK | VCKP-03 native start, VCKP-06 live | ✓ in-repo | shipped (rest/sse/permission) | Snapshot fallback (VCKP-06); fixture-mock native start |
| `voss serve` running | Real live SSE (deferred) | ✗ (not started by webview) | — | Mock SSE stream (SPEC-blessed) |
| `sandbox-exec` (macOS) | VCKP-13a sandbox | ✓ on macOS (system) | system | Tier B/C if unavailable |
| `bwrap`/Landlock (Linux) | VCKP-13a sandbox (Linux) | ✗ unknown on dev (macOS host) | — | macOS Seatbelt is the dev target; Linux path is best-effort |
| Claude Code / OpenCode CLIs | VCKP-13b permission proxy | unknown (user-installed) | — | Tier B (sandbox only) if no hook support |

**Missing dependencies with no fallback:** none block the CORE path (VCKP-01..05/08/10) — all are pure TS + existing IPC.
**Missing dependencies with fallback:** live server (mock), Linux sandbox (macOS-first), per-CLI hooks (sandbox-only tier B).

## Validation Architecture

> `workflow.nyquist_validation: true` — section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.6 (`vitest run`) + Rust `cargo test` for `src-tauri`/`voss-app-core` |
| Config file | `apps/voss-app/vitest.config.ts` |
| Quick run command | `cd apps/voss-app && npx vitest run src/org` |
| Full suite command | `cd apps/voss-app && npm run test` (TS) · `cargo test -p voss-app-core` (Rust) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VCKP-01 | Adapter merges golden snapshot + fake registry into one model; card carries snapshot + overlay fields | unit | `npx vitest run src/org/model/__tests__/adapters.test.ts` | ❌ Wave 0 |
| VCKP-01 | `selectedCard` observed by ≥2 surfaces | component | `npx vitest run src/org/cockpit/__tests__/selection.test.tsx` | ❌ Wave 0 |
| VCKP-02 | `resolveCard('C1')` → `{paneId,sessionNodeId}`; click focuses pane; no-pane falls back to detail | unit+component | `npx vitest run src/org/model/__tests__/bridge.test.ts` | ❌ Wave 0 |
| VCKP-03 | Terminal start invokes launch path with mode/team/scope/budget; native start calls mock createSession; Auto w/o budget/scope blocked | component | `npx vitest run src/org/cockpit/__tests__/runCommandBar.test.tsx` | ❌ Wave 0 |
| VCKP-04 | permission + budget-threshold + sign-off items render with deep-links; permission exposes allow/scoped/deny | component | `npx vitest run src/org/attention/__tests__/attentionQueue.test.tsx` | ❌ Wave 0 |
| VCKP-05 | one selection drives Board + drawer + timeline + gate bar; ⌘⇧O + grid unchanged | component | `npx vitest run src/org/cockpit/__tests__/cockpit.test.tsx` | ❌ Wave 0 |
| VCKP-06 | mock SSE drives board+budget w/o refresh; live/snapshot label correct | unit | `npx vitest run src/org/live/__tests__/sseClient.test.ts` | ❌ Wave 0 |
| VCKP-07 | fixture manifest (2 agents) → 2 roster rows + 2 cards by status; absent swarm degrades | unit | `npx vitest run src/org/__tests__/swarmReconcile.test.ts` | ❌ Wave 0 |
| VCKP-08 | Live↔Review preserves selected run/card; grid unchanged | component | `npx vitest run src/__tests__/liveReviewToggle.test.tsx` | ❌ Wave 0 |
| VCKP-09 | comment dispatches to correct sessionNodeId where write path exists; else disabled-with-reason | unit | `npx vitest run src/org/__tests__/feedbackWritePath.test.ts` | ❌ Wave 0 |
| VCKP-10 | keyboard focus Board→drawer→timeline; no new tokens (grep gate); reduced-motion disables animation | component+lint | `npx vitest run src/org/cockpit/__tests__/a11y.test.tsx` + token grep | ❌ Wave 0 |
| VCKP-11 | preset spawn uses resolved command; no raw-command/explainer; ⌘↵ launches; lands under External Terminal Agents | component | `npx vitest run src/components/modal/__tests__/agentLaunchModal.test.tsx` | ⚠️ exists, extend |
| VCKP-12 | adopt binds card to pane, applies budget+scope, starts partial_lineage node, enforces review; no jargon/per-tool promise; disabled-with-reason where no harness path | component | `npx vitest run src/components/modal/__tests__/adoptAgentModal.test.tsx` | ❌ Wave 0 |
| VCKP-13 | sandbox denies out-of-scope write (OS layer); budget-kill at limit; correct tier per CLI; adopted=tier C | rust+component | `cargo test -p voss-app-core sandbox` + `npx vitest run src/org/__tests__/capabilityTier.test.ts` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `npx vitest run src/org` (org cockpit slice)
- **Per wave merge:** `npm run test` (full TS) + `cargo test -p voss-app-core`
- **Phase gate:** Full TS + Rust suites green; V11 `org/__tests__/*` and grid tests unchanged; token grep gate passes; before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `src/org/model/__tests__/adapters.test.ts` + golden snapshot fixture (reuse `org/__tests__/fixtures`) — VCKP-01
- [ ] `src/org/model/__tests__/bridge.test.ts` + fixture binding card C1↔pane P1↔node N1 — VCKP-02 (verify A1 against a real `.voss/sessions` tree here)
- [ ] `src/org/cockpit/__tests__/selection.test.tsx`, `cockpit.test.tsx`, `runCommandBar.test.tsx`, `a11y.test.tsx` — VCKP-01/03/05/10
- [ ] `src/org/attention/__tests__/attentionQueue.test.tsx` — VCKP-04
- [ ] `src/org/live/__tests__/sseClient.test.ts` + mock SSE stream helper — VCKP-06
- [ ] `cargo test` sandbox profile test (out-of-scope write denied) — VCKP-13a
- [ ] Token grep gate script (assert no new `--xxx` custom properties vs voss-ignite.json) — VCKP-10
- [ ] Extend `agentLaunchModal.test.tsx`; add `adoptAgentModal.test.tsx` — VCKP-11/12

## Security Domain

> `security_enforcement` absent in config → treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local single-user desktop; SSE uses the V13.1 loopback Bearer token (handled by SDK). |
| V3 Session Management | partial | Native session id is harness-minted (`uuid4().hex[:12]`); token is loopback-only. |
| V4 Access Control | **yes** | **VCKP-13 is the access-control story.** OS sandbox = filesystem authorization at the kernel; permission proxy = tool authorization per-CLI. |
| V5 Input Validation | yes | Run-id traversal already guarded (`is_safe_run_id`, `lib.rs:1066`); managed-launch scope paths must be validated/canonicalized before building the sandbox profile. |
| V6 Cryptography | no | No new crypto; reuse V13.1 token handling. |
| V12 Files & Resources | **yes** | Sandbox writable-subpath allowlist is the file-resource control; never widen beyond the scope chip. |

### Known Threat Patterns for {Tauri webview + external CLI agents}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| External CLI writes outside intended scope | Tampering / Elevation | OS sandbox (Seatbelt `deny file-write*` + subpath allow) — kernel-enforced, CLI-agnostic [CITED: 7402.org, michaelneale/agent-seatbelt-sandbox] |
| Runaway agent burns unbounded cost/tokens | DoS | Budget-kill via `budget_update` PtyEvent → `pty_kill` (universal, tier C) |
| Adopted agent presented as fully gated when it isn't | Repudiation / spoofed control | Tier C UI + honest copy (D-11) — never claim per-tool gate on PTY-only agents |
| Path traversal in scope/run ids | Tampering | Existing `is_safe_run_id` + canonicalize scope before sandbox profile (V5) |
| Sandbox profile too permissive (allow default) | Elevation | Start from `deny file-write*`, allow only the scope subpath + `/tmp`; review the generated profile |
| Permission-proxy bypass (`--dangerously-skip-permissions`) | Elevation | Sandbox (tier A floor) still denies at kernel even if the CLI skips its own prompt; never rely on the proxy alone [CITED: pasqualepillitteri PreToolUse guide] |

## Sources

### Primary (HIGH confidence — in-repo, verified this session)
- `apps/voss-app/src/org/{types.ts,orgStore.ts,boardDerive.ts,guards.ts,OrgViewShell.tsx,decisionActions.ts}` — snapshot plane, panel reuse, D-02 contract
- `apps/voss-app/src/org/panels/BoardPanel.tsx` — panel prop shape (`data`/`onCardSelect`/`selectedCardId`)
- `apps/voss-app/src-tauri/src/lib.rs` — `spawn_agent` (:181), `load_run` (:1078), `register_agent` call (:216), swarm cmds (:602/:634)
- `crates/voss-app-core/src/agent_registry.rs` — `AgentEntry`/`session_id` semantics, schema
- `crates/voss-app-core/src/pty/mod.rs` — `spawn_command_session_with_env` (:189) spawn site (VCKP-13)
- `apps/voss-app/src/pane/{pty-ipc.ts,budgetRegistry.ts,agentPaneRegistry.ts}` — live plane, `sessionId` minting, cost tracking
- `apps/voss-app/src/App.tsx` — `orgViewOpen` (:240), StatusBar (:1271), `handleLaunchAgent` stub (:268)
- `sdk/typescript/src/{index.ts,client/sse.ts,launcher/launcher.ts}` — V13.1 SSE consumer (shipped) + Node-only launcher caveat
- `.planning/PROTOCOL.md` §5/§6/§7/§10/§11 — SSE event union, `sessionID` correlation, `uuid4().hex[:12]` id
- `.planning/STATE.md` — V13.1/V13.2 SDK shipped status
- `apps/voss-app/src/themes/bundled/voss-ignite.json` — A12 token set (VCKP-10)

### Secondary (MEDIUM confidence — official docs)
- macOS Seatbelt / sandbox-exec: [7402.org sandboxing-of-folder](https://7402.org/blog/2020/macos-sandboxing-of-folder.html), [michaelneale/agent-seatbelt-sandbox](https://github.com/michaelneale/agent-seatbelt-sandbox), [igorstechnoclub sandbox-exec](https://igorstechnoclub.com/sandbox-exec/)
- Claude Code hooks: [code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks), [PreToolUse permission guide](https://pasqualepillitteri.it/en/news/1832/claude-code-dangerously-skip-permissions-pretooluse-hooks-2026)
- OpenCode permissions: [opencode.ai/docs/permissions](https://opencode.ai/docs/permissions/)

### Tertiary (LOW confidence — to verify at build)
- Native `run_id`/`sessionID`/node-`id` exact equivalence (Open Question 1 / A1) — verify against a real `.voss/sessions` tree in W0.

## Metadata

**Confidence breakdown:**
- Keystone id-bridge: HIGH — verified both id namespaces in code; resolution mechanism is concrete (one residual: A1 native id equivalence, flagged).
- Standard stack / panel reuse: HIGH — panels are already prop-driven; V13.1 SDK confirmed in-repo.
- Live wiring (VCKP-06): HIGH for consumer (SDK shipped); MEDIUM for the server-start seam (Node-only launcher caveat).
- VCKP-13 enforcement: MEDIUM — cited from official docs (Seatbelt/Claude hooks/OpenCode), not yet exercised in this repo; sandbox is the reliable floor.
- Pitfalls: HIGH — grounded in code + project memory.

**Research date:** 2026-06-08
**Valid until:** 2026-07-08 (stable in-repo facts) · 7 days for external CLI hook schemas (Claude Code / OpenCode evolve fast)
