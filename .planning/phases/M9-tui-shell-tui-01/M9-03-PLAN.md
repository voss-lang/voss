---
phase: M9
plan: 03
type: execute
wave: 2
depends_on: [M9-01]
files_modified:
  - voss/harness/tui/widgets/slash_palette.py
  - voss/harness/tui/widgets/help_overlay.py
  - voss/harness/tui/keymap.py
  - voss/harness/tui/reserved_slash_names.py
  - tests/harness/tui/test_slash_palette.py
  - tests/harness/tui/test_help_overlay.py
  - tests/harness/tui/test_reserved_slash_names.py
  - tests/harness/tui/test_keymap_baseline.py
autonomous: true
requirements: [TUI-05, TUI-09]
must_haves:
  truths:
    - "Typing `/` in InputBar opens a popup palette ranked by fuzzy match over the slash registry."
    - "Palette never registers /recall, /forget, /memory, or /save — these are reserved for M8."
    - "Pressing `?` from any non-modal state opens the help overlay listing every binding + visible slash command."
    - "Vim navigation keys (j, k, g, G, Ctrl-d, Ctrl-u) scroll the main pane when it has focus."
    - "Esc dismisses the palette and the help overlay without submitting input."
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
      provides: "Frozen tuple of slash names reserved for downstream phases (M8 memory)"
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
---

<objective>
Build the slash command palette + help overlay + the keymap baseline that downstream plans (M9-05 modals, M9-06 fork-from-turn) extend. Lock the reserved slash names for M8 in a frozen module so the palette + auditor in M9-06 can both grep it.

Purpose: TUI-05 and the discovery side of TUI-09. The palette is the user's only way to find non-obvious commands; the help overlay is the only way to discover keys. Both are required for "feels like Claude Code / Aider depth" per CONTEXT.

Output: SlashPalette + HelpOverlay widgets + KEYMAP table + reserved-name allow-list + 4 test files.
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

<!-- Current registered slash names (from voss/harness/cli.py:_build_slash_registry lines 342-460, reachable via grep): -->
/exit, /help, /clear, /cost, /tools, /analyze, /save_plan, /model, /mode, /login, /save, /plugins, /plugin, /skills, /skill, /agents, /agent
<!-- + /sessions registered elsewhere — confirm by grep -->

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
  <name>Task 1: Reserved slash names + KEYMAP table + HelpOverlay widget</name>
  <files>voss/harness/tui/reserved_slash_names.py, voss/harness/tui/keymap.py, voss/harness/tui/widgets/help_overlay.py, tests/harness/tui/test_reserved_slash_names.py, tests/harness/tui/test_keymap_baseline.py, tests/harness/tui/test_help_overlay.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md ("Slash command palette" section + "Specifics" — reserved names `/recall`, `/forget`, `/memory`, `/save`. Note: `/save` is ALSO currently used by current cli.py — see Specifics conflict resolution below.)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cli.py (lines 342-460 _build_slash_registry — list of currently-registered names; check whether `/save` is a current command or a reserved one)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md ("Help overlay header" copy + "Interaction Contract" Keybindings full table + "Empty side panel" copy)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/app.py (M9-02 — KEYMAP feeds into VossTUIApp.BINDINGS)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/widgets/__init__.py (M9-02 — extend exports with HelpOverlay)
  </read_first>
  <behavior>
    - Test (test_reserved_slash_names): `from voss.harness.tui.reserved_slash_names import RESERVED_SLASH_NAMES; assert RESERVED_SLASH_NAMES == ("/recall", "/forget", "/memory")`. NOTE: `/save` is OMITTED from reserved set because it is already a live command (see Action — conflict resolution); M8 will need to use `/memsave` or similar. Document this in the module docstring.
    - Test: `RESERVED_SLASH_NAMES` is a tuple (immutable); attempting `RESERVED_SLASH_NAMES.append(...)` raises AttributeError.
    - Test (test_keymap_baseline): `from voss.harness.tui.keymap import KEYMAP; assert len(KEYMAP) >= 14`; assert every UI-SPEC row from the Keybindings table is present (use a parametrized test over the expected (key, context_substring) tuples).
    - Test: each Binding has a non-empty `description` (used by HelpOverlay) and `action` (Textual action name).
    - Test (test_help_overlay): mount HelpOverlay(keymap=KEYMAP, registry=test_registry) inside a test app; query renders one row per Binding + one row per visible slash command; pressing Esc dismisses it (re-mount and `await pilot.press("escape")`; assert overlay is no longer in the DOM).
    - Test: HelpOverlay heading text is exactly `voss tui · keys + commands` (UI-SPEC locked copy).
  </behavior>
  <action>
    Create `voss/harness/tui/reserved_slash_names.py`:
      ```python
      """Slash names reserved for downstream phases.

      M8 (Project Memory) will register /recall and /forget and /memory. The TUI
      palette must NOT register these and must NOT autocomplete to them, so M8
      can land without UX collision.

      /save is NOT reserved — it is an existing live command (see
      voss/harness/cli.py:_build_slash_registry, the _save handler). If M8
      needs a memory-save verb it will pick a distinct name (e.g. /memsave).
      """
      from __future__ import annotations

      RESERVED_SLASH_NAMES: tuple[str, ...] = ("/recall", "/forget", "/memory")
      ```
      The conflict-resolution decision MUST be documented in this docstring so the auditor in M9-06 (and the M8 planner later) sees it.

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

    Wire `VossTUIApp.BINDINGS` (in M9-02-created app.py) by appending after this plan: `from .keymap import KEYMAP; BINDINGS = [(b.key, b.action, b.description) for b in KEYMAP if b.context in ("global", "input")]`. Main-pane bindings are added on the TurnView widget itself. Modal-context bindings live on the modals.

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

    Tests: 6 tests across 3 files. Use `pytest-asyncio` + `app.run_test()` for the help overlay. Build a small fake SlashRegistry instance for the help overlay test to avoid coupling to cli.py's live registry.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/tui/test_reserved_slash_names.py tests/harness/tui/test_keymap_baseline.py tests/harness/tui/test_help_overlay.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from voss.harness.tui.reserved_slash_names import RESERVED_SLASH_NAMES; assert RESERVED_SLASH_NAMES == ('/recall', '/forget', '/memory')"` exits 0.
    - `python -c "from voss.harness.tui.keymap import KEYMAP; assert len(KEYMAP) >= 14"` exits 0.
    - `grep -c "voss tui · keys + commands" voss/harness/tui/widgets/help_overlay.py` returns 1 (UI-SPEC locked heading).
    - `grep -c "/save" voss/harness/tui/reserved_slash_names.py` returns 0 (NOT reserved — conflict-resolved); `grep -c "/memsave" voss/harness/tui/reserved_slash_names.py` returns >= 1 in docstring (recommendation documented).
    - All 6 tests pass; prior plans' tests still green.
  </acceptance_criteria>
  <done>Reserved names locked; keymap is single-source; HelpOverlay reachable via `?`. M8 has a clear name allow-list. Auditor can grep one file each.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: SlashPalette popup + fuzzy ranking + recency + collision check vs reserved names</name>
  <files>voss/harness/tui/widgets/slash_palette.py, voss/harness/tui/widgets/__init__.py, tests/harness/tui/test_slash_palette.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/slash.py (full file — SlashRegistry.ids() returns sorted list of visible names; hidden commands are excluded by default)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cli.py (lines 342-460 _build_slash_registry — actual commands the palette will see in production)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md ("Slash palette popup" row in region table + "Focus highlight" row + "Empty session list" copy + "Type / for commands · ? for help" status hint)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/widgets/input_bar.py (M9-02 — palette anchors above the InputBar; need its DOM id and message types)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/reserved_slash_names.py (Task 1 — palette filters these out as belt-and-suspenders even though the registry should not contain them yet)
  </read_first>
  <behavior>
    - Test: `rank_commands(query="he", names=["/help", "/cost", "/exit", "/agents"])` returns `["/help"]` first (substring match wins).
    - Test: `rank_commands(query="cl", names=["/help", "/clear", "/cost"])` returns `["/clear"]` first.
    - Test: `rank_commands(query="", names=names, recency=["/help", "/cost"])` returns recency order first, then alphabetical (`["/help", "/cost", "/agents", "/clear", "/exit"]` from the fixture).
    - Test: `rank_commands(query="recall", names=[...], reserved=RESERVED_SLASH_NAMES)` excludes `/recall` from results even if a malformed registry contained it.
    - Test (test_slash_palette mount): mount SlashPalette inside test app with a registry containing `/help`, `/cost`, `/clear`. Type `/he` into the input bar (`pilot.press("/", "h", "e")`). Assert palette opens (visible in DOM), shows 1 row (`/help`), and selecting it (`pilot.press("enter")`) emits a `PaletteSubmitted("/help")` message.
    - Test: pressing Esc closes the palette without submitting (`pilot.press("escape")`); no message emitted.
    - Test: typing `/` followed by NO match shows the locked empty-state copy `no matching commands` (sentence case per UI-SPEC tone rules — confirm in UI-SPEC Copywriting Contract; this is NOT explicitly locked, so use sentence case + dim style).
    - Test: palette is anchored ABOVE the input bar — `palette.region.y < input_bar.region.y` after mount.
    - Test: palette height is at most 8 rows even when registry has 50+ commands (UI-SPEC region table row: "up to 8 rows").
  </behavior>
  <action>
    Create `voss/harness/tui/widgets/slash_palette.py`:
      ```python
      from textual.widgets import ListView, ListItem, Static
      from textual.message import Message
      from voss.harness.slash import SlashRegistry
      from voss.harness.tui.reserved_slash_names import RESERVED_SLASH_NAMES

      def rank_commands(
          query: str,
          names: list[str],
          *,
          recency: list[str] | None = None,
          reserved: tuple[str, ...] = RESERVED_SLASH_NAMES,
      ) -> list[str]:
          """Rank: 1) substring match (case-insensitive), 2) recency order, 3) alphabetical.
          Reserved names are filtered out unconditionally.
          """
          filtered = [n for n in names if n not in reserved]
          if not query:
              # No query: show recency-first, then alphabetical for the rest.
              rest = sorted(n for n in filtered if not recency or n not in recency)
              return ([n for n in (recency or []) if n in filtered] + rest)[:8]
          q = query.lower().lstrip("/")
          # Substring match first; rank by index of match (lower = better), then alpha
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
              self.recency: list[str] = []   # populated on submit
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

    Hook InputBar to open SlashPalette: in `voss/harness/tui/widgets/input_bar.py` (M9-02), add a binding `("slash", "open_palette", "Open palette")` and a `def action_open_palette(self)` that — only if the input is currently empty — mounts a SlashPalette via `self.app.mount(SlashPalette(self.app.slash_registry), before=self)` and forwards subsequent keystrokes to `palette.update_query(self.value)`. Wire `VossTUIApp.slash_registry: SlashRegistry` as an `__init__` arg with a default of an empty registry; the live wiring to cli.py's `_build_slash_registry()` happens in M9-06.

    Re-export SlashPalette and rank_commands from `voss/harness/tui/widgets/__init__.py`.

    Create `tests/harness/tui/test_slash_palette.py` with the 8 tests above. Use a fake SlashRegistry built from `SlashCommand(name="/help", help="show help", handler=lambda *a: None)` etc.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/tui/test_slash_palette.py tests/harness/tui/test_reserved_slash_names.py tests/harness/tui/test_keymap_baseline.py tests/harness/tui/test_help_overlay.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from voss.harness.tui.widgets import SlashPalette, rank_commands; print(rank_commands('he', ['/help', '/cost']))"` prints `['/help']`.
    - `python -c "from voss.harness.tui.widgets import rank_commands; from voss.harness.tui.reserved_slash_names import RESERVED_SLASH_NAMES; assert '/recall' not in rank_commands('rec', ['/recall', '/help'])"` exits 0 (reserved filter works even if registry leaks).
    - All 8 palette tests pass + 6 prior tests from Task 1.
    - `pytest tests/harness/tui/ -x -q` overall green (all M9-01..03 tests).
  </acceptance_criteria>
  <done>SlashPalette opens above the input bar on `/`, ranks by substring + recency, filters reserved names, dismisses on Esc, emits PaletteSubmitted on Enter. HelpOverlay reachable via `?` and lists keymap + commands.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user → InputBar | typed slash query; bounded to single line, no shell exec. |
| Palette → SlashRegistry | palette only READS registry; never mutates. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M9-03-01 | Spoofing | Malicious slash name (e.g. `/exit\x00...`) injected via plugin registry | mitigate | SlashCommand is `frozen=True`; slash.py already controls registration. Palette renders names via Text(name, markup=False) so escape codes can't break the panel. |
| T-M9-03-02 | Reserved-name bypass | M8 ships and accidentally also registers `/recall` outside slash.py | accept | Belt-and-suspenders: palette's `rank_commands` filter excludes reserved names even if registry leaks. M8 planner is responsible for the registry-level fix. |
| T-M9-03-03 | DoS | Registry with 10k commands | mitigate | rank_commands always slices to first 8 results; height capped at 8 in CSS. |
</threat_model>

<verification>
- 14 tests across 4 files green.
- Reserved-name allow-list is single-source.
- Keymap is single-source.
</verification>

<success_criteria>
1. `voss.harness.tui.widgets.SlashPalette` ranks correctly on substring + recency + alphabetical.
2. Reserved names (/recall, /forget, /memory) cannot appear in palette results regardless of registry state.
3. HelpOverlay opens on `?`, dismisses on `Esc`, lists every Binding + every visible slash command.
4. KEYMAP is the single source feeding VossTUIApp.BINDINGS.
5. `/save` conflict with existing live command is resolved in the reserved-names module docstring.
</success_criteria>

<output>
After completion, create `.planning/phases/M9-tui-shell-tui-01/M9-03-SUMMARY.md`.
</output>
