# Phase V14: ADE Run Cockpit (Integrated Redesign + Live Data Unification) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-08
**Phase:** V14-ade-run-cockpit-integrated-redesign-live-data-unification
**Areas discussed:** Cockpit layout & old-tab fate, RunCommandBar placement & visibility, AttentionQueue surfacing, Cross-surface selection behavior

---

## Cockpit layout & old-tab fate

| Option | Description | Selected |
|--------|-------------|----------|
| Cockpit-only; tabs removed | Cockpit is the single Run Review surface; `ORG_TABS`/`activeTab` deleted; panel bodies become drawer/rail sections | ✓ |
| Cockpit default + tabs as escape hatch | Cockpit default, toggle reveals legacy 10-tab view | |
| Keep tabs, add cockpit as 11th view | Least disruptive, cockpit one more tab | |

**User's choice:** Cockpit-only; tabs removed (Recommended)
**Notes:** Cleanest, matches research thesis, avoids maintaining two layouts. Replay/Audit reachable as drawer/rail sections.

---

## RunCommandBar placement & visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Always-on top strip, both views | Persistent bar in Live Work + Run Review; AgentSidebar Quick-Launch coexists | ✓ |
| ⌘K palette-invoked | Bar appears on ⌘K, dismisses after start | |
| Top strip in Live Work only | Intake only where runs start; review is review-only | |

**User's choice:** Always-on top strip, both views (Recommended)
**Notes:** Warp universal-input style; visible intake aligns with SPEC "no hidden mode". Quick-Launch stays as the fast per-CLI spawn path.

---

## AttentionQueue surfacing

| Option | Description | Selected |
|--------|-------------|----------|
| StatusBar pill + dockable panel | Count pill (reuses agent-pill pattern) opens dockable queue; blocking items pulse the pill | ✓ |
| Toast/banner stream | Transient toasts + banner for blocking items | |
| Permission modal (blocking) + quiet log | Hard modal for permission/sign-off, rest in a log | |

**User's choice:** StatusBar pill + dockable panel (Recommended)
**Notes:** Non-modal, always-available, escalates via pulse only when blocking. Global aggregator — does not replace the existing per-pane permission modal in the live grid.

---

## Cross-surface selection behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Stay in cockpit, inline pane peek | Detail drawer shows read-only live-pane tail + opt-in "Open in grid" button | ✓ |
| Jump straight to grid pane | Card click flips `orgViewOpen`, focuses PTY pane immediately | |
| Modal pane overlay | Card click opens live pane in a modal over cockpit | |

**User's choice:** Stay in cockpit, inline pane peek (Recommended)
**Notes:** Preserves cockpit context; jump-to-grid is opt-in. Detail drawer persistent with a no-selection empty state. Single global `selectedCard` store drives all regions.

---

## Agent spawn & adopt (mockup session, 2026-06-08 — added VCKP-11/12)

Driven by interactive review of throwaway HTML mockups (since removed). Established that ad-hoc terminal spawn and Voss orchestration are peers, joined by an adopt flow.

**Ad-hoc spawn — is it an option, or only orchestration?** → Both, by design. Ad-hoc = first-class (Path 1); orchestration opt-in (Path 2). Quick-launch modal redesigned **sparse/premium**: preset+default-model, one optional prompt, dir/pane — dropped raw-command field + explainer per operator feedback ("simpler, premium, default to the user's CLI command"). → **VCKP-11**.

**Can a user adopt a running ad-hoc agent into the cage?** → Yes — "Manage with Voss" flow. → **VCKP-12**. Copy rewritten to plain language per operator feedback ("not user-friendly… jargon"): "Let Voss manage this agent / Add it to / As the task / Limits / From now on, Voss will…" → CTA "Hand to Voss". Outcomes not mechanics.

**Can adoption truly cage an external CLI?** → No (builder-surfaced limit). PTY-only visibility ⇒ no per-tool gate for external agents; adoption = cost/transcript-audit/budget-monitor/review/advisory-scope. Locked as honest scope; adopt copy must not overpromise.

**Keep pre-adoption work or re-run clean?** → Keep running work; mark audit `partial_lineage`. Re-run-clean alternative considered, deferred.

**Role/Risk on adopt** → pre-inferred but editable; visible by default.

---

## Claude's Discretion

- id-bridge correlation mechanism (card id → live `paneId`/`sessionNodeId`) — keystone technical risk, researcher resolves.
- Adapter shapes + selection-store implementation — planner, matching `org/orgStore.ts` signal style.
- Cockpit CSS/region sizing + collapse — within A12 Ignite tokens.
- Roster IA (native team + swarm + external terminal grouping) — planner; default sectioned single roster.
- Gate bar field set + card-vs-run reactivity — planner.

## Deferred Ideas

- Freeform/Studio investigation canvas — future phase.
- Embedded browser / VerificationArtifact panel — needs webview infra; future phase.
- Replay rollback / re-run — out; replay inspect-only.
- Reject/Unblock full write actions — blocked on harness write path; VCKP-09 best-effort only.
- Custom board columns — columns stay the orchestrator state machine.
