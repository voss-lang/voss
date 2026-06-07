---
phase: V11
slug: ade-org-integration
status: draft
shadcn_initialized: false
preset: none
created: 2026-06-07
---

# Phase V11 — UI Design Contract

> Visual and interaction contract for Phase V11: ADE Org Integration.
> Produced by gsd-ui-researcher. Verified by gsd-ui-checker.

---

## Design System

| Property | Value | Source |
|----------|-------|--------|
| Tool | none — custom CSS vars via theme catalog | A12 precedent |
| Preset | not applicable | project convention |
| Component library | none — SolidJS + hand-rolled components | existing codebase |
| Icon library | Unicode glyphs + inline SVG | A12 precedent |
| Font: Display | Poppins 500/600 (bundled locally in `public/fonts/`) | A12-UI-SPEC |
| Font: UI | Inter (already loaded) | A12-UI-SPEC |
| Font: Terminal / Code | JetBrains Mono (already loaded) | A12-UI-SPEC |
| Active theme | Voss Ignite (`voss-ignite.json`) | A12 ADE visual direction |

**No shadcn.** This is a Tauri/SolidJS app with a custom theme catalog. The shadcn gate is not applicable.

**V11 extends A12.** This spec does not redefine the token system — it references A12 tokens directly and declares only V11-specific additions (org-panel column status colors, board card risk tints, unsupported-claim flag color). If this spec and A12-UI-SPEC conflict, A12-UI-SPEC governs the shared chrome (sidebar, StatusBar, ContextPanel, titlebar). V11 governs the Org/Run view shell and all 10 org panels.

---

## Token Reference: Voss Ignite (inherited — do not redefine)

All V11 components must use CSS variables. No raw hex in component code.

### Background Scale (from A12 / voss-ignite.json)

| Variable | Value | Usage |
|----------|-------|-------|
| `--bg-0` | `#0b0a09` | App background, Org/Run view outer shell |
| `--bg-1` | `#131110` | Sidebar surface, panel header rows |
| `--bg-2` | `#1a1714` | Panel body surface, card backgrounds, table rows |
| `--bg-3` | `#221f1b` | Confirmation dialog, drilldown overlay, run-picker dropdown |

### Foreground Scale (from A12)

| Variable | Value | Usage |
|----------|-------|-------|
| `--fg-0` | `#f5f1ea` | Card titles, panel section headings, dialog body text |
| `--fg-1` | `#c4beb5` | Role labels, column headers, tree node names |
| `--fg-2` | `#8a847a` | Secondary metadata (budget %, timestamps, step counter) |
| `--fg-3` | `#5a554d` | Empty state labels, dividers, inactive scrubber marks |

### Border (from A12)

| Variable | Value | Usage |
|----------|-------|-------|
| `--border` | `#1d1a16` | Panel borders, table row separators, column dividers |
| `--border-bright` | `#2e2924` | Focused panel header border, hover ring on cards |

### Focus / Accent (from A12)

| Variable | Value | Usage |
|----------|-------|-------|
| `--focus` | `#ff5b1f` | Selected card border, active run-picker item, refresh button |
| `--focus-glow` | `rgba(255,91,31,0.18)` | Focus glow on selected card |
| `--focus-soft` | `rgba(255,91,31,0.14)` | Focused panel header background tint |

### Semantic Accent Palette (from A12 — reserved uses)

| Variable | Value | Reserved For |
|----------|-------|-------------|
| `--accent-green` | `#5ec26a` | Board column "Done", reviewer-verdict PASS, budget OK (< 70%) |
| `--accent-amber` | `#e8b86c` | Board column "In Review" / "Review Needed", budget warning (70–90%), risk tier "med" |
| `--accent-red` | `#e87b7b` | Board column "Blocked", budget critical (> 90%), risk tier "high", unsupported EM-claim flag, destructive actions |
| `--accent-cyan` | `#6cc7d4` | Board column "In Progress", diff additions |
| `--accent-magenta` | `#c084d4` | Reviewer-B verdict label, diff modifications |
| `--accent-blue` | `#7aa2ff` | Replay step indicator, session-tree navigation arrow |

### Role Colors (from A12 — extend for org roles)

| Variable | Value | Usage |
|----------|-------|-------|
| `--role-planner` | `#ff5b1f` | Planner/PM role tag in roster + board cards |
| `--role-executor` | `#6cc7d4` | Executor/Backend/Frontend/QA role tag |
| `--role-reviewer` | `#e8b86c` | Reviewer-A and Reviewer-B role tag |
| `--role-watcher` | `#8a847a` | Passive/observer role tag |
| `--role-user` | `#5ec26a` | User / root-session indicator in session tree |

### V11-Specific Token Additions

These extend A12 and must be declared in the V11 org-panel component scope (not in `variant-b.css` — those are phase-level extensions applied in V11 component CSS):

| Variable | Value | Usage |
|----------|-------|-------|
| `--org-col-backlog` | `var(--fg-3)` | Board column header: Backlog |
| `--org-col-todo` | `var(--fg-2)` | Board column header: Todo |
| `--org-col-in-progress` | `var(--accent-cyan)` | Board column header: In Progress |
| `--org-col-in-review` | `var(--accent-amber)` | Board column header: In Review |
| `--org-col-done` | `var(--accent-green)` | Board column header: Done |
| `--org-col-blocked` | `var(--accent-red)` | Board column header: Blocked |
| `--unsupported-flag` | `var(--accent-red)` | Unsupported EM-claim flag in audit panel |
| `--card-risk-low` | `rgba(94, 194, 106, 0.08)` | Board card background tint: low risk |
| `--card-risk-med` | `rgba(232, 184, 108, 0.08)` | Board card background tint: med risk |
| `--card-risk-high` | `rgba(232, 123, 123, 0.10)` | Board card background tint: high risk |

---

## Spacing Scale

8-point base. All values must be multiples of 4. From A12 — unchanged.

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps, status dot spacing, inline badge padding |
| sm | 8px | Card inner padding, panel header padding, column padding |
| md | 16px | Panel body padding, section spacing, replay control padding |
| lg | 24px | Dialog body padding, panel-group gap |
| xl | 32px | Dialog outer padding |
| 2xl | 48px | — reserved |
| 3xl | 64px | — reserved |

**V11 exceptions:**
- Board card height: 64px minimum (enough for title + role + risk + status in 3 lines at 11px mono with 4px gaps).
- Session-tree indent per level: 16px (matches file-tree indent × 1.33 for deeper nesting up to 8 levels).
- Replay scrubber height: 32px touch-target (contains back/forward buttons and step counter).
- Org/Run view mode toggle button: 28px height (matches `--pane-header-height`).
- Budget bar in org context: 4px height (matches existing `BudgetBar` component pattern).
- Run-picker dropdown max-height: 240px with overflow-y scroll.

---

## Typography

All from A12 — inherited directly. No new tiers for V11.

| Role | Font | Size | Weight | Line Height | Usage |
|------|------|------|--------|-------------|-------|
| Display | Poppins | 14px | 500 | 1.2 | Org/Run view header, panel section titles |
| Display large | Poppins | 16px | 600 | 1.2 | Confirmation dialog title only |
| UI body | Inter | 12px | 400 | 1.5 | Sidebar agent names, roster entries, run-picker items |
| UI label | Inter | 11px | 500 | 1.4 | Buttons, badges, board column headers, role pills, run-picker |
| Mono body | JetBrains Mono | 11px | 400 | 1.5 | Card IDs, budget values, token counts, timestamps, CLI command preview in dialog, step counter, diff line numbers |
| Section heading | Poppins | 11px | 600 | 1.2 | Uppercase panel section labels (ROSTER, BOARD, AUDIT, etc.) |

Section heading labels: uppercase, `letter-spacing: 0.08em`.

---

## Color

60/30/10 split — inherited from A12.

| Role | Value | Usage |
|------|-------|-------|
| Dominant 60% | `#0b0a09` (`--bg-0`) | Org/Run view background, panel outer shell |
| Secondary 30% | `#131110` / `#1a1714` (`--bg-1/2`) | Panel surfaces, board column areas, dialog body, run-picker |
| Accent 10% | `#ff5b1f` (`--focus`) | See reserved-for list below |
| Destructive | `#e87b7b` (`--accent-red`) | Reject action, unsupported claim flag, Blocked column, high-risk tint, critical budget |

**V11 accent reserved-for (additions to A12 list — do not use `--focus` for any other element):**
1. Selected board card border (1px `--focus`)
2. Active run-picker item background highlight (`--focus-soft`)
3. "Refresh" button icon/label color
4. Replay scrubber active step dot fill
5. Confirmation dialog CLI command text highlight (monospace block border-left: 2px `--focus`)
6. Active panel tab underline (if panel tabs are used)

All other interactive elements in panels use foreground scale (`--fg-1`, `--fg-2`) with hover tints from `--bg-2` only.

---

## Org/Run View — Shell Layout

The Org/Run view is a new top-level view mode that replaces the GridRoot area when active. It does not destroy the grid; toggling back restores it exactly.

```
┌─────────────────────────────────────────────────────────┐
│ Titlebar                                       38px     │
├─────────────────────────────────────────────────────────┤
│ WorkspaceTabBar                                32px     │
├──────────────┬──────────────────────────────────────────┤
│ AgentSidebar │  OrgViewShell                           │
│ 280px fixed  │  ┌──────────────────────────────────┐   │
│ (unchanged)  │  │ OrgViewHeader                28px │   │
│              │  │  [← Grid]  Run: run-id ▾  [↻]    │   │
│              │  ├──────────────────────────────────┤   │
│              │  │ PanelTabBar                  36px │   │
│              │  │  Roster│Board│Tree│Audit│…  │     │   │
│              │  ├──────────────────────────────────┤   │
│              │  │ ActivePanelArea            flex:1 │   │
│              │  │ (one of 10 panels)               │   │
│              │  └──────────────────────────────────┘   │
├──────────────┴──────────────────────────────────────────┤
│ StatusBar                                      26px     │
└─────────────────────────────────────────────────────────┘
```

**OrgViewShell:** fills the space normally occupied by `GridRoot`. Background `--bg-0`. `flex-direction: column`. The `AgentSidebar` and `StatusBar` remain mounted and unchanged.

**OrgViewHeader (28px, matches `--pane-header-height`):**
- Left: `← Grid` text button (Inter 11px 500 `--fg-2`, hover `--fg-0`) — returns to grid view without disturbing pane layout.
- Center: Run label + run-picker trigger. Format: `Run: <run_id_short>` followed by a `▾` glyph. Run ID truncated to 12 chars with ellipsis. Entire element is a button (Inter 11px 500 `--fg-1`). Click opens the run-picker dropdown.
- Right: Refresh button — `↻` Unicode glyph (U+21BB) + `Refresh` label (Inter 11px 500 `--fg-2`). Triggers `load_run` re-call. While loading: glyph rotates via CSS animation `spin 0.8s linear infinite`; button disabled.
- Background: `--bg-1`. Border-bottom: `1px solid --border`.

**PanelTabBar (36px):**
- 10 tabs: Roster / Board / Tree / Audit / Verdict / Budget / Scope / Diff / Blocked / Replay
- Tab style: Inter 11px 500. Active: `--focus` 2px bottom underline + `--fg-0`. Inactive: `--fg-2`. Hover: `--fg-1`.
- Scroll-overflow: horizontal scroll if viewport < 10 tabs × tab width. No wrapping.
- Background: `--bg-1`. Border-bottom: `1px solid --border`.
- Tab labels exactly: `Roster` / `Board` / `Tree` / `Audit` / `Verdict` / `Budget` / `Scope` / `Diff` / `Blocked` / `Replay`.

**ActivePanelArea:** `flex: 1`, `overflow-y: auto`, `background: --bg-0`.

**Run-picker dropdown:**
- Positioned below the run label trigger, `--bg-3` background, `1px solid --border-bright`, `border-radius: 0` (panel style).
- Max-height: 240px, overflow-y scroll.
- Each row: run_id (JetBrains Mono 11px `--fg-0`) + status badge + mtime (JetBrains Mono 11px `--fg-3`). Height: 28px per row.
- Active/selected row: `--focus-soft` background, `--fg-0` text.
- Hover: `--bg-2` background.
- Closes on Escape and on outside click.
- Empty state: "No runs found" (Inter 12px `--fg-3`, centered, 40px height).

---

## Panel Contracts

### View-Level States (all panels share)

**Loading state (initial `load_run` call):**
- OrgViewShell shows a centered spinner: `⟳` glyph rotating CSS `spin 0.8s linear infinite`, `--fg-2` color, 16px. No text. Refresh button disabled and spinning.

**Error state (invalid/missing run):**
- Centered in `ActivePanelArea`: Heading `Run not found` (Poppins 14px 500 `--fg-0`). Body: `The run "{run_id}" could not be loaded. Check that the run ID is valid and try refreshing.` (Inter 12px 400 `--fg-2`, max-width 320px, text-align center). Below: `Refresh` button (Inter 11px 500 `--fg-2`, transparent background, `1px solid --border`).

**Per-panel "no data" state** (run loaded but panel source absent):
- Centered in panel body: `No {panel-name} data for this run.` (Inter 12px `--fg-3`). No action button.

---

### Panel 1: Roster

Displays the team roster — agent roles, names, and assignments for the loaded run.

**Layout:** Vertical list. Each row: 36px height.

**Row anatomy:**
- Left: role-color dot (7px × 7px, `border-radius: 50%`, role color variable).
- Role label: Inter 11px 500 `--fg-1`, uppercase, truncated.
- Agent name / model: JetBrains Mono 11px `--fg-2`.
- Right: status badge (see below).

**Status badges:** pill shape (`border-radius: 9999px`, padding 0 6px, height 16px, Inter 11px 500).
- `active` → `--accent-green` text, `rgba(94,194,106,0.12)` background.
- `idle` → `--fg-3` text, `--bg-2` background.
- `done` → `--fg-3` text, `--bg-2` background.

**Section header:** Poppins 11px 600 uppercase `--fg-3` `letter-spacing: 0.08em`, padding 8px 16px 4px.

**Empty state:** "No roster data for this run." (Inter 12px `--fg-3`, centered).

---

### Panel 2: Board

Displays the 6-column Kanban board from `voss board` output.

**Column layout:** Horizontal flex, 6 equal-width columns. Each column scrolls independently (`overflow-y: auto`).

**Column header (32px):**
- Column name in the column's status color (see `--org-col-*` tokens). Poppins 11px 600 uppercase `letter-spacing: 0.08em`.
- Card count: JetBrains Mono 11px `--fg-3` `(N)`.
- Column divider: `1px solid --border`.
- Order: Backlog / Todo / In Progress / In Review / Done / Blocked.

**Card (minimum 64px, variable height):**
- Background: `--bg-2` + risk tint (`--card-risk-low/med/high`).
- Border: `1px solid --border`. No border-radius (variant-b rule).
- Selected card: `1px solid --focus`, `box-shadow: 0 0 0 1px --focus`.
- Margin-bottom: 4px.
- Inner padding: 8px.

Card contents (top-to-bottom):
1. Card ID: JetBrains Mono 11px `--fg-3` (e.g. `card-0042`).
2. Card title: Inter 12px 400 `--fg-0`, 2-line clamp (`overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2`).
3. Role pill: Inter 11px 500, role color at 20% opacity background, role color text, `border-radius: 3px`, padding 0 4px.
4. Risk badge: pill, `border-radius: 9999px`, padding 0 6px. Low → `--accent-green` tint; Med → `--accent-amber` text `--bg-2` background; High → `--accent-red` text `--bg-2` background.
5. Budget micro-bar: 4px height bar (matches `BudgetBar` pattern). `--accent-green` < 70%, `--accent-amber` 70–90%, `--accent-red` > 90%. Width fills card, no label.

Click on a card: selects it (focus ring) and navigates the Diff panel to show that card's diff. No other navigation change on click.

**Empty column:** "No cards" text (Inter 11px `--fg-3`, centered, 24px top margin).

---

### Panel 3: Session Tree

Displays the parent→child session tree, navigable.

**Layout:** Vertical scrollable tree. Root nodes at left margin.

**Tree node row (28px):**
- Indent: 16px per level.
- Expand/collapse toggle: `▸` (collapsed) / `▾` (expanded) — JetBrains Mono 11px `--fg-3`. Leaf nodes: `●` dot (4px, `--fg-3`).
- Session ID: JetBrains Mono 11px `--fg-1`, truncated at 20 chars with ellipsis.
- Role badge: same as Roster pill style but 10px font.
- Status dot: 6px circle, `--accent-green` (done) / `--accent-amber` (in-review) / `--accent-red` (error/blocked) / `--fg-3` (idle).
- Right: cost — JetBrains Mono 11px `--fg-3`.
- Hover: `--bg-2` background.
- Selected: `--focus-soft` background + `2px solid --focus` left bar.

Click on node: selects it and shows light metadata below the tree (node ID, role, budget-used, status, parent ID). Metadata area: 72px fixed height, `--bg-1` background, `1px solid --border` top, padding 8px 16px, Inter 12px.

**Empty state:** "No session tree data for this run." (Inter 12px `--fg-3`, centered).

---

### Panel 4: Audit

Renders the V9 audit JSON — §9 sections, claims-vs-evidence, residual-risk.

**Section anatomy:**
Section header row: Poppins 11px 600 uppercase `--fg-3` `letter-spacing: 0.08em`, padding 8px 16px 4px, `border-bottom: 1px solid --border`.

**Claims list:** Each claim is a row (min 32px).
- Claim text: Inter 12px 400 `--fg-1`.
- Evidence badge: pill style. `supported` → `--accent-green` text; `partial` → `--accent-amber` text; `unsupported` → `--accent-red` text.
- **Unsupported EM-claim flag:** When `supported === false` (unsupported), the row additionally shows a `⚑` Unicode flag glyph (U+2691, JetBrains Mono 13px) in `--unsupported-flag` (`--accent-red`) immediately before the claim text. The row background is `rgba(232,123,123,0.06)`. `aria-label="Unsupported claim"` on the flag glyph.

**Residual risk section:** Shown after the §9 sections. Section header: `RESIDUAL RISK`. Content: free-text body in Inter 12px 400 `--fg-1`, padding 8px 16px.

**Empty state:** "No audit data for this run." (Inter 12px `--fg-3`, centered).

---

### Panel 5: Verdict (Reviewer A / Reviewer B)

Displays Reviewer-A and Reviewer-B verdicts separately from `voss review` output.

**Layout:** Two vertical half-panes side-by-side, separated by `1px solid --border`. Each half scrolls independently.

**Half-pane header (28px):**
- Left half: `REVIEWER A` — Poppins 11px 600 `--role-reviewer` + `letter-spacing: 0.08em`.
- Right half: `REVIEWER B` — same style but `--accent-magenta` color to distinguish the two sources.
- Background: `--bg-1`. Border-bottom: `1px solid --border`.

**Verdict body:**
- Verdict label: Inter 12px 500. `PASS` → `--accent-green`; `FAIL` / `BLOCK` → `--accent-red`; `DEFER` → `--accent-amber`.
- Confidence score: JetBrains Mono 11px `--fg-2` (e.g. `conf: 0.84`).
- Domain inferred: JetBrains Mono 11px `--fg-3` (e.g. `domain: code`).
- Narrative/rationale: Inter 12px 400 `--fg-1`, full-width, `white-space: pre-wrap`. Padding: 8px 16px.

**Empty state per half:** "No {Reviewer A/B} verdict for this run." (Inter 12px `--fg-3`, centered).

---

### Panel 6: Budget

Displays budget allocation and consumption: per root / per card / per agent.

**Layout:** Three collapsible sections stacked vertically — `Per Root` / `Per Card` / `Per Agent`. Default: all sections expanded.

**Section header (32px, clickable to collapse):**
- `▾` / `▸` toggle glyph (JetBrains Mono 11px `--fg-3`) + section name (Poppins 11px 600 uppercase `--fg-3` `letter-spacing: 0.08em`).
- Right: total allocated / consumed summary (JetBrains Mono 11px `--fg-2`).

**Budget row (28px):**
- Name: Inter 12px 400 `--fg-1`, truncated.
- Allocation: JetBrains Mono 11px `--fg-2`.
- Consumption bar: 4px height (same `BudgetBar` pattern — `--accent-green` < 70%, `--accent-amber` 70–90%, `--accent-red` > 90%). Width proportional to allocation, fills available space.
- Pct used: JetBrains Mono 11px `--fg-2`.

**Over-budget row highlight:** Row background `rgba(232,123,123,0.06)` when consumption ≥ allocation.

**Empty state:** "No budget data for this run." (Inter 12px `--fg-3`, centered).

---

### Panel 7: Scope

Displays declared vs actual scope: per role and per card.

**Layout:** Two collapsible sections — `Per Role` / `Per Card`.

**Row anatomy (28px):**
- Role/Card name: Inter 12px 400 `--fg-1`.
- Scope items: comma-separated tags in Inter 11px 500 `--fg-2`, 3px radius pill style, `--bg-3` background, 4px horizontal padding.
- Out-of-scope indicator: if a card operated outside declared scope, show `⚑` flag glyph (same as audit, `--accent-red`, `aria-label="Out of scope"`).

**Empty state:** "No scope data for this run." (Inter 12px `--fg-3`, centered).

---

### Panel 8: Diff + Verification Drilldown

Displays the diff and verification result for a specific card. This panel is navigated to either by clicking a board card (Panel 2) or by selecting a card from a picker within this panel.

**Card picker (32px):**
- Positioned at top of panel. Inter 11px 500 `--fg-2` label `Card:` + card ID button (JetBrains Mono 11px `--fg-1`) + `▾`. Click opens dropdown (same style as run-picker).

**Diff view:**
- Monospace diff display. JetBrains Mono 11px 400, `line-height: 1.4`.
- Addition lines: `--accent-cyan` text on `rgba(108,199,212,0.06)` background.
- Removal lines: `--accent-red` text on `rgba(232,123,123,0.06)` background.
- Context lines: `--fg-3` text, `--bg-1` background.
- Line numbers: JetBrains Mono 10px `--fg-3`, right-aligned in a 36px wide column, `border-right: 1px solid --border`.
- Filename header: `--bg-2` full-width row, Inter 11px 500 `--fg-1`, padding 4px 8px.

**Verification result (below diff, separated by `1px solid --border`):**
- Section header: Poppins 11px 600 `VERIFICATION` `--fg-3`.
- Outcome badge: pill. `PASS` → `--accent-green`; `FAIL` → `--accent-red`; `SKIP` → `--fg-3`.
- Test/eval summary: Inter 12px 400 `--fg-1`, `white-space: pre-wrap`.

**No card selected state:** "Select a card to view its diff." (Inter 12px `--fg-3`, centered).
**Card has no diff state:** "No diff recorded for this card." (Inter 12px `--fg-3`, centered).

---

### Panel 9: Blocked — Decision Flow

Lists blocked cards with reasons; decision actions shell the V7/V9 CLI.

**Blocked card list:**
Each row is 72px minimum height.
- Card ID: JetBrains Mono 11px `--accent-red` (blocked color).
- Blocked reason: Inter 12px 400 `--fg-1`, 2-line clamp.
- Action buttons row (right-aligned): `Approve`, `Reject`, `Unblock` — each 28px height, Inter 11px 500, `--bg-2` background, `1px solid --border`, `border-radius: 3px`. Spacing: 4px between buttons.
  - `Approve` text color: `--accent-green`.
  - `Reject` text color: `--accent-red`.
  - `Unblock` text color: `--fg-1`.
- Row separator: `1px solid --border`.
- Hover: `--bg-2` background on the full row.

**Decision confirmation dialog (shared with sign-off):**
- `role="dialog"`, `aria-modal="true"`, `aria-labelledby` → dialog title.
- Background: `--bg-3`. Frame: `1px solid --border-bright`. Width: 480px. No border-radius (panel style).
- Backdrop: `rgba(0,0,0,0.6)`.
- Transition: `opacity 150ms ease-out` + `transform scale(0.96→1.0) 150ms ease-out`. Respects `prefers-reduced-motion`.

Dialog layout:
1. **Header (48px):** Title: `{Action}: {card_id}` — Poppins 600 16px `--fg-0`. Dismiss `×` button top-right (`aria-label="Cancel"`).
2. **CLI preview block:** `--bg-2` background, `border-left: 2px solid --focus`, padding 8px 12px, margin 16px. JetBrains Mono 11px `--fg-0`. Contains the **exact CLI command string** that will be shelled (e.g. `voss approve <run_id> <card_id>`). Label above block: `Command to run:` (Inter 11px 500 `--fg-3`).
3. **Result area (appears after execution):** Initially hidden. On success: `✓ Done` (Inter 12px `--accent-green`) + first 200 chars of stdout (JetBrains Mono 11px `--fg-2`, `white-space: pre-wrap`). On failure: `✗ Failed` (`--accent-red`) + stderr (JetBrains Mono 11px `--fg-2`).
4. **Footer:** Right-aligned. Cancel button (Inter 11px 500 `--fg-2`, transparent, `1px solid --border`, 3px radius) + Confirm button (Inter 11px 500 `--fg-0`, `--focus` background, 3px radius, Poppins 500 style). Confirm button disabled + `opacity: 0.5` while executing.

After success: dialog auto-closes after 1500ms AND triggers `load_run` refresh. User can dismiss early via `×` or Escape.

**Empty state (no blocked cards):** "No blocked cards in this run." (Inter 12px `--fg-3`, centered).

---

### Panel 10: Replay

Steps through the run's persisted transition history to reconstruct board/card state at each step.

**Replay controls bar (32px):**
- Background: `--bg-1`. Border-bottom: `1px solid --border`.
- `‹` Back button (JetBrains Mono 14px `--fg-1`, disabled at step 0 → `--fg-3`).
- Step counter: `Step N / M` (Inter 11px 500 `--fg-2`, min-width 64px, text-align center).
- `›` Forward button (JetBrains Mono 14px `--fg-1`, disabled at final step → `--fg-3`).
- Step event label: description of the transition at the current step (Inter 11px 400 `--fg-2`, left-aligned, truncated, `flex: 1`, margin-left 16px). Example: `card-0042 → In Progress`.
- Active step dot: 6px circle `--focus` fill, immediately left of the step counter.

**Board snapshot area:** Renders the board at step N using the client-side replay reducer output. Uses the exact same board layout as Panel 2, with these differences:
- Non-interactive: card clicks are disabled (no `cursor: pointer`, no focus ring on click). Cards are read-only in replay.
- Replay state badge: `REPLAY` watermark — Inter 10px 500 `--fg-3` positioned in the top-right of the board area, `letter-spacing: 0.12em`.

**Other-panels notice:** Below the controls bar and above the board snapshot: a 24px notice row — `Audit, Verdict, Budget, and Scope panels show final-run state only.` (Inter 11px `--fg-3`, centered). `border-bottom: 1px solid --border`.

**Empty state (no transitions):** "No transition history for this run. Replay requires persisted transitions." (Inter 12px `--fg-3`, centered).

---

## View Toggle Interaction Contract

**Toggling to Org/Run view:**
- Keyboard: `⌘⇧O` (Cmd+Shift+O). Not accessible from `⌘K` command palette in V11 (defer to A7 command registry phase).
- Visual: a toggle button `Org` appears in the StatusBar left region, between workspace info and pane count. Inter 11px 500. Active state: `--focus` text, `rgba(255,91,31,0.15)` background, `1px solid --focus`. Inactive: `--fg-3` text, transparent background. Button padding: 0 6px, height 16px.
- On activation: GridRoot unmounts (or is hidden via `display: none`; implementation at executor's discretion — must restore unchanged). OrgViewShell mounts. Auto-loads most-recent run via D-04 behavior.
- On return: OrgViewShell unmounts (or hidden). GridRoot shown. Grid state is exactly as the user left it.

**Grid does not change while Org/Run view is active.** No PTY panes are affected. The AgentSidebar continues to show live agent data.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| View toggle button | `Org` |
| View toggle keyboard hint | `⌘⇧O` |
| Org view header: back to grid | `← Grid` |
| Org view header: refresh button | `↻ Refresh` |
| Org view header: loading state | (spinner only, no text) |
| Run-picker empty state | `No runs found` |
| Panel tabs (all 10) | `Roster` / `Board` / `Tree` / `Audit` / `Verdict` / `Budget` / `Scope` / `Diff` / `Blocked` / `Replay` |
| View-level error heading | `Run not found` |
| View-level error body | `The run "{run_id}" could not be loaded. Check that the run ID is valid and try refreshing.` |
| View-level loading | (spinner glyph only) |
| Per-panel no-data | `No {panel-name} data for this run.` |
| Blocked panel empty | `No blocked cards in this run.` |
| Diff panel no selection | `Select a card to view its diff.` |
| Diff panel no diff | `No diff recorded for this card.` |
| Replay panel no history | `No transition history for this run. Replay requires persisted transitions.` |
| Session tree no data | `No session tree data for this run.` |
| Replay mode watermark | `REPLAY` |
| Replay notice | `Audit, Verdict, Budget, and Scope panels show final-run state only.` |
| Board card action: approve button | `Approve` |
| Board card action: reject button | `Reject` |
| Board card action: unblock button | `Unblock` |
| Decision dialog title | `{Action}: {card_id}` (e.g. `Approve: card-0042`) |
| Decision dialog CLI label | `Command to run:` |
| Decision dialog confirm button | `Confirm` |
| Decision dialog cancel button | `Cancel` |
| Decision dialog success | `✓ Done` |
| Decision dialog failure | `✗ Failed` |
| Decision auto-close notice | (none — silent auto-close after 1500ms on success) |
| Sign-off action button (if applicable) | `Sign Off` |
| Unsupported claim aria-label | `Unsupported claim` |
| Out-of-scope flag aria-label | `Out of scope` |
| Back button aria-label (replay) | `Previous step` |
| Forward button aria-label (replay) | `Next step` |
| Dismiss dialog aria-label | `Cancel` |

---

## Motion and Transitions

All transitions must include `prefers-reduced-motion: reduce` override setting duration to `0.01ms`.

| Element | Animation | Duration | Easing |
|---------|-----------|----------|--------|
| Org/Run view enter | `opacity` 0→1 | 100ms | `ease-out` |
| Org/Run view exit | `opacity` 1→0 | 80ms | `ease-in` |
| Confirmation dialog appear | `opacity` 0→1 + `transform` scale 0.96→1 | 150ms | `ease-out` |
| Confirmation dialog dismiss | `opacity` 1→0 + `transform` scale 1→0.96 | 100ms | `ease-in` |
| Refresh button spinner | `transform rotate` | 0.8s linear infinite | (while loading) |
| Run-picker dropdown open | `opacity` 0→1 | 100ms | `ease-out` |
| Session tree node expand | `max-height` + `opacity` | 150ms | `ease-out` |
| Budget bar fill change | `width` | 200ms | `ease` |
| Replay scrubber step dot | `background-color` | 80ms | `ease` |
| Decision dialog success auto-close | 1500ms delay, then opacity 1→0 100ms | — | `ease-in` |

---

## Accessibility

- Org/Run view shell: `role="region"`, `aria-label="Org/Run view"`.
- Panel tab list: `role="tablist"`, each tab `role="tab"`, `aria-selected`, panel body `role="tabpanel"`, `aria-labelledby` matching tab id.
- Decision confirmation dialog: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` → dialog title id. Focus trap while open. Focus returns to the triggering action button on close.
- Run-picker dropdown: `role="listbox"`, items `role="option"`, `aria-selected` on current run.
- Session tree: `role="tree"`, each node `role="treeitem"`, `aria-expanded` on expandable nodes.
- Board: column list `role="list"`, each column `role="listitem"`, card list within each column `role="list"`, each card `role="listitem"`. Cards are not interactive controls (read-only display) — use `div`, not `button`, except in replay where they are disabled.
- Replay controls: Back/Forward buttons `aria-label="Previous step"` / `aria-label="Next step"`. `aria-disabled="true"` when at bounds.
- Unsupported claim flag glyph: `aria-label="Unsupported claim"`.
- Out-of-scope flag glyph: `aria-label="Out of scope"`.
- Focus ring: `outline: 2px solid var(--focus); outline-offset: 2px` (consistent with A12 pattern).
- Color contrast: `--fg-0` on `--bg-0` > 12:1. `--fg-2` on `--bg-0` ≈ 4.5:1 minimum. `--accent-red` on `--bg-2` must be verified by executor at 11px text (WCAG AA 4.5:1); if insufficient contrast, pair with `--fg-0` label.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not applicable |
| Third-party | none | not applicable |

No third-party component registries. All UI is hand-rolled SolidJS + CSS.

---

## Pre-Population Sources

| Decision | Source |
|----------|--------|
| Token system (all CSS vars) | A12-UI-SPEC + `voss-ignite.json` — not redefined |
| Spacing scale (8-point, multiples of 4) | A12-UI-SPEC |
| Typography (6 tiers, Poppins/Inter/JBMono) | A12-UI-SPEC |
| 60/30/10 color split | A12-UI-SPEC |
| Border-radius: 0 everywhere (panel style) | A12-UI-SPEC (variant-b convention) |
| Aggregate `load_run` / auto-load most-recent run | V11-CONTEXT D-01, D-04 |
| Static snapshot + manual refresh (no live stream) | V11-SPEC + CONTEXT |
| Decision dialog must show exact CLI command | V11-CONTEXT D-07 + Specifics |
| Inline success/failure + auto-refresh after decision | V11-CONTEXT D-08 |
| Replay = board/card only (reducer, client-side fold) | V11-CONTEXT D-05, D-06 |
| No raw `.voss/sessions` parsing in frontend | V11-SPEC constraint |
| Grid unchanged on toggle back | V11-SPEC acceptance criteria |
| Unsupported EM-claim visible flag (audit) | V11-SPEC VADE-04 acceptance |
| A and B verdicts visually separated | V11-SPEC VADE-03 acceptance |
| Existing sidebar/StatusBar/ContextPanel reused | V11-SPEC + CONTEXT code_context |
| SolidJS produce/proxy caveat (hand-clone in replay reducer) | CONTEXT code_context + memory |
| Vite target safari15 | CONTEXT code_context + memory |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending

---

*Phase: V11-ade-org-integration*
*UI-SPEC created: 2026-06-07*
