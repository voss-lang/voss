---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 01
type: summary
wave: 1
status: complete
depends_on: ["V14-00"]
requirements: [VCKP-01]
---

# V14-01 Summary — VCKP-01 Data Layer + Selection

Status: **COMPLETE**. Both tasks green. `src/org`: 60 passed | 8 todo | 0 fail. `tsc --noEmit` clean. adapters.ts pure (no solid-js/produce/structuredClone).

## Artifacts

Task 1 (buildModel adapter):
- `src/org/model/adapters.ts` — PURE module. Exports:
  - `buildModel(snapshot: RunData | null, liveAgents: AgentEntry[], budgets: Record<string,BudgetEntry>, bridge: CardBridge): Run` — cards from `cardsFromRunData(snapshot)` spine, `.map` overlay: sessionNodeId=card.id, paneId=bridge.paneIdForCard(id), liveBudget=budgets[paneId].cost_usd, liveStatus from registry status / budget freshness. Null-tolerant. Hand-built immutable literals.
  - `registryToAgents(liveAgents, budgets): Agent[]` — roster overlay projection.
  - Local `AgentEntry` interface (no TS type ships for `get_active_agents` shape) + `CardBridge` resolver interface (plan-02 bridge will satisfy it; not imported here to avoid cross-wave dep).
  - Imports: type-only `RunData` from ../types, `BudgetEntry` from ../../pane/budgetRegistry, `cardsFromRunData` from ../boardDerive, `Card/Agent/Run` from ./normalized. No edits to RunData/guards.ts (D-02 intact).
- `src/org/model/__tests__/adapters.test.ts` — flipped 6 plan-00 it.todo → active; 8 tests pass. Merged card C1 asserts snapshot (title/role/risk/column) AND overlay (paneId='P1', liveBudget=0.42, liveStatus='running') from ONE buildModel call; unbound card retains snapshot + sessionNodeId===id; null → empty Run no throw.

Task 2 (selection):
- `src/org/__tests__/selection.test.tsx` — two independent surfaces (SurfaceA/B) read module-level `selectedCardId()`; one `setSelectedCardId('C1')` call → both observe 'C1'. afterEach resets global signal to null (prevents module-state leak). Mirrors boardPanel.test.tsx harness (uses `solid-js/web` render, NOT @solidjs/testing-library — plan text was wrong about the in-repo style).

## Decisions / notes for downstream

- **Shape adaptation:** `cardsFromRunData` returns BoardCard `{id,title,role,risk,column,spent,limit}`; normalized Card nests `budget:{limit,spent}` + has `scope`. buildModel maps spine→Card, sets budget object, uses card title as `scope` (BoardCard folds node `scope ?? id` into title; no separate scope field upstream).
- **Purity-gate quirk (acted on):** plan's literal gate `grep -L "solid-js\|produce\|structuredClone"` also matches the *header comment* text — boardDerive.ts has the same false-positive. T1 reworded adapters.ts header to "no reactive-store cloning helpers" so the gate passes while preserving meaning. Real-import check confirms zero solid-js imports / zero produce/structuredClone calls.
- **registryToAgents** reads `budget?.model` from BudgetEntry — tsc clean, so BudgetEntry carries `model`. Agent.role/permissionMode left '' (registry has no role/permission data; filled later waves).
- **CardBridge param contract:** `{ paneIdForCard(cardId): string | undefined }`. Plan 02 bridge must satisfy this. buildModel takes resolver as param — no import of ../bridge (avoids wave-1→wave-2 dependency).

## Verification
- `npx vitest run src/org` → 60 passed | 8 todo | 0 fail (12 files passed, 1 skipped).
- `npx vitest run src/org/__tests__/guards.test.ts` → 3 passed (D-02 unregressed).
- `npx tsc --noEmit` → clean.
- Purity: real-import grep confirms adapters.ts has no solid-js/produce/structuredClone.
