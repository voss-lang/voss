---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 05
type: summary
wave: 3
status: complete
depends_on: ["V14-02", "V14-03"]
requirements: [VCKP-04, VCKP-13b]
---

# V14-05 Summary — VCKP-04 Global AttentionQueue + VCKP-13b proxy route

Status: **COMPLETE**. Whole suite: 645 passed | 4 todo | 0 fail. tsc clean. Pill+panel purely additive.

## Artifacts

Task 1 (aggregator):
- `src/org/attention/attentionQueue.ts` — module-level `createSignal<AttentionItem[]>([])`, dedup'd immutable updates (mirror budgetRegistry; no produce/structuredClone).
  - `AttentionItem { id, kind, cardId?, sessionNodeId?, summary, deepLink:{paneId?,sessionNodeId?}, tool?, args?, dimension?, affectedPath?, actions?: PermissionAction[], value?, limit? }`. Kinds: permission|budget|confidence|idle|gate|signoff|blocked|unsupported.
  - `ingestEvent(ev: AgentEvent, ctx?: {cardId?, adopted?}): AttentionItem | null` — maps SSE events; deepLink via resolveCard.
  - `ingestSnapshotDecisions(runData)` — Blocked column + RunFinal.sign_off + unsupported_claims → items.
  - `normalizeCliPermission(raw PreToolUse) → permission AgentEvent` — VCKP-13b proxy normalizer; routes through ingestEvent (NO separate path).
  - `permissionActionsFor(adopted)` — [] for tier-C adopted (Pitfall 6, no per-tool gating copy); else allow-once/allow-scoped/deny.
  - `attentionQueue()` signal getter; `__resetAttentionQueue()` test-only.
- `src/org/attention/__tests__/attentionQueue.test.tsx` — 5 tests: 3-item deep-link, permission fields+actions, dedup, VCKP-13b PreToolUse routing.

Task 2 (surface):
- `src/org/attention/AttentionPanel.tsx` — dockable NON-modal panel (no backdrop). `<For>` over attentionQueue(); each row: kind badge (permission/signoff tinted --focus), summary, "Focus" deep-link → setSelectedCardId(cardId ?? deepLink.sessionNodeId), permission meta (tool·dimension·affectedPath), action buttons from item.actions (none when empty → tier-C). onPermissionAction(item,action) stub prop (backend resolution out of scope).
- `src/org/attention/attentionPanel.css` — A12 tokens only. `.attn-pill--pulse` + `@keyframes attn-pulse` + `@media (prefers-reduced-motion:reduce)` disable (plan-12 gate target). Panel never pulses; pill does.
- `components/StatusBar.tsx` — new props attentionCount/attentionBlocking/onToggleAttention (mirror agentCount). Count pill bound to count, reuses agent-pill markup; pulse class when blocking; click → onToggleAttention. Presentational only.
- `App.tsx` — `attentionOpen` signal + `attentionBlocking` memo (kind permission|signoff); wired 3 StatusBar props + `<AttentionPanel open onClose>`.
- `src/org/__tests__/orgView.test.tsx` — added 3 new (inert) props to its direct StatusBar render (forced by required-prop addition).

## Decisions / notes for downstream

- **SSE field reality:** SDK uses `session_id` (snake) on budget/confidence/gate/idle. **permission.updated carries NO session field** — shape `{id, tool_name, args, dimension}` (PROTOCOL §6/§7). So permission item cardId comes from `IngestContext.cardId` (the live-grid binding), NOT the event. **No `affected-path` on the wire** — affectedPath derived best-effort from args (path/file_path/filePath/cwd/target). This best-effort derivation is the honest VCKP-13b tier — tier-B sandbox floor when no hook fires.
- **Open/close state in App.tsx** (mirrors orgViewOpen/contextPanelOpen); StatusBar stays presentational.
- **Live-grid per-pane permission modal:** D-06 "unchanged" holds trivially — no such component exists yet. Global pill/panel is additive only. When the per-pane modal lands, this queue is the AGGREGATOR, not a replacement.
- **Permission action buttons are UI-only stubs** (onPermissionAction); actual allow/deny backend resolution is a future plan.

## Verification
- `npx vitest run src/org/attention/__tests__/attentionQueue.test.tsx` → 5 passed.
- `npx vitest run src/org` → 16 files, 81 passed | 4 todo.
- `npx vitest run` (whole) → 71 files, 645 passed | 4 todo | 0 fail.
- `npx tsc --noEmit` → clean.
- VCKP-13b PreToolUse payload routes through ingestEvent → permission item (tool=Edit, affectedPath=/proj/app.py). Best-effort; tier-B fallback documented.
