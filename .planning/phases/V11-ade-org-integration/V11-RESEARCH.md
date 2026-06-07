# Phase V11: ADE Org Integration — Research

**Researched:** 2026-06-07
**Domain:** SolidJS/Tauri frontend — org-panel view consuming Python CLI JSON
**Confidence:** HIGH (all findings verified directly from codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** One aggregate Tauri command `load_run(run_id)` shells all sources (`voss board` / `voss review` / `voss audit --json` / session-tree export / `run-final.json`) and returns a single typed `RunData` object.
- **D-02:** Frontend types CLI JSON with **hand-authored TS interfaces** in `apps/voss-app/src`, runtime-validated at the Tauri boundary. Flagged for replacement by V13.1 codegen. Leave a `// V13.1-REPLACE: hand-authored stopgap` marker.
- **D-03:** Run discovery is a **Rust/Tauri-side command** that enumerates `.voss/sessions/` root dirs (+ light metadata: mtime, status). No new harness CLI contract.
- **D-04:** Org/Run view **auto-loads the most-recent run** on open; a picker lets the user switch runs.
- **D-05:** Replay folds `transitions[]` + `run-final.json` **client-side** — `load_run` returns full transition history; app folds in-memory (reducer) to derive board/card state at step N.
- **D-06:** Replay reducer reconstructs **board/card state only** (columns + card status/role/risk/budget) per step. Other panels show the **final snapshot**.
- **D-07:** Every decision action shows a **confirmation dialog with the exact CLI command + target card** before shelling.
- **D-08:** After a decision action, Tauri wrapper captures stdout/stderr/exit code; app shows success/failure inline and **auto-refreshes `load_run`**.

### Claude's Discretion

- **Test-fixture strategy:** Use **golden JSON fixtures** captured from a real persisted run, driving panel/reducer tests in **vitest**. Tauri WebDriver E2E stays **skip-deferred on macOS**; gate on vitest + `tsc --noEmit` + `cargo` instead.
- **Error/empty granularity:** View-level empty/error state is the primary boundary (invalid/missing run → empty/error, no crash). Per-panel "no data" states are fine where a source is individually absent.
- **Panel build sequencing:** left to the planner. Suggested: data layer + view shell → structural panels → audit → budget/scope → diff drilldown → blocked-decision → replay.

### Deferred Ideas (OUT OF SCOPE)

- Live streaming during an active run.
- All-panels time-travel during replay (board/card only per D-06).
- Codegen-typed CLI contract (V13.1 owns that).
- V11-UI-SPEC visual design contract (already produced; this phase implements it).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VADE-DATA | CLI-JSON data layer: thin Tauri wrappers invoke `voss board`/`voss review`/`voss audit --json`/session-tree export, return typed `RunData` | Tauri command pattern documented; board/review/audit CLI signatures verified; session-tree `export_tree()` verified |
| VADE-VIEW | Org/Run view mode: dedicated toggleable view hosting panels, static snapshot + manual refresh, no grid disturbance | App.tsx view-toggle pattern studied; existing swarm view and `display: none` workspace isolation confirmed |
| VADE-01/02 | Roster + board panels: 6 columns + cards with role/risk/status/budget | `board.cli_view._COLUMNS`, `Card` fields, `_derive_column/risk` logic documented |
| VADE-03 | Session-tree panel: navigable parent→child tree | `export_tree()` and `SessionTreeNode` schema verified |
| VADE-04 | Reviewer-verdict panel: A and B shown separately | `review_cmd` sidecar format + `ReviewerVerdict` shape verified |
| VADE-05 | Audit panel: §9 sections, claims-vs-evidence, unsupported flags, residual-risk | `AuditReport`/`AuditSnapshot` fully documented; `render_json()` output shape verified |
| VADE-06/07 | Budget + scope visualization: per root/card/agent and per role/card | `envelope.spent/limit` on SessionTreeNode verified; scope from `TeamRoleScope.globs` field |
| VADE-08 | Diff + verification drilldown per card | `.review.json` sidecar `a_verification` field documented; diff_summary is in `sections_missing` for V2-V7 substrate |
| VADE-09 | Blocked-card decision flow: panel lists blocked cards; actions shell V7/V9 CLI | `board_cmd` blocked column derivation; `voss audit --approve` + `voss team run` CLI surfaces documented |
| VADE-10 | Run replay: step through `transitions[]` + `run-final.json` to reconstruct board/card state | `SessionTreeNode.transitions[]` shape verified; `run-final.json` `RunFinal` shape verified; D-05 reducer confirmed viable |

</phase_requirements>

---

## Summary

V11 is a pure frontend consumer phase: it does not touch the Python harness and does not alter any JSON contracts. The key constraint is that **all harness data already exists on disk** in `.voss/sessions/<root_id>/` — V11 builds the Rust/Tauri bridge and the SolidJS panels to render it.

The Tauri command pattern is well-established in this codebase (see `lib.rs`): thin `#[tauri::command]` fns in `src-tauri/src/lib.rs` delegate to `voss-app-core` or shell subprocesses, registered in `tauri::generate_handler![]`. The `invoke()` pattern is used pervasively throughout the SolidJS frontend.

The JSON contracts V11 consumes are all read from two sources: (1) the harness CLIs via subprocess (`voss board`, `voss review`, `voss audit --json`, `voss session tree <root_id> --json`), and (2) direct file reads that Rust performs on `.voss/sessions/<root_id>/` (for `load_run` aggregate and `enumerate_runs`). The concrete shapes are fully documented below.

The swarm view (`src/swarm/swarmTypes.ts`) is the closest existing precedent for a non-grid panel view, but it is minimal — it defines only TS types and relies on Tauri event emission, not a dedicated view shell with tab bar. The App.tsx view layout (Titlebar → WorkspaceTabBar → AgentSidebar + content area → StatusBar) is the structural host that the Org/Run view slot into by replacing `GridRoot`'s display without unmounting it.

**Primary recommendation:** Build the aggregate `load_run` Tauri command first (Wave 0/1), wire the view shell and tab routing second (Wave 1), then implement panels in waves following the order in D discretion. Every test should use golden JSON fixtures from real `.voss/sessions/` node files.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Run data loading | API / Rust (Tauri) | — | SPEC bars frontend raw-parsing; subprocess shells `voss` CLI |
| Run discovery (sessions enumerate) | API / Rust (Tauri) | — | D-03 explicit: Rust enumerates `.voss/sessions/`, not JS |
| Board/roster/session-tree panels | Frontend (SolidJS) | — | Read-only rendering of typed `RunData` |
| Audit/reviewer/budget/scope panels | Frontend (SolidJS) | — | Same: typed render layer |
| Replay reducer | Frontend (SolidJS) | — | D-05: client-side fold; must not be in Rust |
| Decision action (approve/reject/unblock) | API / Rust (Tauri) | — | Shells V7/V9 CLI; captures stdout/stderr/exit code |
| View-toggle state (Org ↔ Grid) | Frontend (SolidJS) | — | Local signal in App.tsx; no Rust involvement |
| TS type definitions | Frontend (SolidJS) | — | D-02: hand-authored in `apps/voss-app/src/org/` |

---

## Standard Stack

### Core (all already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| solid-js | 1.9.13 | Reactive UI | [VERIFIED: codebase] project convention |
| @tauri-apps/api | 2.11.0 | `invoke()` frontend IPC | [VERIFIED: codebase] project convention |
| vitest | 4.1.6 | Unit + reducer tests | [VERIFIED: codebase] already configured |

**No new npm packages required for V11.** All functionality is achievable with:
- The existing SolidJS reactive primitives (`createSignal`, `createMemo`, `createEffect`, `Show`, `For`)
- The existing `invoke()` from `@tauri-apps/api/core`
- Standard CSS variables from the existing Voss Ignite theme (`voss-ignite.json`)

### Rust Dependencies (already in workspace)

| Crate | Purpose |
|-------|---------|
| `serde` / `serde_json` | JSON serialization for Tauri command return types |
| `tauri` | Command registration |
| `std::process::Command` | Shell the `voss` CLI subprocess |

**No new Rust crates are needed.** The subprocess shelling pattern is already present in the codebase (see `git_log` command in `lib.rs` which uses `std::process::Command`).

### Installation

No new packages to install. Zero new dependencies is a hard constraint for V11 — the entire implementation fits within the existing stack.

---

## Package Legitimacy Audit

> No new packages are introduced in this phase. This section is intentionally empty.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
User                App.tsx              src-tauri/lib.rs       voss CLI (subprocess)
  |                    |                        |                        |
  |  Cmd+Shift+O       |                        |                        |
  |─────────────────>  |                        |                        |
  |              setOrgViewOpen(true)            |                        |
  |              auto-load most-recent run       |                        |
  |              invoke('load_run', {runId})─────>                        |
  |                    |                invoke voss board/review/         |
  |                    |                audit/session-tree/               |
  |                    |                run-final.json reads──────────>   |
  |                    |                        |    JSON stdout/file     |
  |                    |                        |<────────────────────    |
  |                    |                assemble RunData struct           |
  |                    |<────── Ok(RunData) ─────                        |
  |              store in createSignal           |                        |
  |              panels render from RunData      |                        |
  |                                              |                        |
  |  click Blocked → Approve                     |                        |
  |─────────────────>  |                         |                        |
  |              show confirm dialog             |                        |
  |              (exact CLI command shown)       |                        |
  |  click Confirm     |                         |                        |
  |─────────────────>  |                         |                        |
  |              invoke('run_decision',…)────────>                        |
  |                    |                shell: voss approve <run> <card>──>
  |                    |                        |  stdout/stderr/exit     |
  |                    |<────────── DecisionResult ───────────────────   |
  |              show success/failure inline     |                        |
  |              invoke('load_run', …) (refresh) |                        |
```

### Recommended Project Structure

```
apps/voss-app/src/org/           # V11 org module (new directory)
├── types.ts                     # RunData, BoardCard, SessionNode, etc.
│                                # V13.1-REPLACE marker at top of file
├── orgStore.ts                  # createSignal(runData), load/refresh logic
├── OrgViewShell.tsx             # Outer shell: header, tab bar, panel routing
├── panels/
│   ├── RosterPanel.tsx
│   ├── BoardPanel.tsx
│   ├── SessionTreePanel.tsx
│   ├── AuditPanel.tsx
│   ├── VerdictPanel.tsx
│   ├── BudgetPanel.tsx
│   ├── ScopePanel.tsx
│   ├── DiffPanel.tsx
│   ├── BlockedPanel.tsx
│   └── ReplayPanel.tsx
├── replayReducer.ts             # Pure function: transitions[] → BoardState at step N
├── decisionActions.ts           # invoke('run_decision', …) + dialog state
├── orgStyles.css                # V11-specific CSS variable additions
└── __tests__/
    ├── replayReducer.test.ts    # Reducer logic with golden JSON fixtures
    ├── boardPanel.test.tsx      # Panel rendering from fixture data
    └── fixtures/
        ├── node-root.json       # Golden SessionTreeNode (root)
        ├── node-child.json      # Golden SessionTreeNode (child with transitions)
        ├── review-sidecar.json  # Golden .review.json sidecar
        ├── run-final.json       # Golden RunFinal
        └── audit-report.json   # Golden AuditReport (from render_json)

apps/voss-app/src-tauri/src/lib.rs   # Add load_run + enumerate_runs + run_decision
```

**Note:** `vitest.config.ts` already includes `src/**/__tests__/**/*.test.{ts,tsx}` — the fixtures directory under `__tests__/` is automatically in scope.

### Pattern 1: Tauri Command with Subprocess — `git_log` Model

The `git_log` command in `lib.rs` is the direct precedent for shelling a subprocess and returning typed data:

```rust
// Source: apps/voss-app/src-tauri/src/lib.rs (VERIFIED: codebase)
#[tauri::command]
fn git_log(workspace_path: String, limit: usize) -> Result<Vec<GitCommit>, String> {
    let output = std::process::Command::new("git")
        .args(["-C", &workspace_path, "log", &format!("-{}", limit), "--format=%H %ct %s"])
        .output()
        .map_err(|e| e.to_string())?;

    if !output.status.success() {
        return Ok(Vec::new());  // graceful degradation
    }
    // parse stdout ...
    Ok(commits)
}
```

`load_run` follows the same shape: shell multiple `voss` subcommands, parse JSON stdout, assemble a `RunData` struct, return `Result<RunData, String>`.

**Registration:** All commands must be added to `tauri::generate_handler![]` in the `run()` function.

### Pattern 2: SolidJS `invoke()` Wrapper

```typescript
// Source: apps/voss-app/src/grid/sync.ts (VERIFIED: codebase)
import { invoke } from '@tauri-apps/api/core';

export async function loadRun(runId: string, cwd: string): Promise<RunData> {
  return invoke<RunData>('load_run', { runId, cwd });
}
```

### Pattern 3: View Toggle via `display: none` (Not Unmount)

App.tsx uses `display: activeId() === workspaceId ? 'flex' : 'none'` on workspace containers so `GridRoot` stays mounted. V11's Org/Run view toggle should follow the same pattern — set `display: none` on the GridRoot area when Org view is active, `display: none` on OrgViewShell when Grid is active.

```typescript
// Source: apps/voss-app/src/App.tsx (VERIFIED: codebase) — workspace toggle pattern
<div
  data-workspace-id={workspaceId}
  style={{ display: activeId() === workspaceId ? 'flex' : 'none', ... }}
>
  <GridRoot ... />
</div>
```

V11 pattern (in App.tsx, wrapping the existing GridRoot region):
```typescript
// grid area — hidden when org view active
<div style={{ display: orgViewOpen() ? 'none' : 'flex', flex: '1', ... }}>
  <For each={workspaceIds()}>{...}</For>
  <ContextPanel ... />
</div>
// org area — hidden when grid active
<Show when={orgViewOpen()}>
  <OrgViewShell cwd={workspacePath() ?? ''} onClose={() => setOrgViewOpen(false)} />
</Show>
```

### Pattern 4: Replay Reducer (Pure Function)

```typescript
// Source: D-05/D-06 + produce/proxy caveat from CONTEXT (ASSUMED for signature,
//         but data shapes are VERIFIED from SessionTreeNode.transitions schema)

// A "replay frame" = board state at step N
export interface BoardFrame {
  columns: Record<string, CardSnapshot[]>;
  step: number;
  eventLabel: string;
}

// Pure reducer — does NOT use produce() (proxy caveat: DATA_CLONE_ERR)
export function computeBoardAtStep(
  nodes: SessionTreeNodeRaw[],  // from RunData.sessionTree.nodes
  step: number
): BoardFrame {
  // Each board.transition in each node's transitions[]
  // Apply transitions up to index `step` in the global ordered list
  // Hand-clone output objects (no structuredClone, no produce drafts)
  // ...
}
```

**Critical constraint:** Reducer must use plain object literals for output — no `produce()` drafts, no `structuredClone()`. The `produce` drafts are Proxies → `DATA_CLONE_ERR` when passed across Tauri IPC or through SolidJS store mutations. [VERIFIED: codebase memory `voss-app-solid-produce-no-structuredclone`]

### Anti-Patterns to Avoid

- **Parsing `.voss/sessions/` JSON in TypeScript/SolidJS.** SPEC bars this; all file reading goes through Tauri commands. The D-03 `enumerate_runs` command is Rust-side.
- **Per-step `invoke('load_run')` calls during replay.** D-05 explicit: load once, fold client-side.
- **Using `structuredClone()` on SolidJS store data.** Safari15 build target + Solid proxies → use manual `JSON.parse(JSON.stringify(x))` or plain spreads.
- **Writing run decisions directly from JS.** SPEC constraint: `run_decision` Tauri command must shell the CLI; never write files directly.
- **Adding new Rust crates.** No new deps — use `std::process::Command`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Diff line rendering | Custom diff parser | Render the pre-parsed diff text from `.review.json` `a_verification.test_path_or_rubric` or from the `sections_missing` list | V2-V7 substrate does not persist raw diffs; diff_summary is always in `sections_missing` |
| CSS animation for refresh spinner | Custom JS timer | Pure CSS `@keyframes spin` + `animation: spin 0.8s linear infinite` | Already established pattern in A12 |
| Run discovery | JS filesystem scan | Rust `enumerate_runs` command reading `.voss/sessions/` dirs | SPEC bars frontend raw-parsing |
| Budget bar | Custom progress bar | Reuse existing `BudgetBar` pattern from F3 (`pane/PaneHeader` area) | Already ships correct threshold colors |

**Key insight:** The `.review.json` sidecar provides the Reviewer-A/B data; `run-final.json` provides RunFinal; node JSON files provide transitions and budget envelopes. All data is already persisted — V11 does not need to generate or transform anything, only read and render.

---

## Runtime State Inventory

> SKIPPED — this is a greenfield frontend phase, not a rename/refactor/migration. No runtime state is being modified.

---

## Upstream JSON Contracts (VERIFIED from codebase)

This section is the planner's primary reference for the `RunData` TS interface (D-02).

### 1. SessionTreeNode JSON (`<root_id>/<node_id>.json`)

```
{
  "id": "<12-char hex>",            // e.g. "abc123def456"
  "root_id": "<12-char hex>",       // same as root node's id
  "parent_run_id": "<id> | null",   // null for root
  "envelope": {
    "limit": 500000,                // token budget limit
    "spent": 12345                  // tokens spent
  },
  "terminal_state": {               // null if not finalized
    "exit_reason": "done|timeout|killed|error",
    "final": ""
  },
  "created_at": "2026-06-07T...",
  "ended_at": "2026-06-07T... | null",
  "rejected_raises": [...],         // cap-raise rejections (array of dicts)
  "transitions": [                  // per-card history — see below
    { "kind": "board.transition", ... },
    { "kind": "em.ticket", ... },
    { "kind": "em.routing", ... },
    { "kind": "em.kill", ... },
    { "kind": "em.rescope", ... }
  ],
  "retry_notes": [...],
  "scope": "some/glob/**" | null,   // V4 additive
  "role": "backend|frontend|..." | null  // V4 additive
}
```

**Transition shapes** (from `audit/load.py`, `cli_view.py`): [VERIFIED: codebase]

```
// board.transition
{ "kind": "board.transition", "from": "Backlog", "to": "InProgress",
  "outcome": "...", "verdict_snapshot": {
    "conf": 0.99, "source": "A"|"B", "tier": "fast"|"strong",
    "verdict": "pass"|"fail"|"block", "notes": "...", "evidence_refs": [],
    "domain_inferred": "code"|"ai"|"docs"|"unknown"
  } | null }

// em.ticket
{ "kind": "em.ticket", "risk_tier": "low"|"med"|"high", ... }

// em.routing
{ "kind": "em.routing", "id": "...", "card_id": "...", "chosen_role": "...",
  "candidates_considered": [...], "rationale_text": "...", "ts": "..." }

// em.kill
{ "kind": "em.kill", "killed_node_id": "...", "rationale_text": "...",
  "evidence_refs": [...], "killed_at": "..." }

// em.rescope
{ "kind": "em.rescope", "predecessor_card_id": "...", "successor_card_id": "...",
  "diff_summary": "...", "rationale_text": "...", "rescoped_at": "..." }

// em.run_final (embedded in transitions, also a separate file)
{ "kind": "em.run_final", ... }
```

**Column derivation** (from `board/cli_view._derive_column`): [VERIFIED: codebase]
Walk `transitions[]`, apply `board.transition` entries in order, then apply `terminal_state.exit_reason` override (timeout/killed → "Blocked", done → "Done"). Last `board.transition.to` wins otherwise. Default is "Backlog".

**Risk derivation** (from `board/cli_view._derive_risk`): [VERIFIED: codebase]
Find first `em.ticket` transition; return `risk_tier` field. Default "med" if absent.

### 2. `run-final.json` (RunFinal) [VERIFIED: codebase — `em/tickets.py`]

```
{
  "root_id": "<12-char hex>",
  "idea": "User's original task goal string",
  "total_cards": 3,
  "done_count": 2,
  "blocked_count": 1,
  "killed_count": 0,
  "rescope_count": 0,
  "em_iterations": 5,
  "ts": "2026-06-07T...",
  "kind": "em.run_final",
  "sign_off": {                     // optional, added by voss team run approve/reject
    "decision": "approve"|"reject",
    "ts": "2026-06-07T..."
  }
}
```

### 3. `.review.json` Sidecar (per card) [VERIFIED: codebase — `cli.py` `_render_review_card`]

Path: `.voss/sessions/<root_id>/<node_id>.review.json`

```
{
  "a_verification": {               // Reviewer-A result (or null/absent)
    "result": "pass"|"fail"|"...",
    "test_path_or_rubric": "tests/...",
    "notes": "..."
  } | null,
  "b_verdict": {                    // Reviewer-B verdict (or null/absent)
    "verdict": "pass"|"fail"|"block",
    "conf": 0.84,
    "tier": "fast"|"strong",
    "domain_inferred": "code"|"ai"|"docs"|"unknown",
    "notes": "...",
    "evidence_refs": ["file:line", ...]
  } | null,
  "final_outcome": "pass"|"fail"|"block"|"?"
}
```

### 4. `voss audit --format json` Output [VERIFIED: codebase — `audit/render.render_json`]

`render_json(AuditReport)` produces a JSON serialization of the entire `AuditReport` dataclass hierarchy. Key fields the panels need:

```
{
  "run_id": "<root_id>",
  "idea": "...",
  "principles": [["key", "text"], ...],
  "team_config": { "source": "...", "roster_ids": [...] },
  "snapshot": {
    "root_id": "...",
    "nodes": [ AuditNode, ... ],
    "cards": [
      {
        "node_id": "...", "column": "Done", "risk_tier": "med",
        "retry_count": 0, "is_killed": false, ...
      }
    ],
    "kills": [...], "rescopes": [...], "routings": [...],
    "verdicts": [...], "liveness": [...],
    "leak6": { "status": "accepted_gap", "evidence": "...", "mitigation_present": false },
    "run_final": { ... } | null
  },
  "review_sidecars": {
    "<node_id>": { "a_verification": {...}|null, "b_verdict": {...}|null, "final_outcome": "..." },
    ...
  },
  "run_final": { ... } | null,
  "signoff_ack": { "ack_ts": "...", "killed_count": 0, "misroute_count": 0 } | null,
  "calibration": { "total_pairs": 0, ... },
  "sections_missing": ["diff_summary", "tests_evals"],  // always present in V2-V7 substrate
  "unsupported_claims": ["<node_id>", ...]  // nodes with em.ticket but no review evidence
}
```

**Critical note for V11:** `sections_missing` always contains `"diff_summary"` and `"tests_evals"` — the diff + tests/eval data genuinely does not exist in the V2-V7 substrate. The Diff panel (VADE-08) must render `a_verification.test_path_or_rubric` from the `.review.json` sidecar as the "verification result" — this is the only per-card verification data that actually exists. Raw diffs are not persisted anywhere; the Diff panel shows the test/rubric context instead.

### 5. `voss session tree <root_id> --json` Output [VERIFIED: codebase — `session_tree.export_tree`]

```
{
  "root_id": "<12-char hex>",
  "nodes": [
    { ...full SessionTreeNode dict... },  // one per <node_id>.json file
    ...
  ]
}
```

This is the session-tree export that Panel 3 (Tree) and the replay reducer consume.

### 6. Board Column Mapping [VERIFIED: codebase — `board/machine.py` and `board/cli_view.py`]

The canonical 6 columns are: `"Backlog"`, `"Planned"`, `"InProgress"`, `"InReview"`, `"Blocked"`, `"Done"`.

**Note:** The V11-UI-SPEC uses `"Todo"` as the second tab label (PanelTabBar: Roster/Board/Tree/...) but the Board panel columns display the actual column names from the harness. The tab label is "Board"; the column headers inside the panel match harness values. The CLI/harness second column is "Planned" — the UI-SPEC column header mapping is:
- Backlog → `--org-col-backlog`
- **Planned** (harness name, UI-SPEC shows "Todo" in the tab but columns render harness names) → `--org-col-todo`
- InProgress → `--org-col-in-progress`
- InReview → `--org-col-in-review`
- Done → `--org-col-done`
- Blocked → `--org-col-blocked`

### 7. Run Discovery Layout [VERIFIED: codebase]

`.voss/sessions/` contains two kinds of entries:
- **Flat `<id>.json` files** — these are legacy `SessionRecord` files from `session_store.list_sessions()`. They have `"id"`, `"name"`, `"model"`, `"turns"`, `"runs"` fields. These are NOT session-tree run directories.
- **Subdirectories `<root_id>/`** — these are V4+ session-tree run directories containing `<node_id>.json` files, `.review.json` sidecars, and `run-final.json`.

The `enumerate_runs` Tauri command (D-03) must only enumerate **subdirectories** with at least one `.json` node file, not flat session files.

---

## Common Pitfalls

### Pitfall 1: Flat Session Files vs. Session-Tree Run Directories
**What goes wrong:** `enumerate_runs` iterates `.voss/sessions/` and picks up the flat `<id>.json` session records as if they were run directories, causing spurious entries in the run picker.
**Why it happens:** Both the flat session store and the session-tree system use the same `.voss/sessions/` path with different layout conventions.
**How to avoid:** `enumerate_runs` must `read_dir` and filter for **entries that are directories** only. Flat `.json` files at the top level are session records, not run roots. [VERIFIED: codebase — `.voss/sessions/` listing shows 12 flat files, 0 subdirs in development env]
**Warning signs:** Run picker shows entries with no panels rendering data.

### Pitfall 2: `load_run` Aggregate — Subprocess Path Resolution
**What goes wrong:** `voss` subprocess is not found because the PATH inside Tauri's sandboxed process differs from the shell PATH.
**Why it happens:** Tauri apps on macOS inherit a minimal login-shell PATH; `voss` may be installed in a virtualenv or custom location.
**How to avoid:** Provide a `cwd` option to the subprocess and pass the `voss` binary path from the frontend (same pattern as `spawn_agent` uses `cli_binary` from the frontend). Store the resolved `voss` binary path in settings or discover it at load_run time.
**Warning signs:** `load_run` returns error even for a valid `run_id`.

### Pitfall 3: Replay Reducer — produce/proxy Caveat
**What goes wrong:** `DATA_CLONE_ERR` when replay reducer uses `produce()` or `structuredClone()` on SolidJS store values.
**Why it happens:** SolidJS store values accessed in the render layer are Proxy objects. `produce` creates a draft Proxy. Passing either to `structuredClone` or Tauri IPC fails. [VERIFIED: codebase — memory `voss-app-solid-produce-no-structuredclone`]
**How to avoid:** The replay reducer must be a **pure function operating on plain deserialized objects** from `RunData` (which came through `invoke()` and was already deserialized to plain JS). Never call the reducer with data accessed via `store.field` — extract to a plain variable first. Return new plain objects via object spread `{...card, column: 'Done'}`.
**Warning signs:** `DATA_CLONE_ERR` in console on step advance.

### Pitfall 4: `sections_missing` — Diff Data Does Not Exist
**What goes wrong:** Diff panel (VADE-08) tries to display `report.snapshot.diff_summary` but crashes because it is always in `sections_missing` for V2-V7 runs.
**Why it happens:** The Python harness does not persist raw diffs anywhere in V2-V7 (`_ALWAYS_MISSING = ("diff_summary", "tests_evals")` hardcoded in `audit/report.py`). [VERIFIED: codebase]
**How to avoid:** The Diff panel should render `a_verification` from the `.review.json` sidecar as the per-card "verification result". Show "No diff recorded for this card." when `a_verification` is null. Do not attempt to fetch `snapshot.diff_summary` from audit JSON — it will always be absent.
**Warning signs:** Diff panel shows no data for any card even when reviews exist.

### Pitfall 5: Missing `run-final.json` on Early-Stage Runs
**What goes wrong:** `load_run` fails or crashes if `run-final.json` is absent (run was interrupted before `_persist_run_final` was called).
**Why it happens:** `run-final.json` is only written at the end of `voss team run`. A session-tree directory with only node files (no `run-final.json`) is a valid incomplete run.
**How to avoid:** Treat `run-final.json` as optional. `load_run` returns `run_final: null` in `RunData` when absent. Panels that depend on `run_final` (Replay source, RunFinal summary) show per-panel "no data" state.
**Warning signs:** `load_run` errors on runs that started but didn't complete.

### Pitfall 6: Grid Regression on View Toggle
**What goes wrong:** GridRoot's PTY panes disconnect or lose state when toggling to Org view and back.
**Why it happens:** Using `Show` conditionally renders/destroys GridRoot, terminating PTY sessions.
**How to avoid:** Use `display: none` CSS hide (same pattern as workspace tab switching in App.tsx — confirmed working). Never use `Show` around the GridRoot area for the view toggle — use CSS `display`.
**Warning signs:** Terminal history lost on toggle back; PTY sessions require re-spawn.

### Pitfall 7: `voss audit --format json` Requires `--cwd`
**What goes wrong:** `audit_cmd` resolves the sessions directory from `cwd_str` (defaults to `"."`). When shelled from Tauri without an explicit `--cwd`, it resolves to the Tauri app's working directory (not the user's project root).
**Why it happens:** `audit_cmd` uses `Path(cwd_str).resolve()` where default `cwd_str = "."`. [VERIFIED: codebase — `cli.py:2541`]
**How to avoid:** `load_run` in Rust must pass `--cwd <workspace_path>` to all CLI subcommands. `workspace_path` should come from the frontend as a parameter to `load_run`.
**Warning signs:** Audit panel always shows empty/no runs found.

---

## Code Examples

### Tauri Command Pattern: `load_run` Skeleton

```rust
// Source: apps/voss-app/src-tauri/src/lib.rs — git_log model (VERIFIED: codebase)
#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct RunData {
    run_id: String,
    board: serde_json::Value,      // raw JSON from `voss board --json` or node parse
    review: serde_json::Value,     // raw JSON from review sidecars
    audit: serde_json::Value,      // raw JSON from `voss audit --format json`
    session_tree: serde_json::Value, // from export_tree (node files glob)
    run_final: Option<serde_json::Value>, // from run-final.json if present
}

#[tauri::command]
fn load_run(run_id: String, cwd: String) -> Result<RunData, String> {
    // Path traversal guard (mirror board_cmd pattern)
    if run_id.contains('/') || run_id.contains('\\') || run_id.contains("..") {
        return Err(format!("invalid run_id: {}", run_id));
    }
    // Shell `voss audit --format json --cwd <cwd> <run_id>`
    // Read node files directly for session_tree (avoid extra subprocess)
    // Read run-final.json directly
    // Read .review.json sidecars directly
    // Assemble RunData
    // ...
    todo!()
}
```

### Tauri Command Pattern: `enumerate_runs`

```rust
// Source: new command following lib.rs conventions (ASSUMED signature)
#[derive(Debug, serde::Serialize)]
struct RunEntry {
    run_id: String,
    mtime_secs: u64,
    has_run_final: bool,
}

#[tauri::command]
fn enumerate_runs(cwd: String) -> Vec<RunEntry> {
    let sessions_dir = std::path::Path::new(&cwd).join(".voss").join("sessions");
    let rd = match std::fs::read_dir(&sessions_dir) {
        Ok(rd) => rd,
        Err(_) => return Vec::new(),
    };
    let mut entries: Vec<RunEntry> = rd
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().map(|t| t.is_dir()).unwrap_or(false))
        .filter_map(|e| {
            let run_id = e.file_name().to_string_lossy().into_owned();
            let mtime = e.metadata().ok()?.modified().ok()?
                .duration_since(std::time::UNIX_EPOCH).ok()?.as_secs();
            let has_run_final = e.path().join("run-final.json").exists();
            Some(RunEntry { run_id, mtime_secs: mtime, has_run_final })
        })
        .collect();
    entries.sort_by(|a, b| b.mtime_secs.cmp(&a.mtime_secs));
    entries
}
```

### SolidJS View Toggle Pattern

```typescript
// Source: apps/voss-app/src/App.tsx (VERIFIED: codebase) — adapted for org toggle
// In App() component, add:
const [orgViewOpen, setOrgViewOpen] = createSignal(false);
// Add ⌘⇧O handler in onAppKey:
if (e.metaKey && e.shiftKey && (e.key === 'o' || e.key === 'O')) {
  setOrgViewOpen(prev => !prev);
  e.preventDefault(); e.stopImmediatePropagation();
  return;
}
// In JSX, replace GridRoot area:
<div style={{ display: orgViewOpen() ? 'none' : 'flex', flex: '1', ... }}>
  {/* existing GridRoot For loop */}
</div>
<Show when={orgViewOpen()}>
  <OrgViewShell cwd={workspacePath() ?? ''} onClose={() => setOrgViewOpen(false)} />
</Show>
```

### Replay Reducer Test Pattern

```typescript
// Source: D-05/D-06 + vitest config (VERIFIED: codebase vitest.config.ts)
// apps/voss-app/src/org/__tests__/replayReducer.test.ts
import { describe, it, expect } from 'vitest';
import { computeBoardAtStep } from '../replayReducer';
import nodeRoot from './fixtures/node-root.json';
import nodeChild from './fixtures/node-child.json';

describe('replayReducer', () => {
  it('starts all cards at Backlog at step 0', () => {
    const frame = computeBoardAtStep([nodeRoot, nodeChild], 0);
    expect(frame.columns['Backlog']).toHaveLength(1);
  });

  it('advances card to InProgress at the correct step', () => {
    const frame = computeBoardAtStep([nodeRoot, nodeChild], 1);
    const card = frame.columns['InProgress']?.find(c => c.id === nodeChild.id);
    expect(card).toBeDefined();
  });
});
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-source Tauri commands (separate board/review/audit commands) | Aggregate `load_run` (D-01) | V11 CONTEXT | One error boundary; simpler frontend |
| Raw file parsing in frontend | Rust-side subprocess + file reading only | V11 SPEC constraint | No duplication of column-derivation logic |
| In-memory M13Allocator for multi-agent | V4 SessionTreeManager + persisted nodes | V4 COMPLETE | V11 reads V4-format node files; backward compat via `_hydrate_node` defaults |

**Deprecated/outdated:**
- `M13Allocator`: removed in V8; V11 reads V4 SessionTreeNode format only.
- `sessions_cmd` flat session records: V11 ignores these (they live at `.voss/sessions/*.json`, not in subdirectories).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `enumerate_runs` command signature (RunEntry fields) | Code Examples | Low — internal struct; planner can adjust |
| A2 | `voss audit --format json` is the correct flag (vs `--json`) | Upstream Contracts | HIGH — `audit_cmd` verified at line 2541; `fmt` parameter choices are `["text", "json", "markdown"]`; so flag is `--format json` |
| A3 | UI-SPEC "Todo" column label maps to harness "Planned" | Upstream Contracts / Architecture | Medium — planner should verify display name mapping vs harness name |
| A4 | `load_run` should read node files directly (not shell `voss session tree`) for session-tree data | Architecture | Low — `export_tree` is a simple glob; Rust direct read is faster and avoids subprocess overhead |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

Note on A2: [VERIFIED: codebase] — confirmed at `cli.py:2542`: `type=click.Choice(["text", "json", "markdown"]), default="text"`. The correct invocation is `voss audit <run_id> --cwd <path> --format json`.

---

## Open Questions (RESOLVED)

1. **`voss` binary location in Tauri process context**
   - What we know: `spawn_agent` receives `cli_binary` from the frontend (the user-configured voss binary path).
   - What's unclear: How does `load_run` know the voss binary path? Either (a) accept it as a parameter from the frontend (same as `spawn_agent`), or (b) derive it from the Rust environment.
   - **RESOLVED:** Accept `cli_binary: String` parameter from frontend (mirror `spawn_agent` pattern); frontend passes the configured voss path. Implemented in Plan 02 Task 1 (`load_run(run_id, cwd, cli_binary)`).

2. **Board data source for `load_run`**
   - What we know: `voss board <root_id> --cwd <path>` shells into `board/cli_view.render_board()` which reads node files and outputs text, not JSON. No `--format json` or `--json` flag exists on `board_cmd`.
   - What's unclear: Should `load_run` (a) read node files directly in Rust (same as what `render_board` does), or (b) shell `voss session tree --json` to get all nodes and derive board state in Rust?
   - **RESOLVED:** Read node files directly in Rust (enumerate `<root_id>/*.json`, exclude `.review.json`, read each, derive column/risk per the verified algorithm). Avoids shelling `voss` for board data and matches the Rust-side `enumerate_runs` pattern. Implemented in Plan 02 Task 1.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| node / npm | vitest, npm run test | ✓ | v22.22.2 | — |
| voss CLI | `load_run` subprocess (audit) | ✓ | installed | — |
| Rust / cargo | src-tauri build | ✓ | (workspace) | — |
| `.voss/sessions/` subdirs | `enumerate_runs`, `load_run` testing | ✗ in dev env | — | Use golden JSON fixtures in tests; real runs created by `voss team run` |

**Missing dependencies with no fallback:** None that block implementation.

**Missing dependencies with fallback:** `.voss/sessions/` run directories do not exist in the current dev environment (only flat session records exist). Tests must use static golden JSON fixtures authored from the verified schemas above.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | vitest 4.1.6 |
| Config file | `apps/voss-app/vitest.config.ts` (environment: jsdom) |
| Quick run command | `cd apps/voss-app && npm run test` |
| Full suite command | `cd apps/voss-app && npm run test && npx tsc --noEmit && cargo test -p voss-app-core` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VADE-DATA | `load_run` returns typed RunData for valid run_id | unit (Rust) | `cargo test -p voss-app-core` or inline lib.rs test | ❌ Wave 0 |
| VADE-VIEW | Org view toggle shows OrgViewShell; GridRoot not destroyed | unit (vitest) | `npm run test` | ❌ Wave 0 |
| VADE-01 | Roster panel renders agent rows from RunData fixture | unit (vitest) | `npm run test` | ❌ Wave 1 |
| VADE-02 | Board panel renders 6 columns + cards with risk/role/budget | unit (vitest) | `npm run test` | ❌ Wave 1 |
| VADE-03 | Session tree panel renders node hierarchy + node select | unit (vitest) | `npm run test` | ❌ Wave 1 |
| VADE-04 | Reviewer verdict panel shows A and B separately | unit (vitest) | `npm run test` | ❌ Wave 1 |
| VADE-05 | Audit panel renders §9 sections + flags unsupported claims | unit (vitest) | `npm run test` | ❌ Wave 2 |
| VADE-06/07 | Budget/scope panels render per root/card/agent/role | unit (vitest) | `npm run test` | ❌ Wave 2 |
| VADE-08 | Diff panel renders `a_verification` data for selected card | unit (vitest) | `npm run test` | ❌ Wave 2 |
| VADE-09 | Blocked panel lists blocked cards + CLI command in dialog | unit (vitest) | `npm run test` | ❌ Wave 3 |
| VADE-10 | Replay reducer: board state correct at each step N | unit (vitest) | `npm run test` | ❌ Wave 0 |
| VADE-10 | Replay panel: forward/back buttons advance/retreat step | unit (vitest) | `npm run test` | ❌ Wave 3 |

**E2E tests (Tauri WebDriver):** Skip-deferred on macOS. Platform-blocked — confirmed by prior A-track decision. [VERIFIED: codebase memory `voss-app-tauri-e2e-macos-blocked`]

### Sampling Rate

- **Per task commit:** `cd apps/voss-app && npm run test` (vitest only — < 30s)
- **Per wave merge:** `cd apps/voss-app && npm run test && npx tsc --noEmit` + `cargo test -p voss-app-core`
- **Phase gate:** Full suite green before `/gsd-verify-work`: vitest + tsc + cargo, existing tests unchanged

### Wave 0 Gaps

- [ ] `apps/voss-app/src/org/__tests__/replayReducer.test.ts` — covers VADE-10 reducer logic
- [ ] `apps/voss-app/src/org/__tests__/fixtures/node-root.json` — golden root node fixture
- [ ] `apps/voss-app/src/org/__tests__/fixtures/node-child.json` — golden child node with board.transition entries
- [ ] `apps/voss-app/src/org/__tests__/fixtures/review-sidecar.json` — golden .review.json sidecar
- [ ] `apps/voss-app/src/org/__tests__/fixtures/run-final.json` — golden RunFinal
- [ ] `apps/voss-app/src/org/__tests__/fixtures/audit-report.json` — golden render_json output

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (local desktop app; no auth boundary) |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Path traversal guard on `run_id` in Rust (mirror `board_cmd` pattern) |
| V6 Cryptography | no | — |

### Known Threat Patterns for Tauri + subprocess stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `run_id` | Tampering | Reject `run_id` containing `/`, `\\`, `..` before any filesystem access (mirror `board_cmd` at `cli.py:3975`) [VERIFIED: codebase] |
| Command injection via `run_id` passed to subprocess | Tampering | Use `std::process::Command::arg()` (not shell string interpolation) — same as `git_log` in lib.rs [VERIFIED: codebase] |
| Stale `RunData` shown after a decision action | Information Disclosure | D-08: auto-refresh `load_run` after decision action |

---

## Sources

### Primary (HIGH confidence)

- [VERIFIED: codebase] `apps/voss-app/src-tauri/src/lib.rs` — Tauri command pattern, subprocess shelling (`git_log`), invoke registration
- [VERIFIED: codebase] `apps/voss-app/src/App.tsx` — view toggle pattern, `display: none` isolation, `invoke()` usage
- [VERIFIED: codebase] `voss/harness/board/machine.py` — `Card` dataclass (12 fields), `_COLUMNS`, `_derive_column`, `_derive_risk`
- [VERIFIED: codebase] `voss/harness/board/cli_view.py` — board read-only renderer, column derivation algorithm, card shape `{id, role, risk, status, spent, limit}`
- [VERIFIED: codebase] `voss/harness/board/verdict.py` — `ReviewerVerdict` 7-field shape
- [VERIFIED: codebase] `voss/harness/audit/model.py` — `AuditReport`, `AuditSnapshot`, `AuditCard`, all audit dataclasses
- [VERIFIED: codebase] `voss/harness/audit/render.py` — `render_json()` output shape; `_SECTIONS` (15 sections); `_ALWAYS_MISSING = ("diff_summary", "tests_evals")`
- [VERIFIED: codebase] `voss/harness/audit/report.py` — `build_audit_report()`, `_unsupported_claims()` logic
- [VERIFIED: codebase] `voss/harness/audit/load.py` — transition shape extraction, `.review.json` sidecar format
- [VERIFIED: codebase] `voss/harness/session_tree.py` — `SessionTreeNode` schema, `export_tree()` output `{root_id, nodes}`
- [VERIFIED: codebase] `voss/harness/em/tickets.py` — `RunFinal` 10-field shape + `sign_off` superset
- [VERIFIED: codebase] `voss/harness/cli.py` — `review_cmd` (sidecar format), `audit_cmd` (`--format json` flag), `board_cmd`, `session_tree_cmd`
- [VERIFIED: codebase] `apps/voss-app/vitest.config.ts` — `environment: jsdom`, include pattern, solidPlugin
- [VERIFIED: codebase] `.voss/sessions/` — flat session records confirm dual-layout pitfall
- [VERIFIED: codebase] `apps/voss-app/src/components/StatusBar.tsx` — existing Org toggle button location (right side; new `Org` button goes in left region per UI-SPEC)
- [VERIFIED: codebase] `apps/voss-app/package.json` — dependency inventory (no new packages needed)

### Secondary (MEDIUM confidence)

- V11-CONTEXT.md decisions D-01..D-08 — implementation decisions
- V11-UI-SPEC.md — panel layout contracts, token system, interaction contracts
- V11-SPEC.md — VADE requirements, acceptance criteria

---

## Metadata

**Confidence breakdown:**
- Upstream JSON contracts: HIGH — all shapes verified from live Python source files
- Tauri command pattern: HIGH — verified from `lib.rs` with multiple examples
- SolidJS patterns: HIGH — verified from `App.tsx`, `sync.ts`, existing tests
- TS type shapes: HIGH — derived from verified Python dataclasses
- Vitest setup: HIGH — verified from `vitest.config.ts`
- Diff panel limitation: HIGH — `_ALWAYS_MISSING` hardcoded in `audit/report.py`
- Replay reducer: MEDIUM — data shapes verified; reducer algorithm is new code

**Research date:** 2026-06-07
**Valid until:** 2026-07-07 (stable internal contracts — no external dependencies to drift)
