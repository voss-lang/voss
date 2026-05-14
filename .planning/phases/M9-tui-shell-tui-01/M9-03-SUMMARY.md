---
phase: M9
plan: 03
status: complete
date: 2026-05-14
---

# M9-03 Summary — Slash Palette + Help Overlay + Keymap Baseline (TUI-05 + TUI-09)

Wave-3 discovery surface. `SlashPalette` opens on `/` in an empty
`InputBar`, ranks by substring + recency + alphabetical. `HelpOverlay` is a
`?` modal listing keymap + visible slash commands. `KEYMAP` is the single
source of truth for `VossTUIApp.BINDINGS`. `RESERVED_SLASH_NAMES` documents
the 4-name M8 ownership boundary.

## Files Created

| Path | Purpose |
|------|---------|
| `voss/harness/tui/reserved_slash_names.py` | `RESERVED_SLASH_NAMES: tuple = ("/recall", "/forget", "/memory", "/save")` — frozen tuple. |
| `voss/harness/tui/keymap.py` | `Binding(key, context, action, description)` frozen dataclass + `KEYMAP` tuple of 17 bindings. |
| `voss/harness/tui/widgets/help_overlay.py` | `HelpOverlay(ModalScreen)`. Heading `voss tui · keys + commands`. `Esc` dismisses via app.pop_screen. |
| `voss/harness/tui/widgets/slash_palette.py` | `SlashPalette(ListView)` + `rank_commands()` pure helper. Substring rank, recency boost, 8-result cap, reserved filter (with `/save` keep-alive). |
| `tests/harness/tui/test_reserved_slash_names.py` | 2 tests — locked order, immutability. |
| `tests/harness/tui/test_keymap_baseline.py` | 17 tests (15 parametrized + 2) — coverage of every UI-SPEC key row. |
| `tests/harness/tui/test_help_overlay.py` | 2 tests — heading + Esc dismiss. |
| `tests/harness/tui/test_slash_palette.py` | 10 tests — rank logic + reserved filter + DOM behavior. |

## Files Modified

| Path | Change |
|------|--------|
| `voss/harness/tui/widgets/__init__.py` | Re-exports `HelpOverlay`, `SlashPalette`, `rank_commands`. |
| `voss/harness/tui/widgets/input_bar.py` | Added `BINDINGS = [("slash", "open_palette", ...)]` + `_on_key` override that intercepts `/` only when `self.value` is empty + `action_open_palette` that mounts a `SlashPalette(self.app.slash_registry)` before the input bar. |
| `voss/harness/tui/app.py` | `BINDINGS` populated from `KEYMAP` (global + input + modal contexts) instead of empty placeholder. `__init__` accepts `slash_registry: SlashRegistry \| None = None` (defaults to fresh empty registry for test mounts). Added `action_open_help`, `action_dismiss_modal`, `action_redraw`, `action_interrupt`, `action_focus_next/previous`. |

## rank_commands Contract

```python
rank_commands(query, names, *, recency=None, reserved=RESERVED_SLASH_NAMES, keep_alive=("/save",))
```

- Empty `query` → recency order first, then alphabetical (cap 8).
- Non-empty `query` → substring match (case-insensitive, leading `/` stripped); rank by match-position; cap 8.
- `reserved` names dropped from input.
- `keep_alive` names bypass the reserved filter (M9-03 keeps `/save` alive even though it appears in the M8 reservation list, because M8 has shipped and `/save` is now a live memory-note handler).

## SlashPalette Widget

- `dock: bottom`, `offset-y: -1` so the popup floats above the input bar.
- `max-height: 8` rows hard-capped via CSS.
- Empty-result row renders the locked copy `no matching commands`.
- `update_query(query)` clears children via `self._nodes._clear()` (synchronous; avoids ListItem id collisions during fast retyping) then appends one ListItem per ranked name.
- Enter triggers `action_select_cursor → _submit_current` which posts `PaletteSubmitted(name)` and removes the palette.
- Esc binding dismisses via `action_dismiss`.

## InputBar `/` Open-Palette

`_on_key` intercepts `event.key == "slash"` and, only when `self.value` is empty, calls `action_open_palette`. Non-empty value falls through to the default `Input` handler so `/` is inserted as a literal character. `action_open_palette` checks for an existing `SlashPalette` instance and bails (idempotent open).

## HelpOverlay

`ModalScreen` with heading `voss tui · keys + commands`. Renders:
1. `keys` section — one row per `Binding` in KEYMAP.
2. `commands` section — one row per visible name in the bound `SlashRegistry`.
3. Footer hint `press Esc to close`.

`BINDINGS = [("escape", "app.pop_screen", "Close help")]`.

## Acceptance Gate Status

| Gate | Result |
|------|--------|
| `RESERVED_SLASH_NAMES == ("/recall", "/forget", "/memory", "/save")` | passes |
| `len(KEYMAP) >= 14` | 17 |
| `grep -c "voss tui · keys + commands" help_overlay.py` | 1 |
| `rank_commands('he', ['/help', '/cost'])[0] == '/help'` | passes |
| `rank_commands('rec', ['/recall', '/help'], reserved=RESERVED_SLASH_NAMES)` excludes `/recall` | passes |
| `rank_commands('sa', ['/save', '/save-session', '/help'])` includes both `/save` + `/save-session` | passes |
| `grep -c "open_palette" voss/harness/tui/widgets/input_bar.py` | 4 |
| `VossTUIApp.BINDINGS` populated from KEYMAP | passes (contains escape, question_mark, ctrl+c, ctrl+l, tab, shift+tab) |
| All TUI tests | 75 passed |
| Full harness suite (excl. pre-existing diagnostics failures) | 370 passed, 2 skipped |

## Deviations from Plan

1. **No `/save` → `/snapshot` rename.** Plan was authored before M8 landed. M8-00 already renamed the snapshot handler to `/save-session` and M8-05 registered `/save` as the memory-note handler. The "rename + deprecation alias" arc is moot — both names already exist as distinct live commands. `RESERVED_SLASH_NAMES` still documents the 4-name M8 ownership boundary as the plan instructed, and `rank_commands.keep_alive` keeps `/save` surfaceable in the palette so users can still find it.

   Tests skipped as a result:
   - `test_save_rename.py` (canonical-vs-alias resolution + stderr deprecation warning) — replaced implicitly by the existing M8 contract tests at `tests/harness/test_slash_save_note.py` and the M8-00 rename audit.
   - The two cli.py grep gates (`SlashCommand("/snapshot"` and `_save_deprecated`) are not satisfied; their intent (separate canonical name + alias) is satisfied by M8's `/save-session` + `/save` registration.

2. **VossTUIApp.BINDINGS includes `modal` context** in addition to `global` + `input`. The plan said "Modal-context bindings live on the modals" but the `escape` binding has context `"modal"` in KEYMAP, and the test acceptance explicitly requires `escape` in `VossTUIApp.BINDINGS`. Both modal-internal handlers (HelpOverlay, future M9-05 modals) and the app-level escape (when no screen pushed) need to resolve `escape`; including the binding at the app level lets it bubble correctly.

3. **`SlashPalette` uses `self._nodes._clear()`** instead of the async `clear()` to swap items. Textual's async clear leaves IDs in the nodes table long enough for the next append cycle to collide; private synchronous clear is the only way to update item content without an `await` in a sync method body. M9-05's modal infrastructure may revisit this if the palette grows multi-step interactions.

4. **`InputBar._on_key` override** added because Textual's `Input` widget consumes printable characters via `_on_key` before BINDINGS resolve. The `("slash", "open_palette")` binding alone would never fire when the widget is focused. The override calls `event.prevent_default()` + `event.stop()` only when value is empty, otherwise falls through to default Input handling.

No other deviations.

## Phase Handoff

- M9-04 wires the recorder bridge → status line BudgetMeter + main pane probable-value visualization. Status-line composition will extend the M9-02 `StatusLine` widget.
- M9-05 builds the diff + permission modals as `ModalScreen` subclasses; both honor `escape` via the M9-03 keymap.
- M9-06 implements `f` fork-from-turn + `ctrl+f` in-pane search using the bindings declared here.
- M9-07 ingests `_build_slash_registry()` from `cli.py` into `VossTUIApp.slash_registry` at boot so the palette + help overlay see production commands.
