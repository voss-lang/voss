---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 03
type: summary
wave: 2
status: complete-with-gap
depends_on: ["V14-00", "V14-01"]
requirements: [VCKP-05]
---

# V14-03 Summary — VCKP-05 Integrated Cockpit

Status: **COMPLETE (one partial vs must-have — see Gap)**. `src/org`: 68 passed | 4 todo | 0 fail. tsc clean. Tab shell removed; 4-region cockpit renders; panels reused verbatim; A12 tokens only.

## Artifacts

Task 2 (leaf components):
- `src/org/cockpit/CardDrawer.tsx` — persistent drawer, default export, props `{ data?: RunData|null }` (optional; falls back to runData()). Reads selectedCardId()/runData() globals. Composes EXISTING panels verbatim (D-02): AuditPanel, VerdictPanel, DiffPanel(data,selectedCardId,onCardSelect), ScopePanel, BudgetPanel, BlockedPanel. No-selection empty state (D-08) via `<Show fallback>`. D-07 stub: read-only pane-peek + disabled "Open in grid" placeholder (orgViewOpen flip deferred to plan 08; disabled-with-reason when no bound pane via paneIdForCard from bridge).
- `src/org/cockpit/GateBar.tsx` — bottom bar, props `{ data?, liveCard? }`. Envelope {limit,spent} from snapshot SessionTreeNode matched by selectedCardId; budgetColor(pct) thresholds COPIED from BoardPanel:24-30 (helper unexported); scope chip + unsupported-claims count from AuditReport.unsupported_claims. Per-card confidence LIVE-only (liveCard.liveStatus), never from RunData. var(--font-mono) numerics.

Task 1 (shell):
- `src/org/cockpit/CockpitShell.tsx` — default export, props `{cwd, cliBinary, onClose}`. LIFTED verbatim from OrgViewShell: onMount auto-load (enumerateRuns→loadRun), pickRun/pickerOpen run-picker, keydown/click onCleanup, loading/error `<Show>` wrappers. Tab machinery dropped. CSS-grid 4 regions: board spine (BoardPanel data/onCardSelect=setSelectedCardId/selectedCardId), `<CardDrawer/>`, rail (SessionTreePanel+ReplayPanel), `<GateBar/>`. Shell aria-label "Run cockpit"; region labels "Board spine"/"Card detail"/"Timeline and replay"/"Gate bar".
- `src/org/cockpit/cockpitStyles.css` — grid-template-areas 'board drawer rail' / 'gate gate gate'. Only existing A12 tokens (--bg-*, --fg-*, --border); zero new --xxx.
- `src/org/OrgViewShell.tsx` — reduced to thin wrapper `<CockpitShell {...props}/>`. Removed ORG_TABS, activeTab, tab bar, per-tab `<Show>`, orphaned panel/import. Kept `import './orgStyles.css'` (shared classes/tokens still needed by panels).

Task 3 (test + obsolete-test cleanup):
- `src/org/cockpit/__tests__/cockpit.test.tsx` — renders CockpitShell with fixture run (card C1, envelope 145000/200000, 2 unsupported claims). Mocks Tauri invoke (enumerate_runs/load_run) like orgView.test.tsx. ONE setSelectedCardId('C1') drives assertions on all 4 regions. afterEach resets selection.
- `src/org/__tests__/orgView.test.tsx` — updated 2 obsolete tab tests (broke by design, D-01 removed tabs): aria-label 'Org/Run view'→'Run cockpit'; `[role=tab].length` 10→0; replaced tab-label-list test with 4-region presence assertion. Grid-stays-mounted intent (Pitfall 6) preserved.

## Wiring path
**OrgViewShell wraps CockpitShell** (lower churn). App.tsx mounts `<OrgViewShell>` under `<Show when={orgViewOpen()}>` at App.tsx:1264; keeping the named OrgViewShell leaves App.tsx + ⌘⇧O toggle + orgView.test.tsx import path untouched.

## GAP vs must-have (truth #1) — timeline rail not selection-reactive
Plan truth #1: one selection should "scroll the timeline rail to C1's node." **Current state: 3 of 4 regions are selection-driven (Board highlight, drawer content, gate bar envelope). The rail (SessionTreePanel) RENDERS C1's node but does NOT scroll/highlight on global selectedCardId** — SessionTreePanel keeps independent LOCAL selection and takes only `data`. Wiring it to global selection requires editing SessionTreePanel, which conflicts with D-02 (reuse-not-rewrite verbatim). Test asserts the weaker true claim (C1's node present/referenced in rail).
- Decision needed: either (a) accept rail as passive-render (panels stay verbatim per D-02) and amend truth #1, or (b) a later plan adds a thin global-selection→rail-scroll adapter without rewriting SessionTreePanel internals. Flag for plan 08 (wiring) or a follow-up.

## Verification
- `npx vitest run src/org` → 14 files, 68 passed | 4 todo | 0 fail.
- `npx vitest run src/org/__tests__` → 50 passed (orgView fixed, V11 panels + guards green; D-02 unregressed).
- `npx tsc --noEmit` → clean.
- OrgViewShell: no ORG_TABS/activeTab. cockpitStyles.css: no new tokens. Grid/⌘⇧O untouched.
