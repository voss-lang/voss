# Handoff: Textual TUI (`voss chat`) fixes — perf + slash palette

**Created:** 2026-06-03
**Scope:** Fix the EXISTING Textual TUI (`voss chat`) — the good, orange-VOSS-branded UI. This is `voss/harness/tui/`. NOT the Rust `voss-tui` (boxy/ugly, demoted to fallback) and NOT the OpenCode fork (paused — possibly unnecessary now that we confirmed the Textual TUI is intact and nice).

**Run it:** `.venv/bin/voss chat`  (or `.venv/bin/python -m voss.cli chat`)

**Status note:** large body of hybrid/server work is UNCOMMITTED on `dev`. Commit before/after these fixes as you prefer. These TUI fixes are independent of all that.

---

## Bug 1 — Slash palette: no filter-as-you-type, no dismiss on `/` deletion

### Repro
1. `voss chat`, focus input.
2. Type `/` → palette opens (good), lists `/agent /agents /analyze /apply /btrace …`.
3. Type more (e.g. `/s`) → palette does NOT filter to matching commands.
4. Backspace the leading `/` (input becomes e.g. `s`) → palette STAYS open + unfiltered (should dismiss). Screenshot showed input `s` with full unfiltered palette still up.

### Root cause (confirmed)
The palette is a separate `ListView` widget mounted on the `/` **keydown**, with a working filter method that is **never called on text change**:
- Open trigger: `voss/harness/tui/widgets/input_bar.py:102` (and `:245`) → `action_open_palette()` (`:394`) mounts `SlashPalette` before the input (`:411-412`).
- Filter method EXISTS but is unwired: `voss/harness/tui/widgets/slash_palette.py:78` `update_query(query)` (rebuilds children — see note in §perf).
- Dismiss paths: only `action_dismiss` on Escape (`slash_palette.py:62,109-116`) or submit (`:107`). **No dismiss when the leading `/` is removed.**
- `InputBar` has NO text-change handler (grep for `on_*changed` in `input_bar.py` → none). So neither filter nor conditional-dismiss ever fires.

### Fix (concrete)
Add a TextArea change handler in `InputBar` (the input is a Textual `TextArea` subclass `_InputTextArea`, id `#input-textarea`, `input_bar.py:185`). On every change:
- Let `text = textarea.text`.
- If `text.startswith("/")`: ensure palette is open (open it if not), then `palette.update_query(text)` to filter live.
- Else (no leading `/`): if a `SlashPalette` is mounted, `palette.remove()` (dismiss).

Textual hook: implement `on_text_area_changed(self, event)` on `_InputTextArea` or `InputBar`, or a `@on(TextArea.Changed)` handler. Note `_InputTextArea._on_key` (`:75`) already intercepts keys — but use the **Changed** message (post-mutation) for filter/dismiss, not key interception (backspace must be observed AFTER it edits the buffer).
Watch out: opening the palette currently happens on the `slash` KEY (`:102`), so the first `/` opens via keydown while subsequent filtering must go via Changed — make sure both paths converge on one "sync palette to text" function to avoid double-open. Consider moving ALL open/filter/close logic into the single Changed handler and dropping the key-based open (cleaner).

### Verify
- Type `/` → opens. `/ag` → filters to `/agent /agents`. Backspace to `` → dismisses. Backspace `/` out of `/foo` leaving `foo` → dismisses.
- Add a Textual snapshot test (repo uses `pytest-textual-snapshot`, see existing `tests/harness/` TUI tests) or a unit test driving `update_query` + the new handler.

---

## Bug 2 — Performance / laggy typing

### Symptom
Typing feels slow/laggy in the TUI.

### Investigate first (don't guess — profile)
- Run with Textual devtools: `textual run --dev -c .venv/bin/voss chat` in one pane + `textual console` in another → watch for excessive refresh/render messages per keystroke.
- Likely culprits to check, in order:
  1. **Slash palette child rebuild**: `slash_palette.py:82-96` "remove children directly" rebuilds the ListView on every `update_query`. Once Bug 1 wires filtering to every keystroke, this rebuild runs per-char → can be janky. Prefer hiding/showing existing `ListItem`s (toggle `.display`) or diffing, instead of remove+re-add all children.
  2. **TextArea input**: the input is a full `TextArea` (`_InputTextArea`, `input_bar.py`), heavier than Textual's `Input`. For a single-line prompt a lighter widget may help; but multi-line (Shift+Enter, T8) is a requirement, so measure before swapping.
  3. **App-level refresh**: only one `self.refresh()` found (`app.py:120`, in interrupt path) — not per-keystroke, so probably not the cause. Confirm no `recompose`/full re-render on common events.
  4. **VOSS ASCII art / welcome widget**: if it re-renders on every layout pass, cache it. Find the welcome/empty-state widget (renders the figlet "VOSS v1 / type a message below to begin"); confirm it isn't recomputing the art each refresh.
  5. **Terminal/host**: confirm it's not just a slow terminal emulator / SSH. Compare in a fast local terminal.

### Likely highest-value fix
Make `SlashPalette.update_query` cheap (toggle visibility, don't rebuild children) — this compounds with Bug 1 since filtering will now run per-keystroke.

### Verify
- Devtools shows ≤1 render per keystroke; typing feels instant. No measurable lag with palette open while typing.

---

## Key files
- `voss/harness/tui/widgets/input_bar.py` — input (`_InputTextArea`, `InputBar`), palette open triggers (`:102,:245,:394`).
- `voss/harness/tui/widgets/slash_palette.py` — palette, `update_query` (`:78`), dismiss (`:109`), child rebuild (`:82-96`).
- `voss/harness/tui/app.py` — `VossTUIApp` (refresh at `:120`).
- `voss/harness/tui/styles.tcss` — TCSS (heights/padding recently tuned).
- `voss/harness/tui/renderer.py` — `TextualRenderer` (agent events → UI), not relevant to these two bugs.
- TUI tests: `tests/harness/` (pytest-textual-snapshot available).

## Don't redo
- The Textual TUI is intact + the default for `voss chat`; do NOT rebuild it. These are two scoped bugs.
- Ignore the Rust `voss-tui` and OpenCode-fork tracks for this work (separate; see memory `voss-opencode-tui-fork`, `voss-harness-hybrid-refactor`).

---

## REVIEW FINDINGS (2026-06-03, 13-agent adversarial review of commits 9cb7a79 / 4896f9d / 996a4a9)

Swarm implemented the core asks correctly: **filter-as-you-type ✓, dismiss-on-`/`-delete ✓, perf toggle-visibility ✓.** One HIGH regression introduced by the focus fix.

### 🔴 HIGH — palette is non-interactive (can't select a command)
`_sync_slash_palette` refocuses the textarea on EVERY `TextArea.Changed` (`input_bar.py:299`, added in 4896f9d) → palette never holds focus → Enter/arrows/Escape never reach it (reproduced via Textual pilot):
- Enter dispatches raw input text (e.g. bare `/`) as a turn instead of the highlighted command. Palette submit path `slash_palette.py:147-161` → `app.py:325 on_slash_palette_palette_submitted` is DEAD.
- Arrow keys don't navigate (`palette.index` stays 0). Escape doesn't dismiss.
- All 15 palette tests pass but NONE drive selection via pilot keystrokes — regression shipped green.
- **VERIFIED: removing line 299 alone does NOT fix it** (focus leaves textarea, never reaches palette). Must add an interaction model:
  - (a) keep textarea focus + forward up/down/enter/escape from `InputBar._on_key` to the mounted `SlashPalette` (Enter → select highlighted, not `action_submit` raw text), OR
  - (b) focus the palette on open + route printable keys/backspace back to the textarea (its native ListView bindings then work).
- **Add a pilot test**: press `/`, `down`, `enter` → assert `on_slash_palette_palette_submitted` fired with the highlighted command (e.g. `/agents`), NOT a raw `/` turn dispatch. (This gap is why it shipped green.)

### 🟡 MEDIUM — Escape doesn't dismiss palette
Same root cause (focus steal). `SlashPalette` escape→dismiss binding (`slash_palette.py:62`) unreachable; App-level `escape→dismiss_modal` (`app.py:113`, `keymap.py:27`) no-ops (palette is a mounted widget, not a Screen). Fixed by the same interaction-model fix, or handle Escape in `InputBar._on_key` while a palette is mounted → `palette.action_dismiss()`. Workaround today: backspace the leading `/`.

### ⚪ LOW — dead keymap binding
`slash→open_palette` (`keymap.py:25`) + `action_open_palette` (`input_bar.py:414`) now redundant (Changed handler drives open). Remove, or keep solely so the help overlay lists `/`. Not a blocker.
