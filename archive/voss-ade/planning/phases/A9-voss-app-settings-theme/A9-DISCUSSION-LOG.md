# Phase A9: voss-app Settings + Theme - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-20
**Phase:** A9-voss-app-settings-theme
**Areas discussed:** Settings panel hosting, Merge & override UX, Hot-reload granularity, Edit-as-JSON & telemetry

---

## Settings panel hosting

### Q1: How should the settings panel render?

| Option | Description | Selected |
|--------|-------------|----------|
| Full-screen overlay | Centered overlay covering pane area. Esc dismisses. Same z-layer as command palette but full-size. | ✓ |
| Dedicated pane type | Settings opens as a special non-terminal pane in the grid. More complex. | |
| Modal dialog | Smaller centered modal. Limits form real estate. | |

**User's choice:** Full-screen overlay
**Notes:** Avoids pane-tree complexity for a rare-visit destination.

### Q2: How does the user open settings?

| Option | Description | Selected |
|--------|-------------|----------|
| ⌘, shortcut | Standard macOS/VSCode convention. Also via ⌘⇧P + A10 cog. | ✓ |
| ⌘⇧P palette only | No dedicated shortcut. Requires two steps. | |
| You decide | Planner picks. | |

**User's choice:** ⌘, shortcut

### Q3: Category nav style?

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed sidebar | Always-visible ~160px category list. Click → scroll right pane. | ✓ |
| Collapsible sidebar | Collapses to icons on narrow windows. More adaptive. | |
| You decide | Planner picks. | |

**User's choice:** Fixed sidebar

### Q4: Search behavior?

| Option | Description | Selected |
|--------|-------------|----------|
| Filter to matches | Typing hides non-matching settings. Clear restores full list. | ✓ |
| Jump to first match | Highlights and scrolls to first match. All settings remain visible. | |
| You decide | Planner picks. | |

**User's choice:** Filter to matches

---

## Merge & override UX

### Q5: Workspace-override indication?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline badge per row | Small 'workspace' badge + reset link. Hover → tooltip with user-level value. | ✓ |
| Section-level indicator | Category header shows 'N workspace overrides'. Less visual clutter. | |
| Separate workspace tab | Top-level 'User Settings' / 'Workspace Settings' toggle. | |
| You decide | Planner picks. | |

**User's choice:** Inline badge per row

### Q6: Which settings workspace-overridable?

| Option | Description | Selected |
|--------|-------------|----------|
| Most overridable | Appearance/Terminal/Layout overridable. Keybindings/Updates/Telemetry global-only. | ✓ |
| Everything overridable | All settings per-workspace. Maximum flexibility. | |
| You decide | Planner decides. | |

**User's choice:** Most overridable (~80%)

### Q7: Merge algorithm?

| Option | Description | Selected |
|--------|-------------|----------|
| Shallow merge by key | Workspace keys overwrite at top level. No deep-merge. | ✓ |
| Deep merge | Recursive nested merge. More granular, harder to reason about. | |
| You decide | Planner picks. | |

**User's choice:** Shallow merge by key

### Q8: Schema validation?

| Option | Description | Selected |
|--------|-------------|----------|
| Runtime Rust validation | Serde typed structs, defaults for unknown/invalid. No JSONSchema. | ✓ |
| JSONSchema + runtime | Ship schema file for VS Code intellisense. More to maintain. | |
| You decide | Planner picks. | |

**User's choice:** Runtime Rust validation

---

## Hot-reload granularity

### Q9: Visual settings reload?

| Option | Description | Selected |
|--------|-------------|----------|
| Immediate all panes | Theme/font/opacity apply instantly everywhere. Non-destructive. | ✓ |
| Preview-then-apply | Preview in one pane, click 'Apply to all'. Extra step. | |
| You decide | Planner picks. | |

**User's choice:** Immediate all panes

### Q10: Shell change behavior?

| Option | Description | Selected |
|--------|-------------|----------|
| New panes only | Existing panes keep running shell. No disruption. | ✓ |
| Offer restart per pane | Toast per pane: 'Shell changed. Restart?' | |
| You decide | Planner picks. | |

**User's choice:** New panes only

### Q11: Scrollback size change?

| Option | Description | Selected |
|--------|-------------|----------|
| New panes only | xterm.js scrollback set at construction. Changing mid-session lossy. | ✓ |
| Retroactive with warning | Apply to live panes with trim warning. | |
| You decide | Planner picks. | |

**User's choice:** New panes only

### Q12: Ask-before flow needed?

| Option | Description | Selected |
|--------|-------------|----------|
| No ask-before needed | Visual = instant+reversible. Process = new-panes-only. No prompts needed. | ✓ |
| Ask before font size changes | Font affects terminal column/row count. Show confirmation. | |
| You decide | Planner picks. | |

**User's choice:** No ask-before needed

---

## Edit-as-JSON & telemetry

### Q13: Edit as JSON behavior?

| Option | Description | Selected |
|--------|-------------|----------|
| OS default editor | Rust shell::open() on settings.json. Link per section. | ✓ |
| In-app read-only viewer | Styled JSON viewer + 'Open in editor' button. | |
| You decide | Planner picks. | |

**User's choice:** OS default editor

### Q14: Telemetry scope?

| Option | Description | Selected |
|--------|-------------|----------|
| Toggles only | Two switches, OFF default, persisted as booleans. No send code. | ✓ |
| Toggles + stub collector | Toggles + no-op collector module for future wiring. | |
| You decide | Planner picks. | |

**User's choice:** Toggles only

### Q15: Telemetry consent copy?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline descriptions | 1-2 lines plain English below each toggle. Direct, honest. | ✓ |
| Expandable detail | Short label + 'Learn more' expand. More transparent, may alarm. | |
| You decide | Planner picks. | |

**User's choice:** Inline descriptions

### Q16: Updates section?

| Option | Description | Selected |
|--------|-------------|----------|
| Placeholder section | Current version + disabled 'Check for updates' + non-functional toggles. | ✓ |
| Skip entirely | Don't show Updates until A11. Fewer dead toggles. | |
| You decide | Planner picks. | |

**User's choice:** Placeholder section

---

## Claude's Discretion

No areas deferred to Claude's discretion during discussion. Planner discretion items listed in CONTEXT.md (form control design, search implementation, icon glyphs, toast feedback, etc.).

## Deferred Ideas

None — all discussion stayed within A9 scope.
