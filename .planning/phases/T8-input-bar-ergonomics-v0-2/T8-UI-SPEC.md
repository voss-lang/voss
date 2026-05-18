---
phase: T8
slug: input-bar-ergonomics-v0-2
status: approved
shadcn_initialized: false
preset: none
medium: terminal-ui
created: 2026-05-17
reviewed_at: 2026-05-17
parent_spec: .planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md
---

# Phase T8 — UI Design Contract (Terminal UI)

> T8 EXTENDS the M9 design contract. It does not re-explore the design system.
> All M9 tokens, glyphs, color roles, layout rules, and copy conventions are
> inherited verbatim. This document specifies only the NEW visual and interaction
> surfaces introduced by INPUT-01..05. Anything not listed here falls back to M9.

---

## Design System

| Property | Value | Source |
|----------|-------|--------|
| Tool | none (no web design system — terminal UI) | M9-UI-SPEC |
| Preset | not applicable | M9-UI-SPEC |
| Library | Textual (locked by M9) | M9-UI-SPEC / T8-CONTEXT D-01 |
| Glyph vocabulary | Inherited from `glyphs.py` allow-list; T8 adds `!` prefix character and `#` prefix character as **text** sigils (not glyph constants) | glyphs.py |
| New glyph constants | None — T8 does NOT add entries to `glyphs.py`. The `!` and `#` prefix sigils are plain ASCII characters rendered as body text, never imported from `glyphs`. | T8 design decision |
| Stylesheet | `voss/harness/tui/styles.tcss` — T8 adds `.local-block`, `.local-block--shell`, `.local-block--note`, `.local-block--notice`, `.reverse-search-bar` classes only | styles.tcss |
| Color palette | Unchanged: `$accent #5FAFFF`, `$dim #888888`, `$good #5FD75F`, `$warn #FFD75F`, `$error #FF5F5F` | styles.tcss |

**shadcn gate:** Not applicable. Python/Textual TUI.
**Registry safety gate:** Not applicable. No third-party component registries.

---

## Layout / Spacing (Character Cells)

All M9 region layout is inherited verbatim. T8 changes only the `#input` region
height contract and introduces **local blocks** in the main pane turn history.

### Input bar height contract (T8 update to M9)

M9 locked: `height: 1; min-height: 1; max-height: 5;`
T8 confirms and clarifies the autogrow behavior:

| State | Rows | tcss rule |
|-------|------|-----------|
| Default (empty or single-line content) | 1 | `height: 1` (auto-shrinks back) |
| Content spans 2–5 lines | 2–5 | `height: auto` with `max-height: 5` |
| Content beyond 5 lines | 5 (capped, scrolls inside) | `max-height: 5`; Textual TextArea internal scroll; cursor kept visible |
| Ctrl-R mode (reverse-i-search prompt replaces content area) | 1 | `height: 1` (always single-row in search mode) |

The `#input` tcss block after T8:

```tcss
#input {
    dock: bottom;
    height: auto;
    min-height: 1;
    max-height: 5;
}
```

### Local block layout (new — T8)

Local blocks are single-turn-view entries in the main pane scrollback. They render
the same way as a normal `TurnView` row but use a distinct `.local-block` class
and never appear in model conversation history.

| Element | Layout | Notes |
|---------|--------|-------|
| Block left gutter | 1 cell — the sigil character (`!` or `#`) | Replaces the `⏵` tool-call glyph position |
| Block body | wrap at (main-pane width − 4) cells | Same as body text |
| Separator row | None — same `md` (1 row) between blocks as between turns | Inherited M9 spacing |
| Max visible rows per block | Uncapped — `!cmd` blocks scroll with the main pane | Entire stdout rendered |

### Slash palette: no layout change

The existing `SlashPalette` layout (`dock: bottom; offset-y: -1; max-height: 8`) is
unchanged. The only T8 interaction change is that the TextArea-based InputBar must
preserve the empty-value guard before opening the palette (guard is currently
in `input_bar.py:_on_key`; T8 must re-wire it after the TextArea swap).

### Inline reverse-i-search prompt layout

Ctrl-R does NOT open a modal or a new region. The reverse-i-search prompt occupies
the full content area of the `#input` region, replacing the normal TextArea display:

```
▌ (reverse-i-search)`query': matched text here
```

| Element | Cols | Style |
|---------|------|-------|
| Prompt glyph `▌` | 2 (glyph + space) | `.accent` (M9 accent rule #1) |
| Prefix label `(reverse-i-search)` `` | static width | `.dim` |
| Query text | typed by user | `.accent` (highlighted) |
| `': ` separator | 3 chars | `.dim` |
| Matched history entry | remainder | body (regular weight) |

Total display fits in 1 row at 80 cols minimum. On narrow terminals where the
full prefix + query + match would overflow, the matched entry is truncated with
`…` at the right edge.

### Image attachment affordance (INPUT-05, when vision capable)

When an image is pasted and the model has vision, the bar shows a one-line
attachment indicator above the text cursor (rendered as a static annotation
inside the `#input` region):

```
▌ [image attached · 1 image]  <user's text here>
```

| Element | Style |
|---------|-------|
| `[image attached · N image]` | `.dim` — subordinate metadata, not an action |
| Text cursor position | After the attachment indicator on the same logical line, or on the next row if multi-line |

The attachment indicator is NOT a separate widget — it is inline status text
rendered by the InputBar widget, cleared on submit.

---

## Spacing Scale (Character Cells)

Inherited verbatim from M9-UI-SPEC. No new tokens.

| Token | Value | Usage |
|-------|-------|-------|
| `tight` | 0 cells | Adjacent labels within a single status field |
| `xs` | 1 cell | Between glyph and following text |
| `sm` | 2 cells | Standard inline padding inside a region |
| `md` | 1 row / 2 cells | Between turns in main pane; between local blocks |
| `lg` | 2 rows | Between top-level sections inside a modal |

No exceptions for T8.

---

## Typography (Terminal Text Roles)

Inherited verbatim from M9-UI-SPEC. No new style tiers.

Three tiers locked by M9: **regular**, **bold**, **dim**. T8 maps new surfaces onto them:

| T8 Surface | Style tier | Rationale |
|------------|-----------|-----------|
| `!cmd` local block — sigil `!` | bold | Distinct from body; signals local action |
| `!cmd` local block — command text (`cmd arg arg`) | `code / paths` role (regular, monospace assumed) | Command text is a code artefact |
| `!cmd` local block — stdout/stderr body | Body (regular) | User-produced output; no weight needed |
| `!cmd` local block — exit code metadata | dim | Subordinate metadata |
| `#note` local block — sigil `#` | bold | Symmetric with `!` sigil treatment |
| `#note` local block — note text | Body (regular) | Memory note content |
| `#note` confirmation line | dim | Subordinate acknowledgement |
| Reverse-i-search prefix label | dim | UI chrome, not content |
| Reverse-i-search query | `.accent` (cyan-blue highlight) | Active input focus signal |
| Reverse-i-search matched entry | Body (regular) | Content being recalled |
| Image attachment indicator | dim | Metadata annotation |
| No-vision notice | `.signal-warn` (bold + amber) | Surfaces a signal state (capability miss) |

---

## Color Contract

Inherited verbatim from M9-UI-SPEC. T8 maps new surfaces to existing roles:

| T8 Surface | Color role | Value (dark truecolor) | 16-color |
|------------|-----------|------------------------|----------|
| `!` sigil in local block | `$warn` | `#FFD75F` | `yellow` SGR 33 |
| `#` sigil in local block | `$accent` | `#5FAFFF` | `cyan` SGR 36 |
| `!cmd` exit code 0 | `$good` | `#5FD75F` | `green` SGR 32 |
| `!cmd` exit code non-zero | `$error` | `#FF5F5F` | `red` SGR 31 |
| Local block separator / border | `$dim` | `#888888` | SGR 2 |
| Ctrl-R query highlight | `$accent` | `#5FAFFF` | `cyan` SGR 36 |
| Ctrl-R prefix label | `$dim` | `#888888` | SGR 2 |
| Image attachment indicator | `$dim` | `#888888` | SGR 2 |
| No-vision inline notice | `$warn` | `#FFD75F` | `yellow` SGR 33 |

### Accent allow-list extension (T8 additions to M9 list)

M9 accent allow-list items 1–6 are inherited unchanged. T8 adds:

7. The `#` sigil in `#note` local blocks.
8. The query text in Ctrl-R reverse-i-search mode.

These are the ONLY T8 additions to the allow-list. The `!` sigil uses `$warn`
(not accent) to signal "local shell action" vs "note" distinction.

NOT permitted to use accent for: `!cmd` stdout/stderr body, exit code metadata,
image attachment indicator text, or any other new T8 surface not listed above.

### `NO_COLOR=1` / monochrome behavior for T8 surfaces

| Surface | Monochrome treatment |
|---------|---------------------|
| `!` sigil | bold text, no color |
| `#` sigil | bold text, no color |
| Exit code 0 | regular weight + `ok` suffix |
| Exit code non-zero | bold + `[exit N]` |
| No-vision notice | bold + `[no vision]` prefix |
| Ctrl-R query | reverse-video on the query chars |

---

## Copywriting Contract

M9 copy conventions inherited: sentence case, no exclamation marks, imperative voice,
backtick paths, numeric units. T8 adds the following locked strings:

### New locked strings

| Element | Copy |
|---------|------|
| `!cmd` local block header line | `! {cmd}` — the raw command string as typed (no truncation in header) |
| `!cmd` local block footer (exit 0) | `· exit 0` (dim, signal-good) |
| `!cmd` local block footer (non-zero) | `· exit {N}` (dim, signal-error) |
| `!cmd` empty (bare `!` with no cmd text) | No local block emitted. Input cleared silently. (No-op is the visual contract.) |
| `#note` local block | `# note saved` (dim) — single line, no block header. No body echo of the note text in the TUI. |
| `#note` empty (bare `#` with no text) | No block emitted. Input cleared silently. |
| Ctrl-R mode — prompt prefix | `(reverse-i-search)`` ` — exact string including backtick, preserving bash/zsh parity |
| Ctrl-R mode — separator | `':` — exact string (backtick + colon), space before matched text |
| Ctrl-R no matches | `(reverse-i-search)`` {query}': (no match)` — `(no match)` in dim, rest unchanged |
| Ctrl-R — Enter action (loads match) | No copy emitted. The matched text is loaded into the bar editable; user sees the text. |
| Ctrl-R — Esc action | Bar returns to normal mode with previously typed content restored (or empty if none). No toast. |
| Image attached (vision-capable model) | `[image attached · 1 image]` (dim) inline in input bar before text cursor |
| Image — no-vision inline notice | `current model has no vision — image not attached` (signal-warn) |
| No-vision notice placement | Renders as a **transient local block** in main pane scrollback (NOT a status-line toast, NOT a modal). Disappears on next submit or after 3000ms auto-removal — whichever comes first. |
| No-vision notice — `NO_COLOR=1` | `[no vision] current model has no vision — image not attached` |

### Destructive actions inventory (T8 additions)

No new destructive actions in T8. The `!cmd` shell execution goes through the
existing permission prompt (M9's "Run shell command via `shell_run`" destructive
action row in the M9-UI-SPEC). The confirmation UX is unchanged — T8 does not
bypass or shortcut the permission modal.

---

## Interaction Contract

### T8 Keybinding additions (additions to M9 KEYMAP only)

One new binding only. The existing `keymap.py` KEYMAP tuple receives:

```python
Binding("ctrl+r", "input", "reverse_search", "Reverse-search input history"),
```

All other M9 keybindings are unchanged.

**Disambiguation:** `ctrl+f` in `main` context = in-pane output search (M9,
unchanged). `ctrl+r` in `input` context = reverse-i-search over submitted task
history (T8, new). No collision — contexts are mutually exclusive by focus.

### INPUT-01 — TextArea swap interaction contract

| Behavior | Contract |
|----------|---------|
| Widget class | `TextArea` (Textual built-in), replacing `Input` |
| Default key for newline | `Enter` in Textual TextArea inserts newline by default — **invert**: bind `Enter` to submit, `Shift+Enter` to newline, matching M9 keymap |
| Prompt glyph render | `▌ ` (glyph + single space) rendered at col 0 of row 0 of the TextArea. On subsequent rows (multi-line), rows 2–5 have no prompt glyph — the glyph only appears on row 1 |
| `Submitted` message contract | `InputBar.Submitted(value: str)` — preserved unchanged. Value is the full multi-line string. |
| Slash palette empty-value guard | Ported from `_on_key` to the TextArea equivalent handler. Palette opens ONLY when `self.document.text` is empty. Non-empty bar inserts literal `/`. |
| Autogrow | `height: auto; min-height: 1; max-height: 5` in tcss. Content beyond 5 rows scrolls inside the TextArea. |

### INPUT-02 — `!cmd` dispatch interaction contract

| Behavior | Contract |
|----------|---------|
| Trigger | Value starts with `!` after `.strip()`. Checked in `action_submit` before emitting `Submitted`. |
| Dispatch path | Submit-time prefix dispatch — branches BEFORE posting `Submitted`. Calls the existing gated shell-exec path (T5 D-12 deny-set + permission-mode behavior). Does NOT post `Submitted`. |
| Recorder event | Emits `shell.local` via `recorder_bridge.py` on command completion. |
| Local block render | Immediately appended to main pane scrollback as a `.local-block.local-block--shell` block. Never enters model conversation history. |
| Permission modal | Appears as with any `shell_run` call — deny/allow-once/allow-always. Plan-mode refuses cleanly with no escalation. |
| Non-zero exit | Block footer shows `· exit {N}` in signal-error. Block body shows stdout + stderr in full. |
| Empty `!` (no command) | No-op. Input cleared. No block emitted. |

### INPUT-03 — `#note` dispatch interaction contract

| Behavior | Contract |
|----------|---------|
| Trigger | Value starts with `#` after `.strip()`. Checked in `action_submit`. |
| Dispatch path | Branches BEFORE posting `Submitted`. Calls `voss_md`/`memory_cli` section-aware append to `VOSS.md § ## Notes`. |
| Note format written to VOSS.md | `- [{ISO-8601 timestamp}] {text}` — timestamp is UTC ISO-8601, microseconds omitted |
| Recorder event | Emits `memory.note` via `recorder_bridge.py` after the append. |
| Local block render | Single dim line `# note saved` appended to main pane scrollback as `.local-block.local-block--note`. Never enters model conversation history. |
| Empty `#` (no text) | No-op. Input cleared. No block emitted. |

### INPUT-04 — Ctrl-R reverse-i-search interaction contract

| Behavior | Contract |
|----------|---------|
| Entry | `ctrl+r` in `input` context triggers `action_reverse_search`. InputBar enters search mode. |
| Search mode — visual | The TextArea content display is replaced by the reverse-i-search prompt string (see Copywriting). The TextArea value is NOT mutated — it is saved and restored on cancel. |
| Corpus | Submitted task inputs only (prompts that posted `Submitted` and triggered `run_turn`). Source: current project's episodic store (`cli.py:584`). Consecutive duplicates collapsed, most-recent-first. Excludes `!cmd` / `#note` / `/`-palette lines. |
| Match algorithm | Case-insensitive substring match. First match = most-recent entry containing the query. |
| Repeated `ctrl+r` | Steps to the next older match in the corpus. |
| Enter in search mode | Loads matched entry into the bar as **editable text** (user can tweak before submitting). Does NOT auto-submit. Exits search mode. |
| Esc in search mode | Cancels. Restores pre-search bar content (or empty if bar was empty). Exits search mode. |
| No match state | Prompt shows `(no match)` suffix in dim. `Enter` is a no-op. `Esc` cancels as usual. |
| `ctrl+r` with empty corpus | Immediately shows `(no match)` state. |
| Search mode — TextArea state | TextArea is read-only while in search mode. Typing characters updates the query incrementally and re-filters in real time. |

### INPUT-05 — Paste-image interaction contract

| Behavior | Contract |
|----------|---------|
| Trigger | OS paste keypress detected by Textual (`ctrl+v` / `cmd+v`). Before inserting text, probe OS clipboard for image data. |
| Vision-capable model | Image is attached to the next `run_turn` call as a vision input. Inline indicator `[image attached · 1 image]` (dim) shown inside the input bar until submit. On submit, image is cleared from the bar state. |
| Vision-incapable model | Image dropped silently (no attachment). Inline notice `current model has no vision — image not attached` rendered as a transient local block in main pane (`.local-block.local-block--notice`). Auto-removes after 3000ms or on next submit. |
| Clipboard-image unsupported (platform fallback) | Falls back to normal text paste. No local block emitted. No error shown. |
| Multiple images in clipboard | Attach first image only. Indicator shows `1 image` regardless. (Multi-image deferred.) |
| Image + text in clipboard | Attach image; paste text content into bar normally. |

---

## Component Inventory (T8 additions to M9 component table)

| Component | Purpose | tcss class(es) | Props / key behaviors |
|-----------|---------|---------------|----------------------|
| `InputBar` (rewrite) | Multi-line text input — TextArea-based | `#input` | `Submitted(value)` message; autogrow 1–5 rows; slash-palette guard; `!`/`#` prefix dispatch on submit; Ctrl-R mode toggle |
| `LocalBlock` | Ephemeral local-action entry in main pane | `.local-block` + variant class | `kind: "shell" | "note" | "notice"`, `body: str`, `footer: str | None`; never in model history |
| `LocalBlockShell` | `!cmd` local block variant | `.local-block--shell` | `cmd: str`, `stdout: str`, `stderr: str`, `exit_code: int` |
| `LocalBlockNote` | `#note` local block variant | `.local-block--note` | Renders `# note saved` dim line only |
| `LocalBlockNotice` | Transient notice (e.g. no-vision) | `.local-block--notice` | `message: str`; auto-removes after 3000ms; `.signal-warn` style |
| `ReverseSearchBar` | Inline Ctrl-R search mode overlay | `.reverse-search-bar` | Renders over InputBar content; query string, matched entry; not a separate widget — a render mode of InputBar |

---

## tcss Additions (new classes only)

The following classes are added to `voss/harness/tui/styles.tcss`. No existing
classes are modified.

```tcss
/* T8: Local block — base. Ephemeral turn-view rows that never enter model history. */
.local-block {
    padding: 0 1;
}

/* T8: !cmd local block shell variant — sigil color $warn */
.local-block--shell > .sigil {
    color: $warn;
    text-style: bold;
}

/* T8: #note local block note variant — sigil color $accent */
.local-block--note > .sigil {
    color: $accent;
    text-style: bold;
}

/* T8: Transient notice block (e.g. no-vision) — signal-warn */
.local-block--notice {
    color: $warn;
}

/* T8: Reverse-search mode — dim label, accent query */
.reverse-search-bar .rs-label {
    color: $dim;
}

.reverse-search-bar .rs-query {
    color: $accent;
}
```

---

## Snapshot-Test Anchors (acceptance surface)

Textual snapshot tests must cover the following observable states. Each anchor
is a description of what the snapshot must show — exact snapshot file names are
planner's discretion.

| # | Surface | What must be visible in snapshot |
|---|---------|----------------------------------|
| 1 | INPUT-01 single-line | Input bar shows 1 row, `▌ ` prompt at col 0, cursor after prompt |
| 2 | INPUT-01 multi-line (3 rows) | Input bar shows 3 rows; prompt glyph only on row 1; rows 2–3 have no glyph |
| 3 | INPUT-01 at cap (5 rows) | Input bar capped at 5 rows; no layout reflow above |
| 4 | INPUT-01 slash palette guard | Slash palette opens when bar is empty and `/` pressed; does not open when bar is non-empty |
| 5 | INPUT-02 `!cmd` — local block (exit 0) | Main pane contains `.local-block--shell` row: `!` sigil (warn color), command text, `· exit 0` in signal-good |
| 6 | INPUT-02 `!cmd` — local block (exit non-zero) | Same block but `· exit 1` (or N) in signal-error |
| 7 | INPUT-03 `#note` — confirmation line | Main pane contains `.local-block--note` row: `# note saved` in dim |
| 8 | INPUT-04 Ctrl-R — search mode | Input bar shows `▌ (reverse-i-search)`` query': matched text` with correct color roles |
| 9 | INPUT-04 Ctrl-R — no match | Input bar shows `(no match)` suffix in dim |
| 10 | INPUT-05 image attached | Input bar shows `[image attached · 1 image]` dim annotation before cursor |
| 11 | INPUT-05 no-vision notice | Main pane contains `.local-block--notice` row in signal-warn: `current model has no vision — image not attached` |

Recorder-event assertions (non-snapshot, unit-level):

| # | Event | Assertion |
|---|-------|-----------|
| R1 | `!cmd` submit | `recorder_bridge.emit("shell.local", ...)` called with `cmd`, `exit_code`, `stdout`, `stderr` |
| R2 | `#note` submit | `recorder_bridge.emit("memory.note", ...)` called with `text` and `timestamp` |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| n/a (no shadcn — Python TUI) | n/a | not applicable |
| Textual built-in widgets | `TextArea` (replacing `Input`) — first-party Textual widget | none required — first-party library |
| Third-party Textual packages | None declared for T8 | n/a |

---

## Acceptance Visual Checks (for ui-checker + ui-auditor)

Inherits all 10 M9 acceptance checks. T8 adds:

11. **TextArea autogrow contract held** — bar grows 1–5 rows with content; never exceeds 5 rows; prompt glyph only on row 1 in multi-line state.
12. **Glyph allow-list not extended** — diff of `glyphs.py` shows zero new constants. `!` and `#` sigils appear only as plain string literals, never imported from `glyphs`.
13. **Accent allow-list held (T8 additions)** — `$accent` color appears on `#` sigil in note blocks and on Ctrl-R query text only. `!` sigil uses `$warn`. No other new uses of `$accent`.
14. **Local blocks absent from model history** — recorder shows no `user`/`assistant` messages containing `!cmd` or `#note` bodies.
15. **Slash palette guard preserved** — after TextArea swap, palette still opens only on empty bar, not on non-empty `/` keypress.
16. **Ctrl-R stays inline** — no modal or new pane opened by `ctrl+r`; search mode is purely a render-mode of the InputBar widget.
17. **No-vision notice is transient** — notice block auto-removes; not written to model conversation history; not a status-line toast.
18. **`ctrl+r` does not shadow `ctrl+f`** — in-pane output search (`ctrl+f` in `main` context) is unaffected; `ctrl+r` binding exists only in `input` context.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals (glyphs, layout, local blocks, search mode): PASS
- [ ] Dimension 3 Color (palette + accent allow-list T8 extensions): PASS
- [ ] Dimension 4 Typography (3 style tiers, T8 surface mapping): PASS
- [ ] Dimension 5 Spacing (character-cell layout, autogrow contract): PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending

---

## Notes for Planner / Executor

- **TextArea swap is the load-bearing change.** The `_on_key` slash-palette guard,
  the `Submitted` message, and the `action_submit` prefix-dispatch all must be
  re-wired on `TextArea`. Read `input_bar.py` in full before implementing.
- **`ctrl+r` binding placement:** Add one `Binding("ctrl+r", "input", "reverse_search", "Reverse-search input history")` to the `KEYMAP` tuple in `keymap.py`. Do not touch any other binding row.
- **Local blocks are not `TurnView` instances.** They are a separate widget type
  that renders in the same scrollback scroll-container but carries no model-history
  plumbing. The key invariant: they must never be added to the `messages` list that
  `run_turn` receives.
- **Ctrl-R corpus seeding in tests** must be deterministic and hermetic (T7
  precedent). Pre-seed the episodic store with a fixed list before exercising
  snapshot tests for search mode.
- **`#note` VOSS.md heading:** `## Notes` — heading created if absent. No other
  section of `VOSS.md` is touched. Uses `voss_md`/`memory_cli` section-aware
  append — do not open a raw file handle.
- **No-vision notice lifetime:** 3000ms auto-remove OR next submit, whichever
  fires first. Implement as a `call_later(3.0, block.remove)` on the
  `LocalBlockNotice` after mount.
- **Image attachment state** lives in the InputBar widget only (not persisted,
  not in recorder unless the model turn fires). If the user clears the input
  bar manually before submitting, the attachment is discarded silently.
- **Clipboard shim:** planner chooses between `PIL.ImageGrab`, `pyperclip` with
  image extension, or a thin platform shim. Constraint: hermetic-testable (mockable
  clipboard probe); graceful no-op where clipboard-image is unsupported (falls
  back to text paste with no error block).
