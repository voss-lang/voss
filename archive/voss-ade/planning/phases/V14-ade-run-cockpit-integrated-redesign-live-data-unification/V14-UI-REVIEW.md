# Phase V14 — UI Review

**Audited:** 2026-06-09
**Baseline:** V14-DESIGN-BRIEF.md (cockpit layout contract) + V14-CONTEXT.md decisions D-01..D-13 + A12-UI-SPEC.md (Ignite token contract)
**Screenshots:** Not captured — no dev server running (Tauri app; code-only audit)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 2/4 | "Voss-native" appears in user-facing UI; emoji in RunCommandBar; attention pill uses glyph-only content; card drawer shows raw ID as heading |
| 2. Visuals | 2/4 | Cockpit regions have no section chrome; card drawer shows raw ID (not title) as first content; pane-peek is a permanently-grey stub with zero affordance signal |
| 3. Color | 3/4 | Hardcoded `#fff` in 5 places; A12 token discipline otherwise strong; attention badge 9px font below 11px minimum |
| 4. Typography | 2/4 | Unauthorized 9px, 10px, 15px, 18px sizes scattered across V14 components; RunCommandBar uses var(--font-mono) for all controls contra A12 UI-body spec |
| 5. Spacing | 2/4 | 6px, 10px, 14px values appear 9+ times breaking the 4-multiple rule; only 4px/8px/12px/16px are on-scale |
| 6. Experience Design | 3/4 | Card drawer never shows card title as heading; timeline rail is passive (not selection-reactive per D-03 summary gap); attention panel positioning context fragile |

**Overall: 14/24**

---

## Top 3 Priority Fixes

1. **CardDrawer renders raw card ID as the visible "heading" (CardDrawer.tsx:107)** — Users see an internal UUID string at the top of every card detail panel, not the card's title or role. This is the single largest visual regression from the operator-approved cockpit mockup (which showed "idea/AC · role · reviewerA/B"). Fix: look up the card's title from runData via the selectedCardId, render it as a Poppins 500 14px `--fg-0` heading above the panel sections.

2. **"Voss-native" appears in user-facing UI copy (RunCommandBar.tsx:87, :154)** — D-10 locks that internal-mechanics vocabulary must never appear in the UI. The target segmented control shows the label "Voss-native" and the block-reason string reads "Voss-native runs are not available yet". Both violate the operator-locked copy rule. Fix: rename the label to "Voss run" or "Managed" and the block reason to "Managed runs aren't available yet."

3. **9px font size in AttentionPanel badge (attentionPanel.css:106)** — A12 spec sets 11px as the minimum for all UI copy; 9px is below WCAG AA legibility threshold at this dark contrast level. The kind-badge at 9px is the first text users read to classify an attention item. Fix: raise `.attn-row__badge` to 11px, adjust padding to `1px 4px` to preserve visual density.

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

**WARNING — Multiple contract violations found.**

**1a. "Voss-native" in user-facing labels — BLOCKER under D-10**
- `RunCommandBar.tsx:87`: `{ id: 'native', label: 'Voss-native' }` — the target segmented control renders "Voss-native" as a button label visible to every user.
- `RunCommandBar.tsx:154`: `setBlockReason('Voss-native runs are not available yet (server gated).')` — an `role="alert"` string that surfaces directly to the user.
- D-10 locks: "terms `cage`, `Voss-native`, `PermissionGate`, `session-tree node`, `partial lineage`, `pane` do not appear in the UI." This is a copy-contract hard violation.
- Fix: `label: 'Voss run'` (or `'Managed run'`); block reason: `'Managed runs require the Voss server — not available in this build.'`

**1b. Emoji in RunCommandBar — WARNING**
- `RunCommandBar.tsx:225`: `{contextAttached() ? '📎 Context' : '📎 Attach'}` — a paperclip emoji in the primary intake strip. The A12 spec uses Unicode glyphs (not emoji) for chrome elements, and the project CLAUDE.md prohibits emojis. This also fails to render consistently in monospace-styled buttons.
- Fix: use `[ctx]` / `+ ctx` text glyphs or an SVG paperclip icon.

**1c. AttentionPanel pill is glyph-only with no text label — WARNING**
- `StatusBar.tsx:129-130`: The pill renders `⚠` or `◆` plus a count number. When count = 1, it shows `⚠ 1` with no text, so screen reader and quick-scan reads as: "alert: one" — no context. A12 spec for the agent pill says `● N agents · $X.XX`; the attention pill has no equivalent pattern.
- Fix: render `⚠ 1 item` or `◆ 3 pending` — add a short text label after the count.

**1d. "Live pane output preview unavailable." — redundant passive stub copy — WARNING**
- `CardDrawer.tsx:117-118`: When a live pane IS bound, the pane-peek section renders: "Live pane output preview unavailable." This reads as a broken feature, not a known gap. The user has no way to distinguish "feature not yet built" from "something failed."
- Fix: `Output preview coming soon — use Open in grid to see live output.`

**1e. Copy contract compliance for modals — PASS**
- `AdoptAgentModal.tsx`: "Let Voss manage this agent", "Hand to Voss", "From now on, Voss will", "track what this agent spends", "keep a record of its work" — no jargon, outcomes-only. D-10 compliant.
- `AgentLaunchModal.tsx`: no raw-command field, no explainer block. D-09 compliant.

---

### Pillar 2: Visuals (2/4)

**WARNING — Visual hierarchy is absent from the cockpit's core surfaces.**

**2a. CardDrawer shows raw UUID as first/only heading — BLOCKER**
- `CardDrawer.tsx:107-108`: The first visible content in a selected card is:
  ```
  {selectedCardId()}
  ```
  rendered in `var(--font-mono)` 11px `--fg-3`. This is a raw internal ID string (e.g. `card-3a8f12b4`) presented as the card's identity. There is no card title, no role badge, no idea summary displayed.
- The operator-approved cockpit mockup showed the drawer leading with the card's "idea/AC · reviewerA/B · scope · budget" — the board card itself shows `props.card.title` (`BoardPanel.tsx:89`). The drawer has access to the same `runData()` but never looks up the matching card to display its title.
- Impact: every selected card shows an opaque UUID header. The cockpit is unusable for navigation without memorizing IDs.
- Fix: in `CardDrawer.tsx`, look up the selected card via `runData()?.session_tree.nodes.find(n => n.id === selectedCardId())` or the normalized `Card` model; render a Poppins 500 14px `--fg-0` heading (card title or idea summary) as the first section.

**2b. Cockpit regions have no visible section chrome — WARNING**
- `CockpitShell.tsx:204-240`: The three regions (`.cockpit-board`, `.cockpit-drawer`, `.cockpit-rail`) are CSS grid cells touching each other with only a 1px `--border` divider between them. None has a labeled header like "Board" / "Details" / "Timeline". The gate bar at the bottom has no label distinguishing it from body content.
- The operator-approved mockup showed region headers (compact column headers in the board spine, a "Card detail" header on the drawer, a "Timeline" label on the rail). Without headers, a first-time user cannot parse the three-pane layout.
- Fix: add a 28px header row to each region with a `--font-display` 11px 600 uppercase label (`BOARD` / `DETAILS` / `TIMELINE`) styled with `--fg-3` — matching the sidebar section heading pattern.

**2c. Pane-peek section always visible but permanently stub — WARNING**
- `CardDrawer.tsx:89-144`: The read-only pane-peek section is rendered for EVERY selected card (not conditionally hidden for snapshot-only cards). When no live pane is bound (the common case for snapshot runs), it shows "No live pane bound to this card." and a disabled "Open in grid" button. This is dead chrome that takes vertical space above every panel section.
- Fix: wrap the entire pane-peek section in `<Show when={boundPaneId()}>`, so it is invisible for snapshot cards. Add a soft separator so the panel sections start with visual breathing room.

**2d. RunCommandBar wraps to multiple lines — WARNING**
- `runCommandBar.css:16`: `flex-wrap: wrap`. At typical viewport widths (1160px workspace), the bar wraps when all chips are shown (goal input + 2 segmented controls + team selector + scope chip + budget chip + context-attach + start button). Warp-style bars never wrap; they stay single-line with overflow management or field collapsing. This undermines the "always-on universal input" identity.
- Fix: replace `flex-wrap: wrap` with overflow-x scroll or hide low-priority controls (context-attach, team) under a `...` overflow menu at narrow widths.

---

### Pillar 3: Color (3/4)

**WARNING — Hardcoded color values and one sub-minimum font size on a colored badge.**

**3a. Hardcoded `#fff` in five places — WARNING**
- `runCommandBar.css:82`: `.run-bar__start { color: #fff }` — the Start button text is hardcoded white instead of using a semantic token.
- `modal.css:175`: `.modal-btn-primary { color: #fff }` — Launch Agent / Hand to Voss button.
- `modal.css:252, :257`: `.modal-segmented__btn--active { color: #fff }` and its hover variant.
- `modal.css:295`: `.modal-switch__track--on .modal-switch__thumb { background: #fff }`.
- A12 spec: "All colors must be expressed via CSS variables. No raw hex values in component code." While `#fff` is safe on `--focus` (#ff5b1f) for contrast, it creates a token-purity violation.
- Fix: add `--on-accent: #fff` to the Ignite token set, or use `var(--fg-0)` in these five places (verify contrast).

**3b. AttentionPanel badge at 9px — WARNING (also Typography)**
- `attentionPanel.css:106`: `.attn-row__badge { font-size: 9px }` — this is also a color-contrast issue: orange-on-dark at 9px falls below WCAG AA 4.5:1 requirement for text under 14px. The A12 spec (Accessibility section) calls out that "Cost value when exceeding $1.00 per agent" requires a `--fg-0` label alongside if contrast is insufficient.

**3c. Attention badge pulse color correct — PASS**
- `attentionPanel.css:20-26`: pulse uses `box-shadow: 0 0 0 0 var(--focus)` and `rgba(255,91,31,0.35)` — these are token-referenced, not hardcoded.

**3d. 60/30/10 distribution — PASS**
- Dominant 60%: `--bg-0` used for body surfaces throughout cockpit and panels.
- Secondary 30%: `--bg-1` used for RunCommandBar strip, gate bar, drawer background, attention panel.
- Accent 10%: `--focus` used only for Start button fill, active segmented button, attention pill, focus borders — within A12's reserved-for list (items 3, 7, 8 from the spec).
- No unauthorized accent elements found.

---

### Pillar 4: Typography (2/4)

**NEEDS WORK — Four unauthorized font sizes in V14 components; RunCommandBar uses monospace for UI controls.**

**4a. Unauthorized font sizes — WARNINGS**

A12-UI-SPEC.md authorizes: 16px (modal title), 14px (display), 12px (UI body), 11px (UI label / mono body). The following unauthorized sizes appear:

- `attentionPanel.css:106`: `9px` — badge kind label. Below the 11px minimum.
- `attentionPanel.css:134, :153`: `10px` — meta line and action button font. A12 merges 10px into the 11px "Mono body" tier.
- `cockpitStyles.css:14`: `10px` — `.cockpit-live-label` (snapshot/live indicator). Should be 11px.
- `modal.css:43`: `15px` — `.modal-header__title`. A12 specifies 16px for modal title (Display large). 15px is between tiers with no contract basis.
- `modal.css:59`: `18px` — `.modal-header__dismiss` dismiss button font. Not in A12 type scale.
- `attentionPanel.css:67`: `13px` — `.attn-panel__close`. Not in A12 type scale.

In total, 6 unauthorized sizes appear across V14 files, with the most egregious being 9px (below legibility minimum) and 15px (split between the 12/16 authorized tiers).

**4b. RunCommandBar uses var(--font-mono) for all controls — WARNING**
- `runCommandBar.css:18, :30, :47, :66, :83, :97`: Every element in the RunCommandBar — goal input, team selector, chips, context-attach, Start button, reason text — uses `var(--font-mono)`.
- A12 spec: "UI label: Inter 11px 500" for buttons; "UI body: Inter 12px 400" for inputs. JetBrains Mono is reserved for "terminal content, status bar proc name, pane header cwd/shell, model names, cost values, timestamps."
- A goal-description textarea typed by the user should use Inter (readable prose), not monospace.
- Fix: Goal input → `var(--font-ui), Inter`; team select → `var(--font-ui)`; Start button → `var(--font-display), Poppins`. Keep monospace only on scope/budget chips (they are path/number values).

**4c. Poppins correctly used in modal headers and board column labels — PASS**
- `modal.css:41-42`: Poppins 600 — correct.
- `BoardPanel.tsx:176`: `var(--font-display), Poppins` for column headers — correct.

---

### Pillar 5: Spacing (2/4)

**NEEDS WORK — A12 8-point/4-multiple scale violated in 9+ places across V14 files.**

A12-UI-SPEC.md declares: xs=4px, sm=8px, md=16px, lg=24px, xl=32px. All values must be multiples of 4.

**Off-scale values found:**

| File | Rule | Value | Count | Fix |
|------|------|-------|-------|-----|
| `runCommandBar.css:15` | `.run-command-bar padding` | `6px 10px` | 1 | → `4px 8px` |
| `runCommandBar.css:61` | `.run-bar__attach padding` | `0 10px` | 1 | → `0 8px` |
| `runCommandBar.css:78` | `.run-bar__start padding` | `0 14px` | 1 | → `0 12px` |
| `cockpitStyles.css:18` | `.cockpit-live-label padding` | `0 6px` | 1 | → `0 4px` or `0 8px` |
| `cockpitStyles.css:105` | `.cockpit-comment gap` | `6px` | 1 | → `4px` or `8px` |
| `cockpitStyles.css:118` | `.cockpit-comment__box padding` | `6px` | 1 | → `8px` |
| `GateBar.tsx:91` | gap inline | `'6px'` | 1 | → `'4px'` or `'8px'` |
| `GateBar.tsx:112` | padding inline | `'1px 6px'` | 1 | → `'0 8px'` with height |
| `attentionPanel.css:100` | `.attn-row__head gap` | `6px` | 1 | → `4px` or `8px` |

In addition, inline style values in `CardDrawer.tsx` (`gap: '12px'`, `padding: '12px'`) are on-scale (12 = 4×3) but not in the declared token set — they should use `var(--space-md)` or a named size token rather than bare pixel values.

**On-scale and clean — PASS**
- Modal paddings (8px/16px/20px), attentionPanel body padding (8px), sidebar dimensions (280px, 44px, 28px) are all correct.

---

### Pillar 6: Experience Design (3/4)

**WARNING — Three notable gaps in interaction quality.**

**6a. Timeline rail is passive — not selection-reactive (known gap from V14-03) — WARNING**
- V14-03-SUMMARY.md explicitly documents: "The rail (SessionTreePanel) RENDERS C1's node but does NOT scroll/highlight on global selectedCardId." The cockpit's core promise (one selection drives all four regions) is only 3/4 fulfilled. From the operator's perspective, clicking a board card does not move the timeline — the most important temporal navigation link is broken.
- The V14-03-SUMMARY deferred this to plan 08 or a follow-up. There is no evidence from V14-08 through V14-11 that it was resolved.
- Impact: the central VCKP-05 acceptance criterion — "the timeline rail scrolls to C1's node" from a single selection action — is not met.
- Fix: add a thin adapter (not a rewrite of SessionTreePanel) that reads `selectedCardId()` and scrolls/highlights the matching `SessionTreeNode` row via a ref call or a class toggle on `data-card-id`.

**6b. No post-launch feedback in RunCommandBar — WARNING**
- `RunCommandBar.tsx:244-258`: After a successful run start, the bar resets nothing; there is no "Run started" confirmation, no run ID display, no way for the user to know if the launch was successful. The only feedback is the block-reason for failures.
- The operator-approved "Warp universal-input style" includes immediate feedback after submission (Warp shows the command being run, Raycast dismisses and shows a result). The RunCommandBar shows nothing.
- Fix: On successful start, show a transient `run-bar__reason` style message ("Starting run…" → "Run started") for 2 seconds, or display the launched run ID in the existing snapshot label area.

**6c. AttentionPanel positioning context is ambiguous — WARNING**
- `attentionPanel.css:31-46`: `.attn-panel { position: absolute; right: 8px; bottom: 30px }`. The nearest `position: relative` ancestor in `App.tsx` is the work-surface column div at line 1325. With `bottom: 30px` the panel should sit above the StatusBar, but this relies on the element being correctly contained. If the work-surface column is vertically clipped (e.g. on a small screen), the panel may render partially under the StatusBar or clip behind it.
- Fix: Move the AttentionPanel `position: absolute` reference to a dedicated overlay container that wraps the full application surface (inside the `showGrid()` Show, outside the column flex), or use `position: fixed` with a high enough z-index (already z-index:50) above the StatusBar.

**6d. State coverage — PASS**
- Loading state: `CockpitShell.tsx:175-181` — spinner with aria-label.
- Error state: `CockpitShell.tsx:183-198` — "Run not found" heading + body + Refresh button.
- Empty states: drawer no-selection, board no-data, gate bar no-selection — all present.
- Disabled-with-reason: RunCommandBar Auto gate, "Open in grid" disabled when no live pane, CardDrawer follow-up disabled for snapshot cards, AdoptAgentModal CTA disabled when no harness path — all correctly implemented.
- Reduced-motion: `cockpitStyles.css:150-157` and `attentionPanel.css:175-178` — both present and correct.

**6e. Keyboard navigation — PASS (partial)**
- `CockpitShell.tsx:204, 212, 217-220`: three cockpit regions carry `tabindex={0}` in DOM order.
- `cockpitStyles.css:93-98`: `:focus-visible` outlines using `--focus` token.
- The gate bar does NOT carry `tabindex={0}`, breaking the intended Board→drawer→timeline→gate traversal.
- Fix: add `tabindex={0}` to `.cockpit-gate` div in `CockpitShell.tsx:241`.

**6f. AdoptAgentModal and AgentLaunchModal experience quality — PASS**
- Both modals have focus-on-mount, Esc/Cmd+Enter keymaps, backdrop click-out.
- Role/risk pre-inferred + editable in adopt modal per D-12.
- Capability tier surfaced honestly (tier B for non-hook CLIs) per D-13.

---

## Files Audited

- `/apps/voss-app/src/org/cockpit/CockpitShell.tsx`
- `/apps/voss-app/src/org/cockpit/CardDrawer.tsx`
- `/apps/voss-app/src/org/cockpit/GateBar.tsx`
- `/apps/voss-app/src/org/cockpit/RunCommandBar.tsx`
- `/apps/voss-app/src/org/cockpit/cockpitStyles.css`
- `/apps/voss-app/src/org/cockpit/runCommandBar.css`
- `/apps/voss-app/src/org/attention/AttentionPanel.tsx`
- `/apps/voss-app/src/org/attention/attentionPanel.css`
- `/apps/voss-app/src/org/panels/BoardPanel.tsx`
- `/apps/voss-app/src/org/orgStyles.css`
- `/apps/voss-app/src/components/modal/AgentLaunchModal.tsx`
- `/apps/voss-app/src/components/modal/AdoptAgentModal.tsx`
- `/apps/voss-app/src/components/modal/modal.css`
- `/apps/voss-app/src/components/sidebar/AgentSidebar.tsx`
- `/apps/voss-app/src/components/sidebar/AgentContextMenu.tsx`
- `/apps/voss-app/src/App.tsx` (RunCommandBar mount region, StatusBar wiring, AttentionPanel placement)
- `/apps/voss-app/src/themes/bundled/voss-ignite.json`
- `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-03-SUMMARY.md` (gap documented)
- `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-04-SUMMARY.md`
- `.planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md`
