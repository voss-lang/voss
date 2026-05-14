---
phase: M9
plan: 03
type: execute
wave: 3
depends_on: [M9-02]
files_modified:
  - voss/harness/tui/widgets/slash_palette.py
  - voss/harness/tui/widgets/help_overlay.py
  - voss/harness/tui/widgets/__init__.py
  - voss/harness/tui/widgets/input_bar.py
  - voss/harness/tui/app.py
  - voss/harness/tui/keymap.py
  - voss/harness/tui/reserved_slash_names.py
  - voss/harness/cli.py
  - tests/harness/tui/test_slash_palette.py
  - tests/harness/tui/test_help_overlay.py
  - tests/harness/tui/test_reserved_slash_names.py
  - tests/harness/tui/test_keymap_baseline.py
  - tests/harness/tui/test_save_rename.py
autonomous: true
requirements: [TUI-05, TUI-09]
must_haves:
  truths:
    - "Typing `/` in InputBar opens a popup palette ranked by fuzzy match over the slash registry."
    - "Palette never registers /recall, /forget, /memory, or /save — the full M8 reservation list (4 names) is honored per CONTEXT.md."
    - "Live slash command `/save` (persist session snapshot) is renamed to `/snapshot`; `/save` is now registered as a deprecation-alias to `/snapshot` for one release, then will be removed when M8 lands."
    - "Pressing `?` from any non-modal state opens the help overlay listing every binding + visible slash command."
    - "Vim navigation keys (j, k, g, G, Ctrl-d, Ctrl-u) scroll the main pane when it has focus."
    - "Esc dismisses the palette and the help overlay without submitting input."
    - "InputBar (M9-02) now owns the `/` open-palette binding; VossTUIApp.BINDINGS is populated from KEYMAP."
  artifacts:
    - path: "voss/harness/tui/widgets/slash_palette.py"
      provides: "SlashPalette popup widget; wraps voss/harness/slash.py registry; fuzzy ranking + recency weight"
      exports: ["SlashPalette", "rank_commands"]
    - path: "voss/harness/tui/widgets/help_overlay.py"
      provides: "HelpOverlay modal-style screen showing keymap + visible slash commands"
      exports: ["HelpOverlay"]
    - path: "voss/harness/tui/keymap.py"
      provides: "Locked keymap table (key, context, action) — single source of truth for bindings"
      exports: ["KEYMAP", "Binding"]
    - path: "voss/harness/tui/reserved_slash_names.py"
      provides: "Frozen tuple of slash names reserved for downstream phases (M8 memory) — full 4-name list"
      exports: ["RESERVED_SLASH_NAMES"]
  key_links:
    - from: "voss/harness/tui/widgets/slash_palette.py"
      to: "voss/harness/slash.py:SlashRegistry"
      via: "SlashPalette.__init__(registry) calls registry.ids(include_hidden=False)"
      pattern: "registry.ids"
    - from: "voss/harness/tui/keymap.py"
      to: "voss/harness/tui/app.py:VossTUIApp.BINDINGS"
      via: "VossTUIApp.BINDINGS = [Binding(k.key, k.action, k.description) for k in KEYMAP]"
      pattern: "BINDINGS"
    - from: "voss/harness/cli.py"
      to: "voss/harness/cli.py:_build_slash_registry"
      via: "live `/save` handler is re-registered under name `/snapshot`; an alias entry under `/save` emits a deprecation warning and forwards to the same handler"
      pattern: "SlashCommand\\(\"/snapshot\""
---

<objective>
Build the slash command palette + help overlay + the keymap baseline that downstream plans (M9-04 viz, M9-05 modals, M9-06 fork-from-turn) extend. Lock the full 4-name reserved slash list for M8 in a frozen module so the palette + auditor in M9-07 can both grep it. Rename the existing live `/save` slash command to `/snapshot` (user decision on checker warning W2) so the M8 reservation of `/save` is honored without scope reduction; keep `/save` registered as a deprecation alias for one release.

Purpose: TUI-05 and the discovery side of TUI-09. The palette is the user's only way to find non-obvious commands; the help overlay is the only way to discover keys. Both are required for "feels like Claude Code / Aider depth" per CONTEXT. Also resolves checker B3 (declare wiring files honestly) and W2 (free `/save` for M8 by renaming the live command).

Output: SlashPalette + HelpOverlay widgets + KEYMAP table + reserved-name allow-list (4 names) + live `/save` → `/snapshot` rename + alias + 5 test files.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md
@.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md
@voss/harness/slash.py
@voss/harness/cli.py

<interfaces>
<!-- Slash registry the palette wraps (from voss/harness/slash.py): -->

```python
@dataclass(frozen=True)
class SlashCommand:
    name: str           # e.g. "/help"
    help: str
    handler: SlashHandler
    aliases: tuple[str, ...] = ()
    mutating: bool = False
    hidden: bool = False

class SlashRegistry:
    def register(self, command: SlashCommand) -> None: ...
    def lookup(self, name: str) -> SlashCommand | None: ...
    def ids(self, *, include_hidden: bool = False) -> list[str]: ...
    def help_lines(self) -> list[str]: ...
    def dispatch(self, ctx: Any, line: str) -> bool: ...
```

<!-- Current registered slash names in cli.py:_build_slash_registry (lines 462-482): -->
/help, /exit (alias /quit), /clear, /cost, /tools, /login, /model, /mode, /save (mutating), /analyze, /save-plan, /plugins, /plugin, /skills, /skill, /agents, /agent

<!-- Key observation: SlashCommand supports an `aliases` tuple field. The rename uses this — `/snapshot` becomes the canonical name; `/save` becomes either a deprecation alias entry or a separate registration that emits a stderr warning before dispatching the same _save handler. -->

<!-- UI-SPEC locked keymap table — full row list reproduced below from UI-SPEC "Keybindings" -->
| Key | Context | Action |
| Tab / Shift+Tab | global (no modal) | Cycle focus regions |
| Enter | input bar | Submit task |
| Shift+Enter | input bar | Insert newline |
| / | input bar (when empty) | Open slash palette |
| Esc | any modal | Close modal (deny / cancel) |
| ? | global (no modal) | Open help overlay |
| j / k | main pane | Scroll one row down / up |
| Ctrl+d / Ctrl+u | main pane | Half-page down / up |
| g / G | main pane | Jump top / bottom |
| f | main pane, turn highlighted | Fork session from this turn (impl in M9-06) |
| Ctrl+f | main pane | In-pane search prompt (impl in M9-06) |
| y / n / s / a / q | diff modal | Diff actions (modal owns these — M9-05) |
| a / A / d | permission modal | Permission actions (modal owns — M9-05) |
| Ctrl+c | global | Interrupt turn; second press exits app |
| Ctrl+l | global | Redraw screen |
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Restore full 4-name RESERVED_SLASH_NAMES + rename live `/save` → `/snapshot` with deprecation alias + KEYMAP table + HelpOverlay widget</name>
  <files>voss/harness/tui/reserved_slash_names.py, voss/harness/tui/keymap.py, voss/harness/tui/widgets/help_overlay.py, voss/harness/tui/widgets/__init__.py, voss/harness/cli.py, tests/harness/tui/test_reserved_slash_names.py, tests/harness/tui/test_keymap_baseline.py, tests/harness/tui/test_help_overlay.py, tests/harness/tui/test_save_rename.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md (CONTEXT line 106: "Reserved slash command names for M8 (`/recall`, `/forget`, `/memory`, `/save`)" — 4 names, all reserved; CONTEXT line 49 mirrors this. Checker warning W2 user-decision: rename live `/save` → `/snapshot` to honor the full reservation.)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cli.py (line 411 `_save` handler definition; line 473 `SlashCommand("/save", "persist session snapshot", _save, mutating=True)` — this is the line that gets renamed to `/snapshot` plus a separate `/save` alias registration that emits a deprecation warning)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/slash.py (full file; confirm `aliases` field on SlashCommand and that the registry treats aliases as additional dispatch names without registering them as separate listed ids — if aliases ARE separate ids, use a wrapper handler instead)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md ("Help overlay header" copy + "Interaction Contract" Keybindings full table + "Empty side panel" copy)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/app.py (M9-02 — KEYMAP feeds into VossTUIApp.BINDINGS; this plan extends the placeholder `BINDINGS = []`)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/widgets/__init__.py (M9-02 — extend exports with HelpOverlay)
    - /Users/benjaminmarks/Projects/Voss/tests/harness/test_cognition.py (confirm: only references `/save-plan` and `_save_plan`, NOT bare `/save`. Verified via `grep -n '"/save"\\|line="/save"\\|/save\\b' tests/`. Rename does not break this file.)
  </read_first>
  <behavior>
    - Test (test_reserved_slash_names): `from voss.harness.tui.reserved_slash_names import RESERVED_SLASH_NAMES; assert RESERVED_SLASH_NAMES == ("/recall", "/forget", "/memory", "/save")`. Full 4-name list per CONTEXT.md and UI-SPEC.
    - Test: `RESERVED_SLASH_NAMES` is a tuple (immutable); attempting `RESERVED_SLASH_NAMES.append(...)` raises AttributeError.
    - Test (test_save_rename): `_build_slash_registry()` returns a registry whose `ids()` contains `/snapshot` AND `/save`. `registry.lookup("/snapshot").help == "persist session snapshot"`. `registry.lookup("/save").help` contains the substring `deprecated` (case-insensitive) AND `/snapshot`.
    - Test: dispatching `/save` writes a deprecation warning to stderr (capture via capsys) — exactly one line matching `^voss: /save is deprecated; use /snapshot \\(will be removed when M8 ships\\)$`, then proceeds with the same persistence side effect as `/snapshot`. Both `/save` and `/snapshot` MUST hit the same `_save` handler (no duplicated implementation).
    - Test: dispatching `/snapshot` writes NO deprecation warning to stderr.
    - Test: palette `rank_commands(query="sa", names=registry.ids())` returns `/save` after `/snapshot` (substring match) — both present, both rankable; M8 will replace `/save` with its own handler when it ships.
    - Test (test_keymap_baseline): `from voss.harness.tui.keymap import KEYMAP; assert len(KEYMAP) >= 14`; every UI-SPEC row from the Keybindings table is present (parametrized over expected (key, context_substring) tuples).
    - Test: each Binding has a non-empty `description` (used by HelpOverlay) and `action` (Textual action name).
    - Test (test_help_overlay): mount HelpOverlay(keymap=KEYMAP, registry=test_registry) inside a test app; query renders one row per Binding + one row per visible slash command; pressing Esc dismisses it. Both `/snapshot` and `/save` (with deprecated note) appear in the overlay's command list.
    - Test: HelpOverlay heading text is exactly `voss tui · keys + commands` (UI-SPEC locked copy).
  </behavior>
  <action>
    Edit `voss/harness/tui/reserved_slash_names.py` — restore the FULL 4-name list per CONTEXT.md (revert the conflict-resolution decision from the original plan; the conflict is now resolved at the registry level via the rename):
      ```python
      """Slash names reserved for downstream phases.

      M8 (Project Memory) will register /recall, /forget, /memory, /save. The TUI
      palette MUST NOT autocomplete to these names (the registry does still expose
      a deprecation-alias `/save` pointing at the renamed `/snapshot` until M8
      ships and takes ownership of `/save`).

      Order is locked: see CONTEXT.md "Reserved slash command names for M8".
      """
      from __future__ import annotations

      RESERVED_SLASH_NAMES: tuple[str, ...] = ("/recall", "/forget", "/memory", "/save")
      ```

    Edit `voss/harness/cli.py` `_build_slash_registry` (around line 473):
      - REPLACE the existing line `SlashCommand("/save", "persist session snapshot", _save, mutating=True)` with TWO registrations:
        1. `SlashCommand("/snapshot", "persist session snapshot", _save, mutating=True)` — canonical name.
        2. A deprecation-alias entry under `/save`. Two implementation options; pick the one that fits slash.py's existing surface:
           - Option A (preferred): a separate `SlashCommand("/save", "deprecated; use /snapshot", _save_deprecated, mutating=True, hidden=False)` where `_save_deprecated` is a thin wrapper defined immediately above the registry that writes one line to stderr `voss: /save is deprecated; use /snapshot (will be removed when M8 ships)` and then calls `_save(ctx, args, line)`.
           - Option B (if slash.py treats `aliases` tuple as registry-listed names): use `SlashCommand("/snapshot", ..., _save, aliases=("/save",))` plus a one-line wrapper on the dispatch path that detects the alias and warns. Use Option A unless slash.py already supports alias-emit hooks — confirm by reading slash.py first.
      - The `_save_deprecated` wrapper lives in cli.py adjacent to `_save` (around line 411). Signature matches `SlashHandler`. Body:
        ```python
        def _save_deprecated(ctx: ReplContext, args: list[str], line: str) -> None:
            import sys
            sys.stderr.write("voss: /save is deprecated; use /snapshot (will be removed when M8 ships)\n")
            return _save(ctx, args, line)
        ```
      - Do NOT delete or rename `_save` itself. `_save-plan` and any other handler is untouched.

    Create `voss/harness/tui/keymap.py`:
      ```python
      from dataclasses import dataclass

      @dataclass(frozen=True)
      class Binding:
          key: str           # textual key syntax e.g. "ctrl+d"
          context: str       # one of: "global", "input", "main", "diff", "permission"
          action: str        # textual action name e.g. "scroll_down"
          description: str   # shown in HelpOverlay

      KEYMAP: tuple[Binding, ...] = (
          Binding("tab",          "global",      "focus_next",       "Cycle focus to next region"),
          Binding("shift+tab",    "global",      "focus_previous",   "Cycle focus to previous region"),
          Binding("enter",        "input",       "submit",           "Submit task"),
          Binding("shift+enter",  "input",       "newline",          "Insert newline"),
          Binding("slash",        "input",       "open_palette",     "Open slash command palette"),
          Binding("escape",       "modal",       "dismiss_modal",    "Close modal / cancel"),
          Binding("question_mark","global",      "open_help",        "Open help overlay"),
          Binding("j",            "main",        "scroll_down",      "Scroll one row down"),
          Binding("k",            "main",        "scroll_up",        "Scroll one row up"),
          Binding("ctrl+d",       "main",        "half_page_down",   "Half-page down"),
          Binding("ctrl+u",       "main",        "half_page_up",     "Half-page up"),
          Binding("g",            "main",        "jump_top",         "Jump to top of history"),
          Binding("G",            "main",        "jump_bottom",      "Jump to bottom of history"),
          Binding("f",            "main",        "fork_turn",        "Fork session from focused turn"),
          Binding("ctrl+f",       "main",        "open_search",      "Open in-pane search"),
          Binding("ctrl+c",       "global",      "interrupt",        "Interrupt turn; press again to exit"),
          Binding("ctrl+l",       "global",      "redraw",           "Redraw screen"),
      )
      ```
      (Diff modal + permission modal keys live in those modals' BINDINGS in M9-05; KEYMAP holds only global + main + input + modal-dismiss baseline.)

    Wire `VossTUIApp.BINDINGS` (Task 2 of this plan; see below) by appending: `from .keymap import KEYMAP; BINDINGS = [(b.key, b.action, b.description) for b in KEYMAP if b.context in ("global", "input")]`. Main-pane bindings are added on the TurnView widget itself. Modal-context bindings live on the modals.

    Create `voss/harness/tui/widgets/help_overlay.py`:
      ```python
      class HelpOverlay(ModalScreen):
          """? overlay — shows keymap + visible slash commands. Dismissed by Esc."""
          BINDINGS = [("escape", "app.pop_screen()", "Close")]
          def __init__(self, keymap, registry, **kw):
              super().__init__(**kw); self.keymap = keymap; self.registry = registry
          def compose(self):
              yield Static("voss tui · keys + commands", classes="modal-title")
              # keymap rows
              for b in self.keymap:
                  yield Static(f"  {b.key:<14} {b.context:<8} {b.description}")
              yield Static("")
              yield Static("commands", classes="modal-subhead")
              for name in self.registry.ids():
                  cmd = self.registry.lookup(name)
                  yield Static(f"  {name:<14} {cmd.help if cmd else ''}")
              yield Static("")
              yield Static("press Esc to close", classes="modal-hint")
      ```
      Re-export HelpOverlay from `voss/harness/tui/widgets/__init__.py`.

    Tests: 4 test files. test_reserved_slash_names.py (2 tests), test_save_rename.py (4 tests — fresh registry build + lookup + deprecation warning capture + handler equality), test_keymap_baseline.py (2 tests), test_help_overlay.py (2 tests). Use `pytest-asyncio` + `app.run_test()` for the help overlay. Build a small fake SlashRegistry instance for the help overlay test to avoid coupling to cli.py's live registry; but use the REAL `_build_slash_registry()` for the rename tests.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/tui/test_reserved_slash_names.py tests/harness/tui/test_keymap_baseline.py tests/harness/tui/test_help_overlay.py tests/harness/tui/test_save_rename.py tests/harness/test_cognition.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from voss.harness.tui.reserved_slash_names import RESERVED_SLASH_NAMES; assert RESERVED_SLASH_NAMES == ('/recall', '/forget', '/memory', '/save')"` exits 0.
    - `python -c "from voss.harness.tui.keymap import KEYMAP; assert len(KEYMAP) >= 14"` exits 0.
    - `grep -c "SlashCommand(\"/snapshot\"" voss/harness/cli.py` returns 1 (canonical rename present).
    - `grep -c "_save_deprecated" voss/harness/cli.py` returns >= 2 (handler def + registration).
    - `grep -c "deprecated; use /snapshot" voss/harness/cli.py` returns >= 1 (locked deprecation copy present).
    - `grep -c "voss tui · keys + commands" voss/harness/tui/widgets/help_overlay.py` returns 1 (UI-SPEC locked heading).
    - `grep -v '^#' voss/harness/tui/reserved_slash_names.py | grep -c "/save"` returns >= 1 (`/save` IS in the reserved tuple per CONTEXT, restored from earlier 3-name interim).
    - `pytest tests/harness/test_cognition.py -x -q` green (no regression on `/save-plan`).
    - All 10 tests in this task pass; prior plans' tests still green.
  </acceptance_criteria>
  <done>Reserved names locked at full 4-name CONTEXT list; live `/save` renamed to `/snapshot` with deprecation alias; keymap is single-source; HelpOverlay reachable via `?`. M8 has a clear 4-name allow-list. Auditor can grep one file each.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: SlashPalette popup + fuzzy ranking + recency + collision check vs reserved names; wire VossTUIApp.BINDINGS and InputBar `/` open-palette action</name>
  <files>voss/harness/tui/widgets/slash_palette.py, voss/harness/tui/widgets/__init__.py, voss/harness/tui/widgets/input_bar.py, voss/harness/tui/app.py, tests/harness/tui/test_slash_palette.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/slash.py (full file — SlashRegistry.ids() returns sorted list of visible names; hidden commands are excluded by default)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cli.py (lines 462-484 _build_slash_registry — actual commands the palette will see in production, NOW including /snapshot and the /save alias from Task 1)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md ("Slash palette popup" row in region table + "Focus highlight" row + "Empty session list" copy + "Type / for commands · ? for help" status hint)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/widgets/input_bar.py (M9-02 — palette anchors above the InputBar; need its DOM id and message types; THIS TASK adds the `/` binding to it)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/app.py (M9-02 — `BINDINGS = []` placeholder; THIS TASK fills it from KEYMAP)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/reserved_slash_names.py (Task 1 — palette filters these out as belt-and-suspenders even though the registry should not contain `/recall`, `/forget`, `/memory` yet; the registry DOES contain `/save` per Task 1 alias, so the palette's reserved filter must NOT hide `/save` since users still need to type it for the one-release deprecation window — see Action below)
  </read_first>
  <behavior>
    - Test: `rank_commands(query="he", names=["/help", "/cost", "/exit", "/agents"])` returns `["/help"]` first (substring match wins).
    - Test: `rank_commands(query="cl", names=["/help", "/clear", "/cost"])` returns `["/clear"]` first.
    - Test: `rank_commands(query="", names=names, recency=["/help", "/cost"])` returns recency order first, then alphabetical (`["/help", "/cost", "/agents", "/clear", "/exit"]` from the fixture).
    - Test (reserved filter, M8-only): `rank_commands(query="recall", names=[...], reserved=RESERVED_SLASH_NAMES)` excludes `/recall` from results. SAME test for `/forget` and `/memory`. `/save` IS included even though it appears in RESERVED_SLASH_NAMES, because Task 1 left it registered as a deprecation alias and users typing `sa` should still find it — implemented by a `keep_alive: tuple[str,...] = ()` kwarg on rank_commands that overrides reserved filtering for an explicit allow-list. Default keep_alive includes `/save` until M8 ships.
    - Test (test_slash_palette mount): mount SlashPalette inside test app with a registry containing `/help`, `/cost`, `/clear`, `/snapshot`. Type `/he` into the input bar (`pilot.press("/", "h", "e")`). Assert palette opens (visible in DOM), shows 1 row (`/help`), and selecting it (`pilot.press("enter")`) emits a `PaletteSubmitted("/help")` message.
    - Test: pressing Esc closes the palette without submitting (`pilot.press("escape")`); no message emitted.
    - Test: typing `/` followed by NO match shows the locked empty-state copy `no matching commands` (sentence case + dim style).
    - Test: palette is anchored ABOVE the input bar — `palette.region.y < input_bar.region.y` after mount.
    - Test: palette height is at most 8 rows even when registry has 50+ commands.
    - Test (InputBar wiring): `InputBar` now has a `("slash", "open_palette", ...)` binding. When the input value is empty, pressing `/` triggers `action_open_palette` which mounts a SlashPalette via `self.app.mount(SlashPalette(self.app.slash_registry), before=self)`. When the input value is non-empty, `/` inserts a literal `/` (no palette).
    - Test (VossTUIApp.BINDINGS): `VossTUIApp.BINDINGS` is non-empty after Task 2; it contains at least the `escape`, `question_mark`, `ctrl+c`, `ctrl+l`, `tab`, `shift+tab` entries from KEYMAP (the global + input context subset).
  </behavior>
  <action>
    Create `voss/harness/tui/widgets/slash_palette.py`:
      ```python
      from textual.widgets import ListView, ListItem, Static
      from textual.message import Message
      from voss.harness.slash import SlashRegistry
      from voss.harness.tui.reserved_slash_names import RESERVED_SLASH_NAMES

      # /save is reserved for M8 long-term but stays in the palette during the
      # one-release deprecation window (Task 1 leaves it registered as an alias
      # to /snapshot). Once M8 ships, M8's planner will remove this entry.
      _PALETTE_KEEP_ALIVE: tuple[str, ...] = ("/save",)

      def rank_commands(
          query: str,
          names: list[str],
          *,
          recency: list[str] | None = None,
          reserved: tuple[str, ...] = RESERVED_SLASH_NAMES,
          keep_alive: tuple[str, ...] = _PALETTE_KEEP_ALIVE,
      ) -> list[str]:
          """Rank: 1) substring match (case-insensitive), 2) recency order, 3) alphabetical.
          Reserved names are filtered out unless they appear in keep_alive.
          """
          blocked = tuple(n for n in reserved if n not in keep_alive)
          filtered = [n for n in names if n not in blocked]
          if not query:
              rest = sorted(n for n in filtered if not recency or n not in recency)
              return ([n for n in (recency or []) if n in filtered] + rest)[:8]
          q = query.lower().lstrip("/")
          scored = []
          for n in filtered:
              idx = n.lower().lstrip("/").find(q)
              if idx >= 0:
                  scored.append((idx, n))
          scored.sort()
          return [n for _, n in scored[:8]]

      class SlashPalette(ListView):
          class PaletteSubmitted(Message):
              def __init__(self, value: str): super().__init__(); self.value = value

          DEFAULT_CSS = """
          SlashPalette {
              dock: bottom;
              offset-y: -1;       /* anchor above input bar */
              height: auto;
              max-height: 8;
              border: round $dim;
          }
          """
          BINDINGS = [
              ("escape", "dismiss", "Close palette"),
              ("enter", "submit", "Select command"),
          ]
          def __init__(self, registry: SlashRegistry, **kw):
              super().__init__(**kw)
              self.registry = registry
              self.query_text = ""
              self.recency: list[str] = []
          def update_query(self, query: str) -> None:
              self.query_text = query
              self.clear()
              ranked = rank_commands(query, self.registry.ids(), recency=self.recency)
              if not ranked:
                  self.append(ListItem(Static("no matching commands", classes="dim")))
                  return
              for name in ranked:
                  cmd = self.registry.lookup(name)
                  label = f"{name:<14} {cmd.help if cmd else ''}"
                  self.append(ListItem(Static(label), id=name))
          def action_submit(self) -> None:
              item = self.highlighted_child
              if item and item.id:
                  self.recency.insert(0, item.id)
                  self.recency = self.recency[:10]
                  self.post_message(self.PaletteSubmitted(item.id))
                  self.action_dismiss()
          def action_dismiss(self) -> None:
              self.remove()
      ```

    Edit `voss/harness/tui/widgets/input_bar.py` (M9-02): add a binding `("slash", "open_palette", "Open palette")` and a `def action_open_palette(self)` that — only if `self.value` is empty — mounts a SlashPalette via `self.app.mount(SlashPalette(self.app.slash_registry), before=self)` and forwards subsequent keystrokes to `palette.update_query(self.value)`. If `self.value` is non-empty, fall through to the default `Input` handling so `/` is inserted as a literal character.

    Edit `voss/harness/tui/app.py` (M9-02) to (1) accept `slash_registry: SlashRegistry | None = None` in `__init__` (default constructs an empty `SlashRegistry()` so tests can mount the app without a real cli registry; live wiring to cli.py's `_build_slash_registry()` lands in M9-07), and (2) populate the class-level BINDINGS from KEYMAP:
      ```python
      from voss.harness.tui.keymap import KEYMAP
      ...
      class VossTUIApp(App):
          CSS_PATH = "styles.tcss"
          BINDINGS = [(b.key, b.action, b.description)
                      for b in KEYMAP
                      if b.context in ("global", "input")]
          def __init__(self, *, slash_registry=None, **kw):
              super().__init__(**kw)
              self.slash_registry = slash_registry or SlashRegistry()
      ```

    Re-export SlashPalette and rank_commands from `voss/harness/tui/widgets/__init__.py`.

    Create `tests/harness/tui/test_slash_palette.py` with the 10 tests above. Use a fake SlashRegistry built from `SlashCommand(name="/help", help="show help", handler=lambda *a: None)` etc., plus one real-registry assertion confirming `/snapshot` and `/save` both appear in `rank_commands("sa", registry.ids())`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/tui/test_slash_palette.py tests/harness/tui/test_reserved_slash_names.py tests/harness/tui/test_keymap_baseline.py tests/harness/tui/test_help_overlay.py tests/harness/tui/test_save_rename.py tests/harness/tui/test_app_shell.py tests/harness/tui/test_plain_parity.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from voss.harness.tui.widgets import SlashPalette, rank_commands; print(rank_commands('he', ['/help', '/cost']))"` prints `['/help']`.
    - `python -c "from voss.harness.tui.widgets import rank_commands; from voss.harness.tui.reserved_slash_names import RESERVED_SLASH_NAMES; r = rank_commands('rec', ['/recall', '/help'], reserved=RESERVED_SLASH_NAMES); assert '/recall' not in r"` exits 0 (reserved filter works for M8 names).
    - `python -c "from voss.harness.tui.widgets import rank_commands; r = rank_commands('sa', ['/save', '/snapshot', '/help']); assert '/save' in r and '/snapshot' in r"` exits 0 (keep-alive lets `/save` deprecation alias remain in palette).
    - `grep -c "open_palette" voss/harness/tui/widgets/input_bar.py` returns >= 1.
    - `grep -c "BINDINGS = \\[" voss/harness/tui/app.py` returns 1 and the line is followed by a list-comprehension over KEYMAP (no longer an empty list).
    - All 10 palette tests pass + 10 prior tests from Task 1.
    - `pytest tests/harness/tui/ -x -q` overall green (all M9-01..03 tests).
  </acceptance_criteria>
  <done>SlashPalette opens above the input bar on `/`, ranks by substring + recency, filters M8-reserved names (except the `/save` deprecation alias), dismisses on Esc, emits PaletteSubmitted on Enter. HelpOverlay reachable via `?` and lists keymap + commands. InputBar + VossTUIApp wired honestly — both files declared in this plan's files_modified.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user → InputBar | typed slash query; bounded to single line, no shell exec. |
| Palette → SlashRegistry | palette only READS registry; never mutates. |
| /save alias → _save handler | alias dispatch goes through the same handler; deprecation warning is a side channel (stderr), not a security boundary. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M9-03-01 | Spoofing | Malicious slash name (e.g. `/exit\x00...`) injected via plugin registry | mitigate | SlashCommand is `frozen=True`; slash.py already controls registration. Palette renders names via Text(name, markup=False) so escape codes can't break the panel. |
| T-M9-03-02 | Reserved-name bypass | M8 ships and accidentally also registers `/recall` outside slash.py | accept | Belt-and-suspenders: palette's `rank_commands` filter excludes reserved names even if registry leaks. M8 planner is responsible for the registry-level fix. |
| T-M9-03-03 | DoS | Registry with 10k commands | mitigate | rank_commands always slices to first 8 results; height capped at 8 in CSS. |
| T-M9-03-04 | Confused-deputy | `/save` alias dispatches to the wrong handler | mitigate | `_save_deprecated` is a thin wrapper that calls `_save` directly. Test asserts the handler reference is the same callable post-dispatch. |
</threat_model>

<verification>
- 16+ tests across 5 files green.
- Reserved-name allow-list is single-source AND matches CONTEXT.md (4 names, locked order).
- Keymap is single-source AND wired into VossTUIApp.BINDINGS.
- `/save` rename: canonical `/snapshot`; deprecation alias `/save` with stderr warning; same underlying handler.
- All wiring files (input_bar.py, app.py, widgets/__init__.py) declared in files_modified — no scope leak (resolves checker B3).
</verification>

<success_criteria>
1. `voss.harness.tui.widgets.SlashPalette` ranks correctly on substring + recency + alphabetical.
2. Reserved names (/recall, /forget, /memory) cannot appear in palette results regardless of registry state; `/save` stays during the deprecation window.
3. HelpOverlay opens on `?`, dismisses on `Esc`, lists every Binding + every visible slash command.
4. KEYMAP is the single source feeding VossTUIApp.BINDINGS.
5. `/save` is now an alias to `/snapshot`; dispatch emits the locked deprecation stderr line; M8 reservation (4 names) is honored.
6. InputBar `/` opens palette only when input is empty; otherwise inserts literal `/`.
</success_criteria>

<output>
After completion, create `.planning/phases/M9-tui-shell-tui-01/M9-03-SUMMARY.md`.
</output>
</content>
</invoke>