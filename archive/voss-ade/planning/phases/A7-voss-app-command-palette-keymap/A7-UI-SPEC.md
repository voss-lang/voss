---
phase: A7
slug: voss-app-command-palette-keymap
status: approved
shadcn_initialized: false
preset: none
created: 2026-05-20
reviewed_at: 2026-05-20T18:30:38Z
---

# Phase A7 - UI Design Contract: voss-app Command Palette + Keymap

> Visual and interaction contract for Phase A7. A7 extends the A1 Variant B shell, A3 grid chrome, A4 layout preset controls, A5 project setup surface, and A6 persistence planning. It must not introduce a component library, raw color values, rounded cards, explanatory onboarding text, or L2 agent semantics.
> Sources: A7-CONTEXT.md, A7-RESEARCH.md, ROADMAP A7 CMD-01..07, A1/A3/A4 UI-SPECs, `variant-b.css`, and current voss-app source.

---

## Design System

| Property | Value | Source |
|---|---|---|
| Tool | none (manual CSS + Tailwind v4) | Existing Solid/Tauri app; no `components.json` |
| Preset | not applicable | no component library |
| Component library | none - hand-rolled Solid components only | A1/A3/A4 contracts |
| Icon library | none - glyph characters and text only (`⌘`, `⇧`, `⌥`, `●`, `⋯`, `›`) | Variant B density rule |
| Font (all UI) | `"JetBrains Mono", "SF Mono", "Menlo", ui-monospace, monospace` | `--font-mono` |

**shadcn gate:** not applicable. voss-app is Solid/Tauri, not React/Next.js, and no third-party UI registry is allowed in A7.

---

## Token Inheritance Contract

A7 MUST use the existing Variant B tokens from `apps/voss-app/src/styles/variant-b.css` and Tailwind v4 mappings from `apps/voss-app/src/index.css`.

A7 MUST NOT:

- Add new color tokens.
- Use raw hex values in component code.
- Add rounded corners.
- Add gradient, glass, blur, orb, card-heavy, or marketing-style treatments.
- Add a component library or third-party registry block.
- Add visible help text explaining keyboard shortcuts outside the command surfaces themselves.
- Add L2 agent/cost/status semantics to palette categories or commands.

A7 may add component classes under `apps/voss-app/src/command-palette/`, but values must be composed from:

- `--bg-0`, `--bg-1`, `--bg-2`, `--bg-3`
- `--border`, `--border-bright`
- `--focus`, `--focus-glow`
- `--fg-0`, `--fg-1`, `--fg-2`, `--fg-3`
- `--accent-green`, `--accent-amber`, `--accent-red`, `--accent-cyan`, `--accent-magenta`, `--accent-blue`
- `--titlebar-height`

---

## Spacing Scale

A7 uses the standard 4px spacing scale for all new palette, toast, and keymap surfaces.

| Token | Value | A7 Usage |
|---|---:|---|
| xs | 4px | Row icon/chord gaps, compact inline separators |
| sm | 8px | Row vertical padding, input inset, toast inner gaps |
| md | 16px | Palette side padding, row horizontal padding, toast side padding |
| lg | 24px | Palette header/footer separation where needed |
| xl | 32px | Palette row min-height and toast min-height |
| 2xl | 48px | Overlay top margin on short viewports |
| 3xl | 64px | Maximum overlay vertical breathing room on tall viewports |

Exceptions: none for A7-owned components.

Inherited fixed chrome constants from A1/A3/A4 remain in force but are not new A7 spacing tokens: 22px titlebar/pane header height, 1px borders, 0px radius, and existing traffic-light spacing.

---

## Typography

A7 uses four sizes and two weights only.

| Role | Size | Weight | Line Height | Font | A7 Usage |
|---|---:|---:|---:|---|---|
| Meta | 10px | 400 | 1.0 | `--font-mono` | Chord hints, category glyph labels, toast timestamp-free metadata |
| Label | 11px | 400 | 1.0 | `--font-mono` | Category names, empty/error copy, prefix indicator |
| Body | 12px | 400 | 1.4 | `--font-mono` | Palette row labels, quick-open item paths, toast body |
| Heading | 13px | 600 | 1.2 | `--font-mono` | Palette input text and selected row label emphasis |

Rules:

- Palette rows use Body 12px/400 at rest.
- The active row label may use Heading 13px/600 only while highlighted.
- Chord hints stay Meta 10px/400 and right-aligned.
- Toast title/body uses Body 12px/400; destructive or warning labels do not get extra weight.
- No display type, hero type, title case marketing copy, or negative letter spacing.

---

## Color

A7 uses A1/A3/A4 tokens verbatim.

| Role | Value | Usage |
|---|---|---|
| Dominant (60%) | `--bg-0`, `--bg-1` | App dimmer, overlay backdrop, base palette surface |
| Secondary (30%) | `--bg-2`, `--bg-3`, `--border`, `--border-bright`, `--fg-0..3` | Palette panel, row hover/active states, toasts, structural borders, text tiers |
| Accent (10%) | `--focus`, `--accent-amber`, `--accent-red`, `--accent-green`, `--accent-cyan` | Focus ring, tmux prefix indicator, validation warning/error/success/info states only |
| Destructive | `--accent-red` | Close pane command row, destructive confirmation copy, keymap validation errors |

Accent reserved for:

- `--focus`: focused palette input outline, active row left rail, keyboard focus ring.
- `--accent-amber`: Cmd+B prefix indicator and keymap warning toasts.
- `--accent-red`: invalid keymap errors and destructive command labels.
- `--accent-green`: keymap profile/override load success toast.
- `--accent-cyan`: neutral informational toast or command category glyph only when a category needs a non-error semantic mark.

Accent is never a general-purpose interactive color. Hover states use `--bg-2`/`--bg-3`, not accent colors.

---

## Copywriting Contract

| Element | Copy |
|---|---|
| Primary CTA | `Open project` |
| Quick-open placeholder | `Open layout or recent project` |
| Full-palette placeholder | `Run command` |
| Empty quick-open heading | `No layouts or recent projects` |
| Empty quick-open body | `Save a layout or open a project to add quick-open targets.` |
| Empty full-palette heading | `No matching commands` |
| Empty full-palette body | `Refine the query or press Esc to return to the focused pane.` |
| Keymap invalid toast | `Keymap entry ignored` |
| Keymap conflict toast | `Keymap conflict ignored` |
| Keymap success toast | `Keymap updated` |
| Profile switch toast | `Keymap profile changed` |
| Destructive confirmation | `Close pane`: `"{process}" is running. Close anyway?` |

Additional command labels are locked:

| Command | Copy |
|---|---|
| Quick-open layouts section | `Layouts` |
| Quick-open recents section | `Recent Projects` |
| Full palette window category | `Window` |
| Full palette pane category | `Pane` |
| Full palette layout category | `Layout` |
| Full palette project category | `Project` |
| Full palette settings category | `Settings` |
| Full palette help category | `Help` |
| Switch profile command | `Switch Keymap Profile` |
| VSCode profile label | `VSCode` |
| tmux profile label | `tmux` |

Do not use generic single-word form labels or vague empty-state copy. Every label must name the object being acted on.

---

## Command Palette Contract

A7 ships one `CommandPalette` component with two modes:

- `quick`: opened by `Cmd+P`; lists saved layouts and recent projects.
- `full`: opened by `Cmd+Shift+P`; lists all registry commands.

### Visual Hierarchy

Primary focal point: the palette input at the top of the overlay. It receives focus immediately, uses the highest A7 text role, and carries the only focus ring inside the overlay.

Secondary focal point: the active result row. It is indicated by `--bg-2`, a 1px `--focus` left rail, and higher text contrast.

Tertiary information: category glyphs, secondary paths, and chord hints. These stay dim (`--fg-3`) so they teach the command model without competing with the selected command.

Toast focal point: the 1px severity rail and first line of toast copy. Toasts never steal focus from the palette or pane.

### Overlay

| Property | Contract |
|---|---|
| Position | Centered overlay, fixed to viewport, above titlebar/grid/panes |
| Width | `min(680px, calc(100vw - 64px))` |
| Max height | `min(520px, calc(100vh - 96px))` |
| Background | `var(--bg-1)` panel on subtle `rgba(0,0,0,0.48)` backdrop or `--bg-0` dimmer |
| Border | `1px solid var(--border-bright)` |
| Radius | `0px` |
| Shadow | Existing hard terminal shadow only: `0 16px 48px rgba(0,0,0,0.45)` |
| Animation | None required; if added, max 80ms opacity only and must respect reduced motion |

The overlay is not a card within a card. It is a single command surface over the app.

### Input

| Property | Contract |
|---|---|
| Height | 48px |
| Padding | `0 16px` |
| Font | Heading 13px/600 for typed query |
| Placeholder color | `--fg-3` |
| Border bottom | `1px solid var(--border)` |
| Focus | `box-shadow: inset 0 0 0 1px var(--focus)` |

Input copy:

- quick mode placeholder: `Open layout or recent project`
- full mode placeholder: `Run command`

### Rows

| Property | Contract |
|---|---|
| Min height | 32px |
| Padding | `0 16px` |
| Layout | category glyph/label, primary label, optional secondary path, right-aligned chord |
| Rest background | transparent |
| Hover/active background | `--bg-2` |
| Active indicator | 1px left rail in `--focus`; do not fill the row with accent |
| Primary label | `--fg-0` when active, `--fg-1` at rest |
| Secondary path | `--fg-3`, truncated in the middle or end |
| Chord hint | `--fg-3`, Meta 10px/400, right aligned |

Rows must not change height on hover, selection, loading, or missing chord hints.

### Category Glyphs

A7 may use text glyphs only:

| Category | Glyph |
|---|---|
| Window | `W` |
| Pane | `P` |
| Layout | `L` |
| Project | `R` |
| Settings | `S` |
| Help | `?` |
| Layout quick-open item | `L` |
| Recent project quick-open item | `R` |

Glyphs use `--fg-3` at rest and `--fg-1` when active. Do not introduce illustrative icons.

### Keyboard Interaction

| Key | Behavior |
|---|---|
| `Cmd+P` | Open quick mode; focus input; PTY does not receive the chord |
| `Cmd+Shift+P` | Open full mode; focus input; PTY does not receive the chord |
| `Esc` | Dismiss palette and restore focus to previously focused pane |
| `Enter` | Execute highlighted row and dismiss if the row completes synchronously |
| `ArrowDown` / `ArrowUp` | Move selection by one row |
| `Tab` / `Shift+Tab` | Move focus within palette only; never into pane while open |
| Click outside | Dismiss palette and restore pane focus |

While the palette is open, all printable keystrokes belong to the palette input. No palette-open keystroke reaches the PTY.

### Quick Mode Rows

Quick mode row order:

1. Saved layouts from `.voss/layouts/<name>.json`, sorted by recency if available, then alphabetically.
2. Recent projects from `~/.config/voss-app/recents.json`, newest first.

Quick mode actions:

- Layout row: apply layout via existing A4 load/apply path.
- Recent project row: open project via existing A5 `openProject` path, refresh recents, and apply default layout if present.

No file search, file-open placeholder, or disabled L4 row is allowed in A7.

### Full Mode Rows

Full mode includes all v0 command categories from ROADMAP CMD-03 and FEATURES L1.5:

- Window
- Pane
- Layout
- Project
- Settings
- Help

Commands with no active implementation must either be omitted or be real no-op-safe commands explicitly scoped to L1. A7 must not render placeholder commands that say "coming soon".

---

## Toast Contract

A7 ships a minimal toast stack for keymap/profile feedback.

| Property | Contract |
|---|---|
| Position | Fixed bottom-right, above pane content and below modal palette when palette is open |
| Width | 320px max; `calc(100vw - 32px)` on narrow windows |
| Min height | 32px |
| Padding | `8px 16px` |
| Gap | 8px between stacked toasts |
| Background | `--bg-3` |
| Border | `1px solid var(--border-bright)` |
| Radius | 0px |
| Font | Body 12px/400 |
| Auto-dismiss | 5s for non-error, 8s for error |
| Max visible | 3; newest at bottom |

Toast severity colors:

- Success: 1px left rail `--accent-green`
- Warning: 1px left rail `--accent-amber`
- Error: 1px left rail `--accent-red`
- Info: 1px left rail `--accent-cyan`

Toast body must include the failing command id or key when available:

- `Keymap entry ignored: pane.splitRight uses invalid chord`
- `Keymap conflict ignored: Cmd+D already belongs to Pane: Split Right`

---

## Keymap Profile and Override UI Contract

A7 does not ship the A9 settings UI. Profile switching is command-palette-driven and persists to `~/.config/voss-app/settings.json`.

### Profile Selection

The command `Switch Keymap Profile` opens an in-palette choice list using the same `CommandPalette` surface. It is not a separate modal.

Rows:

| Label | Secondary Text | Behavior |
|---|---|---|
| `VSCode` | `Default keymap` | Persist `keymap.profile = "vscode"` |
| `tmux` | `Cmd+B prefix mode` | Persist `keymap.profile = "tmux"` |

Active profile row shows a right-aligned `active` label in `--fg-3`, not an accent badge.

### `.voss/keymap.json` Validation Feedback

Invalid entries are surfaced as toasts only. The palette must not open automatically on file-watch errors.

Toast copy rules:

- Unknown command id: `Keymap entry ignored: unknown command "{id}"`
- Invalid chord syntax: `Keymap entry ignored: "{key}" is not a supported chord`
- Chord conflict: `Keymap conflict ignored: {chord} already belongs to {command}`
- Valid partial apply: `Keymap updated`

Partial apply means a valid subset updates immediately even when invalid entries toast errors.

---

## Tmux Prefix Indicator Contract

The tmux prefix indicator appears only when:

- active keymap profile is `tmux`
- focused pane is known
- user pressed `Cmd+B`
- 1.5s prefix window has not expired

Placement:

- Inside the focused pane's existing `PaneHeader`.
- Right side, immediately before the `⋯` menu trigger.
- No separate row, no layout shift larger than the indicator's reserved width.

Copy and styling:

| Element | Contract |
|---|---|
| Text | `[Cmd+B...]` |
| Font | Label 11px/400 |
| Color | `--accent-amber` |
| Background | transparent |
| Border | none |
| Width | reserve 72px when profile is tmux; render empty when inactive |

Behavior:

- Timeout after 1.5s clears the indicator.
- Esc clears the indicator and does not reach PTY.
- Recognized prefix key clears the indicator after dispatch.
- Unrecognized prefix key clears the indicator and passes the key through to PTY.
- Unfocused panes never show the indicator.

---

## Native Menu Contract

Native OS menus must wrap the same command registry used by keyboard dispatch and palette rows.

Menu categories map exactly to palette categories:

- Window
- Pane
- Layout
- Project
- Settings
- Help

Rules:

- Native menu item id equals command id.
- Native menu label equals registry label.
- Native menu accelerator equals effective keybinding when supported by Tauri.
- Native menu event calls the same registry handler through `AppContext`.
- Profile or override changes rebuild/update accelerators without changing labels.

No separate hard-coded native menu command list is allowed unless generated from the registry metadata.

---

## Accessibility Contract

- Palette has `role="dialog"` and `aria-modal="true"`.
- Palette input has `aria-label="Command search"` in full mode and `aria-label="Quick open search"` in quick mode.
- Rows are `role="option"` inside a listbox-like result container, or buttons with deterministic aria labels. Pick one pattern and test it.
- Active row exposes `aria-selected="true"` if using listbox semantics.
- Toast stack uses `aria-live="polite"` for success/info and `aria-live="assertive"` for errors.
- Icon/glyph-only affordances require assistive labels; no visible helper text is added.
- Focus returns to the previously focused pane after palette dismissal.

---

## Responsive and Overflow Contract

Desktop:

- Palette max width is 680px.
- Result list scrolls internally when content exceeds max height.
- Chord hints remain visible unless width is below 420px.

Narrow windows:

- Palette width becomes `calc(100vw - 64px)`.
- Secondary paths truncate before primary labels.
- Chord hints may hide below 420px, but command labels and categories remain visible.
- Toast width becomes `calc(100vw - 32px)`.

Text must not overlap in palette rows, toast bodies, the pane header prefix indicator, or native menu labels.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|---|---|---|
| shadcn official | none | not required |
| third-party registries | none | not applicable - no third-party UI registry blocks allowed |

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-05-20
