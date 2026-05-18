---
phase: T8-input-bar-ergonomics-v0-2
plan: 02
type: execute
wave: 1
depends_on: ["T8-01"]
files_modified:
  - voss/harness/tui/widgets/input_bar.py
  - voss/harness/tui/styles.tcss
  - voss/harness/tui/keymap.py
  - tests/harness/tui/test_input_bar_textarea.py
  - tests/harness/tui/snapshots
autonomous: true
requirements: [INPUT-01]
user_setup: []

must_haves:
  truths:
    - "InputBar is a Widget container holding a TextArea child; it exposes a .text property and no .value"
    - "Enter submits (posts Submitted with full multi-line value); Shift+Enter inserts a newline"
    - "Slash palette opens only when the bar is empty; non-empty bar inserts a literal /"
    - "Bar autogrows 1→5 rows then scrolls internally; prompt glyph appears only on row 1"
    - "keymap.py gains exactly one additive line: Binding('ctrl+r','input','reverse_search',...) and no other row changes"
  artifacts:
    - path: "voss/harness/tui/widgets/input_bar.py"
      provides: "TextArea-based InputBar with preserved Submitted contract + slash guard"
      contains: "class InputBar"
      min_lines: 60
    - path: "voss/harness/tui/styles.tcss"
      provides: "#input height:auto autogrow contract"
      contains: "height: auto"
    - path: "voss/harness/tui/keymap.py"
      provides: "additive ctrl+r input binding"
      contains: "reverse_search"
  key_links:
    - from: "voss/harness/tui/widgets/input_bar.py"
      to: "textual.widgets.TextArea"
      via: "InputBar composes a child TextArea; _on_key intercepts enter before super()"
      pattern: "TextArea"
    - from: "voss/harness/tui/widgets/input_bar.py"
      to: "InputBar.Submitted"
      via: "action_submit posts Submitted(value: str) preserved verbatim"
      pattern: "Submitted\\(.*value"
    - from: "voss/harness/tui/keymap.py"
      to: "VossTUIApp.BINDINGS"
      via: "KEYMAP tuple comprehension in app.py filters context=='input'"
      pattern: "Binding\\(\"ctrl\\+r\", \"input\""
---

<objective>
Swap `InputBar` from single-line Textual `Input` to a `Widget` container holding a `TextArea` child (D-01), implement the Enter/Shift+Enter key inversion (M9-locked semantics, RESEARCH Pitfall — TextArea maps Enter→newline in `_on_key`), the autogrow 1→5-row tcss contract (D-02), the preserved `/`-palette empty-guard, and add the single additive `ctrl+r` keymap binding. This is the load-bearing change all other T8 behaviors build on.

Purpose: INPUT-01 — multi-line input with M9-locked Enter=submit / Shift+Enter=newline, without rewriting the M9 keymap table.
Output: rewritten input_bar.py, one-line styles.tcss change, one-line keymap.py addition, green INPUT-01 tests + baseline snapshots 1-4.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/T8-input-bar-ergonomics-v0-2/T8-RESEARCH.md
@.planning/phases/T8-input-bar-ergonomics-v0-2/T8-PATTERNS.md
@.planning/phases/T8-input-bar-ergonomics-v0-2/T8-UI-SPEC.md
@.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md
@.planning/phases/T8-input-bar-ergonomics-v0-2/T8-01-SUMMARY.md

<interfaces>
Current voss/harness/tui/widgets/input_bar.py (VERIFIED — full file is the analog):
- `class InputBar(Input)`; `BINDINGS = [("slash","open_palette",...)]`
- `class Submitted(Message): __init__(self, value: str)` — M9-LOCKED, field `value: str`, do NOT rename
- `async def _on_key(self, event)` — slash guard: `if event.key=="slash" and not self.value: prevent_default/stop/action_open_palette/return; await super()._on_key(event)`
- `async def action_submit(self)` — `value=self.value; await super().action_submit(); if value.strip(): self.post_message(self.Submitted(value))`
- `def action_open_palette(self)` — `if self.value: self.insert_text_at_cursor("/"); return` then mounts `SlashPalette(registry)` via `self.app.mount(palette, before=self)`
- module imports `from .. import glyphs`; `glyphs.PROMPT` is the `▌` glyph

Textual 8.2.6 TextArea API (VERIFIED via source inspection):
- `TextArea._on_key` maps `"enter"` → `"\n"` insert internally; overriding BINDINGS does NOT prevent it — must `event.prevent_default()` + `event.stop()` BEFORE `super()._on_key()`
- `TextArea.text` property → full document string; `TextArea.load_text(s)` replaces + clears undo; `TextArea.insert(s)` inserts at cursor
- TextArea has NO `.value`; TextArea.BINDINGS includes `ctrl+f→delete_word_right` (Pitfall 2) and `ctrl+u→delete_to_start_of_line` (Pitfall 1)

Current styles.tcss `#input` block (lines 49-54): `dock: bottom; height: 1; min-height: 1; max-height: 5;`

keymap.py KEYMAP tuple (lines 20-38): frozen `Binding(key, context, action, description)` dataclass; existing `input`-context rows are enter/shift+enter/slash (lines 23-25); `ctrl+f` is `main`-context (line 35, MUST NOT move).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Rewrite InputBar onto TextArea with key inversion + slash guard</name>
  <behavior>
    - Enter on non-empty bar → posts InputBar.Submitted(value) with the full (possibly multi-line) text; TextArea does NOT insert a newline
    - Shift+Enter → inserts "\n" at cursor; no Submitted posted
    - "/" pressed when bar text is empty → opens SlashPalette; bar text non-empty → literal "/" inserted, palette NOT opened
    - InputBar exposes a `.text` property returning the child TextArea content; `.value` attribute is absent
    - Empty/whitespace-only bar + Enter → no Submitted posted (no-op)
  </behavior>
  <read_first>
    - voss/harness/tui/widgets/input_bar.py (full current file — the exact analog being rewritten)
    - T8-RESEARCH.md Pattern 1 (Enter-key inversion — verified intercept order), Pattern 2 (TextArea text access), Pattern 4 (prompt-glyph via Static child at row0/col0, A1 ASSUMED), Pattern 5 (action_submit structure), Pitfall 2 (`ctrl+f` shadow — remove from child TextArea.BINDINGS or rely on focus-context separation), Pitfall 3 (`.value` → `.text`)
    - T8-PATTERNS.md §"input_bar.py" (Submitted contract preserve-exactly, _on_key intercept discipline, action_open_palette rewire: `self.query_one(TextArea).text.strip()` + `.insert("/")`)
    - T8-UI-SPEC.md §"INPUT-01 — TextArea swap interaction contract", §"Component Inventory" (InputBar row)
  </read_first>
  <action>Rewrite `input_bar.py`: `InputBar(Widget)` with a `compose()` yielding a `Static` prompt-glyph label (`glyphs.PROMPT + " "`, `classes="accent"`, id `prompt-glyph`) and a child `TextArea` (id `input-textarea`). Preserve the `Submitted(Message)` class verbatim (`value: str`). Expose a `.text` property delegating to `self.query_one(TextArea).text`. Override `_on_key` to intercept, in order, BEFORE `await super()._on_key(event)` and using `event.prevent_default(); event.stop()` then `return` per branch: `enter` (not in search mode — `self._search_mode` flag default False, reserved for Plan 05) → `await self.action_submit()`; `shift+enter` → child `TextArea.insert("\n")`; `slash` with empty `TextArea.text.strip()` → `self.action_open_palette()`. Rewrite `action_submit` to read `self.text`, `load_text("")` to clear, and `post_message(self.Submitted(value))` only when stripped value is non-empty (no `super().action_submit()` — TextArea has none). Rewrite `action_open_palette` per PATTERNS: non-empty guard via `self.query_one(TextArea).text.strip()`, literal insert via `self.query_one(TextArea).insert("/")`, palette mount unchanged. Subclass the child TextArea to drop `ctrl+f`/`ctrl+u` from its `BINDINGS` (Pitfall 1/2) so M9 `main`-context bindings are never shadowed. Keep `from __future__ import annotations` and `# noqa: BLE001` on bare excepts (Shared Patterns). Add the new `Binding("ctrl+r", "input", "reverse_search", "Reverse-search input history")` line to the KEYMAP tuple in `keymap.py` AFTER the existing `slash` input row — exactly one line added, no other row touched (the `reverse_search` action itself lands in Plan 05; the binding is additive here so app.BINDINGS picks it up).</action>
  <verify>
    <automated>pytest tests/harness/tui/test_input_bar_textarea.py tests/harness/tui/test_keymap_baseline.py tests/harness/tui/test_slash_palette.py -q -x</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/tui/test_input_bar_textarea.py -q` — INPUT-01 unit tests (Enter submits, Shift+Enter newline, .text present, .value absent, slash guard) PASS (xfail markers removed for these by this task)
    - `pytest tests/harness/tui/test_slash_palette.py tests/harness/tui/test_full_flow_pilot.py -q` exits 0 (migrated tests still pass against the new TextArea widget)
    - `grep -c 'class Submitted' voss/harness/tui/widgets/input_bar.py` returns 1 and `grep 'def __init__(self, value: str)' voss/harness/tui/widgets/input_bar.py` matches (contract preserved)
    - `grep -v '^#' voss/harness/tui/keymap.py | grep -c 'reverse_search'` returns 1; `git diff voss/harness/tui/keymap.py` shows exactly one added line (no deletions, no modified rows) — verified by `git diff --numstat voss/harness/tui/keymap.py` showing `1\t0`
    - `python -c "from voss.harness.tui.widgets.input_bar import InputBar; assert not hasattr(InputBar, 'value')"` exits 0
  </acceptance_criteria>
  <done>InputBar is TextArea-backed; Enter/Shift+Enter inverted; slash guard preserved; Submitted contract intact; one additive keymap line.</done>
</task>

<task type="auto">
  <name>Task 2: Autogrow tcss + prompt-glyph layout + baseline snapshots 1-4</name>
  <read_first>
    - voss/harness/tui/styles.tcss lines 49-54 (the `#input` block — only `height: 1` → `height: auto` changes; the 5-hex-palette comment block at top must NOT gain entries)
    - T8-UI-SPEC.md §"Layout / Spacing > Input bar height contract", §"Snapshot-Test Anchors" (anchors 1-4: single-line glyph at col0, 3-row glyph-only-row-1, 5-row cap, slash-palette guard)
    - T8-RESEARCH.md Pattern 3 (autogrow via `height: auto; min-height:1; max-height:5` — no Python), Pitfall 8 (`--snapshot-update` on first run; baseline SVGs committed)
    - T8-PATTERNS.md §"styles.tcss" (replace `height: 1` only; append no classes here — Plan 03 adds local-block classes), §"Snapshot Tests" (snap_compare fixture pattern)
  </read_first>
  <action>In `styles.tcss`, change the `#input` block's `height: 1` to `height: auto` (keep `dock: bottom; min-height: 1; max-height: 5;` unchanged). This is the ONLY edit to styles.tcss in this plan — do NOT add the `.local-block*`/`.reverse-search-bar` classes (Plan 03/05 own those) and do NOT add palette hex entries. Ensure the prompt-glyph `Static` only renders on row 1 by giving it the layout from UI-SPEC §"Input bar height contract" (glyph + space at col 0 row 0; rows 2-5 unprefixed — the TextArea owns rows; the Static is a sibling at the container's top-left). Fill the INPUT-01 snapshot tests in `test_input_bar_textarea.py` to use the `snap_compare` fixture for the 4 anchors (single-line, 3-row multi-line, 5-row cap, slash-palette-guard), then run `pytest tests/harness/tui/ --snapshot-update -k "snap1 or snap2 or snap3 or snap4"` to generate the baseline SVGs and commit them under the snapshots package dir. Remove the `xfail` markers on these four tests.</action>
  <verify>
    <automated>pytest tests/harness/tui/test_input_bar_textarea.py -q -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -v '^#' voss/harness/tui/styles.tcss | grep -c 'height: auto'` returns 1; `grep -v '^#' voss/harness/tui/styles.tcss | grep -c '#[0-9A-Fa-f]\{6\}'` returns exactly 5 (palette unchanged — UI-SPEC Acceptance Check)
    - `git diff --numstat voss/harness/tui/styles.tcss` shows `1\t1` (exactly one line changed: `height: 1`→`height: auto`)
    - `pytest tests/harness/tui/test_input_bar_textarea.py -q` exits 0 — all INPUT-01 tests + 4 snapshot anchors green; baseline SVGs exist under `tests/harness/tui/snapshots/`
    - `git status --porcelain tests/harness/tui/snapshots/` shows the 4 generated baseline files staged/added
  </acceptance_criteria>
  <done>Autogrow contract in tcss (1-line change, palette intact); 4 INPUT-01 snapshot anchors green with committed baselines.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user keystroke → InputBar | untrusted text/keys enter the widget; submitted value crosses to run_turn (wired in Plan 04) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T8-03 | Tampering | keymap.py M9 source-of-truth | mitigate | exactly one additive `Binding` line; `git diff --numstat` gate asserts `1\t0` (no rows rewritten/rebound); enter/shift+enter/slash/ctrl+f rows untouched |
| T-T8-04 | Elevation of privilege | TextArea child shadowing M9 `ctrl+f`/`ctrl+u` `main`-context bindings | mitigate | child TextArea subclass strips `ctrl+f`/`ctrl+u` from its BINDINGS (Pitfall 1/2); contexts are focus-exclusive but the strip is belt-and-suspenders |
| T-T8-05 | Spoofing | multi-line submitted value | accept | value is rendered/forwarded as plain `Text` (no markup) downstream; Submitted carries an opaque `str` — no injection surface at the widget tier |
| T-T8-SC | Tampering | npm/pip installs | mitigate | no package installs in this plan (Plan 01 owns dev-dep install); slopcheck + blocking human checkpoint N/A |
</threat_model>

<verification>
- `pytest tests/harness/tui/test_input_bar_textarea.py -q` exits 0 (INPUT-01 unit + 4 snapshot anchors)
- `pytest tests/harness/tui/test_slash_palette.py tests/harness/tui/test_full_flow_pilot.py tests/harness/tui/test_keymap_baseline.py -q` exits 0 (no M9 regression)
- `git diff --numstat voss/harness/tui/keymap.py` == `1\t0`; `git diff --numstat voss/harness/tui/styles.tcss` == `1\t1`
</verification>

<success_criteria>
- InputBar is TextArea-backed, `.text` exposed, `.value` gone, Submitted contract verbatim
- Enter=submit / Shift+Enter=newline / empty-slash-guard all hold
- Autogrow 1-5 rows; glyph row-1 only; 4 INPUT-01 snapshot anchors green
- keymap.py change is exactly one additive line; M9 contract intact
</success_criteria>

<output>
Create `.planning/phases/T8-input-bar-ergonomics-v0-2/T8-02-SUMMARY.md` when done
</output>
