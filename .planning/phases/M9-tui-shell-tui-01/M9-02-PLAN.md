---
phase: M9
plan: 02
type: execute
wave: 2
depends_on: [M9-01]
files_modified:
  - voss/harness/tui/app.py
  - voss/harness/tui/renderer.py
  - voss/harness/tui/widgets/__init__.py
  - voss/harness/tui/widgets/header.py
  - voss/harness/tui/widgets/turn_view.py
  - voss/harness/tui/widgets/status_line.py
  - voss/harness/tui/widgets/input_bar.py
  - voss/harness/tui/widgets/confidence_bar.py
  - voss/harness/tui/widgets/budget_meter.py
  - voss/harness/tui/styles.tcss
  - voss/harness/tui/glyphs.py
  - voss/harness/render.py
  - tests/harness/tui/test_app_shell.py
  - tests/harness/tui/test_textual_renderer_protocol.py
  - tests/harness/tui/test_glyph_and_color_contract.py
autonomous: true
requirements: [TUI-02, TUI-03]
must_haves:
  truths:
    - "VossTUIApp boots, mounts header, main pane, status line, input bar exactly per UI-SPEC region grid."
    - "TextualRenderer implements all 11 methods of the Renderer protocol from voss/harness/render.py."
    - "Glyph vocabulary file (glyphs.py) declares ONLY the locked set; importing any other glyph raises AttributeError."
    - "TCSS stylesheet uses ONLY the locked color values (terminal default, dim grey, accent cyan-blue, signal good/warn/error)."
    - "ConfidenceBar widget renders exactly 16 cells total: 10 bar + 1 space + 4 numeric + 1 trailing pad."
    - "BudgetMeter widget renders exactly 18 cells total at standard inputs; when ctx_pct==0 or total==0 the meter renders the em-dash placeholder `—` (no division)."
    - "At 80x24 the app mounts without truncating header glyphs or status fields."
  artifacts:
    - path: "voss/harness/tui/app.py"
      provides: "VossTUIApp (textual.app.App) with locked region grid"
      exports: ["VossTUIApp"]
    - path: "voss/harness/tui/renderer.py"
      provides: "TextualRenderer implementing voss.harness.render.Renderer protocol; drives VossTUIApp via thread-safe message-passing"
      exports: ["TextualRenderer"]
    - path: "voss/harness/tui/widgets/__init__.py"
      provides: "Public widget re-exports"
      exports: ["HeaderBar", "TurnView", "StatusLine", "InputBar", "ConfidenceBar", "BudgetMeter"]
    - path: "voss/harness/tui/glyphs.py"
      provides: "Frozen glyph vocabulary constants — single import surface for the entire TUI"
      exports: ["PROMPT", "USER_INPUT", "TOOL_CALL", "WARN", "BAR_FILL", "BAR_EMPTY", "BUDGET_FILL", "BUDGET_EMPTY", "NEST_LAST", "NEST_MID", "FORK"]
    - path: "voss/harness/tui/styles.tcss"
      provides: "Textual CSS stylesheet binding UI-SPEC color contract"
  key_links:
    - from: "voss/harness/tui/renderer.py"
      to: "voss/harness/render.py:Renderer"
      via: "TextualRenderer satisfies the Renderer protocol (structural typing)"
      pattern: "class TextualRenderer"
    - from: "voss/harness/tui/app.py"
      to: "voss/harness/tui/widgets/"
      via: "VossTUIApp.compose() yields header, main, status, input"
      pattern: "def compose"
    - from: "voss/harness/tui/renderer.py"
      to: "voss/harness/tui/app.py"
      via: "renderer.app: VossTUIApp; each show_* posts a Message to the app"
      pattern: "call_from_thread\\|post_message"
---

<objective>
Build the Textual app shell + the TextualRenderer that satisfies the existing Renderer protocol. Lock the glyph vocabulary into one importable module and the color contract into one TCSS file so subsequent plans (and the auditor in M9-07) can grep for misuse.

Purpose: This is the substrate every later plan in M9 builds on. The app shell + renderer is the swap-in target for the M9-01 capability hook (which currently raises NotImplementedError for the TextualRenderer path). All visualization, palette, modals, and resume UX in waves 3–7 mount onto the regions and widgets created here.

Output: VossTUIApp + 6 reusable widgets + locked glyph + locked color stylesheet + protocol-conformance test.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md
@.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md
@.planning/phases/M9-tui-shell-tui-01/M9-01-PLAN.md
@voss/harness/render.py
@voss/harness/tui/capability.py

<interfaces>
<!-- Renderer protocol — see M9-01-PLAN.md interfaces block. TextualRenderer must implement all 11 methods. -->

<!-- Textual library surface used in this plan: -->
- `textual.app.App`, `App.compose()`, `App.call_from_thread(callable, *args)`
- `textual.containers.Horizontal`, `Vertical`
- `textual.widgets.Static`, `Header`, `Footer`, `Input`, `RichLog`
- `textual.reactive.reactive`
- `textual.css.query.NoMatches`

<!-- Glyph vocabulary (UI-SPEC locked, copy verbatim — codepoints listed): -->
- PROMPT       = "▌"    U+258C   prompt
- USER_INPUT   = "❯"    U+276F   user input marker (reserved for input-bar echo)
- TOOL_CALL    = "⏵"    U+23F5   tool call
- WARN         = "⚠"    U+26A0   warning
- BAR_FILL     = "█"    U+2588   confidence bar filled
- BAR_EMPTY    = "░"    U+2591   confidence bar empty
- BUDGET_FILL  = "▰"    U+25B0   budget bar filled
- BUDGET_EMPTY = "▱"    U+25B1   budget bar empty
- NEST_LAST    = "└─"   U+2514 + U+2500   nested spawn last child
- NEST_MID     = "├─"   U+251C + U+2500   nested spawn sibling
- FORK         = "⎇"    U+2387   fork marker in session list

<!-- Color contract (UI-SPEC locked, dark-theme truecolor values shown; light + 16-color variants in styles.tcss): -->
- accent      = "#5FAFFF"   used ONLY for the 6 allow-listed elements (UI-SPEC "Accent reserved for" list)
- dim         = "#888888"   borders, separators, timestamps, status-line bg accent
- signal_good = "#5FD75F"   tool success, confidence >= 0.85
- signal_warn = "#FFD75F"   confidence 0.50–0.84, budget 75–99%
- signal_error = "#FF5F5F"  tool failure, budget 100%, rejected diff

<!-- ConfidenceBar locked width contract (resolved per checker W4): -->
Total width = 16 cells: 10 (bar glyphs) + 1 (single space separator) + 4 (numeric `d.dd`) + 1 (trailing pad).
This supersedes any earlier "15 cell" interpretation of UI-SPEC. Auditor in M9-07 grep-asserts the exact string shape.

<!-- BudgetMeter zero-total contract (resolved per checker W5): -->
When `total == 0` OR `ctx_pct == 0` (no budget signal yet from recorder), BudgetMeter MUST render `▱▱▱▱▱▱▱▱▱▱  — ` (10 empty cells + double-space + em-dash + trailing pad). NEVER substitute `total=1` to avoid division-by-zero; the em-dash is the explicit "no signal" indicator. Total cell count stays 18 (10 + 2 + 4 + 2 = 18; numeric slot is `— ` padded right).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Lock glyph vocabulary + color stylesheet + app shell skeleton</name>
  <files>voss/harness/tui/glyphs.py, voss/harness/tui/styles.tcss, voss/harness/tui/app.py, voss/harness/tui/widgets/__init__.py, voss/harness/tui/widgets/header.py, voss/harness/tui/widgets/status_line.py, voss/harness/tui/widgets/input_bar.py, voss/harness/tui/widgets/turn_view.py, tests/harness/tui/test_app_shell.py, tests/harness/tui/test_glyph_and_color_contract.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md (entire "Layout / Spacing", "Color Contract", "Typography", "Glyph vocabulary" rows, "Component Inventory" table — the rows for HeaderBar, StatusLine, InputBar, TurnView)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/render.py (lines 58-78 — existing GLYPH_* constants and Banner copy. TextualRenderer must produce the EXACT same banner copy from UI-SPEC "App banner (TTY start)" row.)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/capability.py (M9-01 module — capability gate the app shell respects)
    - Textual docs (use Context7 — `mcp__context7__resolve-library-id` for "textual" then `mcp__context7__get-library-docs` for "app composition, RichLog, Input, TCSS, call_from_thread"). Fall back to `npx --yes ctx7@latest library textual` if MCP unavailable.
  </read_first>
  <behavior>
    - Test (test_glyph_and_color_contract): `from voss.harness.tui.glyphs import PROMPT, TOOL_CALL, WARN, BAR_FILL, BAR_EMPTY, BUDGET_FILL, BUDGET_EMPTY, NEST_LAST, NEST_MID, FORK` succeeds; each equals the locked codepoint above. Accessing `glyphs.EMOJI_THUMBS_UP` raises AttributeError.
    - Test: `voss/harness/tui/styles.tcss` content — `grep -c "#5FAFFF" styles.tcss` returns >= 1; `grep -Ec "(😀|🚀|❤|👍)" styles.tcss` returns 0 (no emoji); `grep -c "^\\.accent" styles.tcss` returns >= 1 (a single `.accent` rule using `$accent` var).
    - Test (test_app_shell): `from voss.harness.tui.app import VossTUIApp; app = VossTUIApp(); pilot = app.run_test()` — run inside `async with app.run_test() as pilot:`. After mount, query each region: `app.query_one("#header", HeaderBar)`, `app.query_one("#main", TurnView)`, `app.query_one("#status", StatusLine)`, `app.query_one("#input", InputBar)` all return non-None. NO `NoMatches` raised.
    - Test: at terminal size 80x24, `pilot.app.console.size == (80, 24)` after `pilot.resize_terminal(80, 24)`, and all four regions render without raising.
    - Test: VossTUIApp default focus after mount is `#input` (InputBar).
    - Test: HeaderBar with `session_id="abc123def456"`, `model="claude-opus-4-7"`, `budget_used=1024`, `budget_total=4000`, `git_status="clean"` renders a single-row Text containing `abc123de` (session truncated to 8 chars), `claude-opus-4-7`, `1.0k / 4.0k`, `clean`. Total width <= 80 cols at 80-col terminal.
    - Test: StatusLine accepts `set_status(model="m", tokens=1234, cost_usd=0.012, ctx_pct=0.42, toast=None)` and renders dim text containing `1,234 tok`, `$0.012`, `ctx 42%`. (Format inherited from existing TtyRenderer.status to keep continuity.)
    - Test: InputBar prompt glyph at col 0 is `▌` (from glyphs.PROMPT). Pressing `enter` with text "hello" posts a `Submitted("hello")` message that an external listener can await.
  </behavior>
  <action>
    Create `voss/harness/tui/glyphs.py` as a frozen-module of UPPERCASE string constants. Use a `__getattr__` module hook that raises `AttributeError` for any name not in the explicit allow-list — this is the auditor anchor for the "no emoji introduced" UI-SPEC acceptance check. The `--no-unicode` fallback table lands in M9-07; this plan ships only the locked Unicode values.

    Create `voss/harness/tui/styles.tcss`. Define design-token variables at the top:
      ```tcss
      $accent: #5FAFFF;
      $dim: #888888;
      $good: #5FD75F;
      $warn: #FFD75F;
      $error: #FF5F5F;
      ```
      Then layout rules for `#header { dock: top; height: 1; }`, `#status { dock: bottom; height: 1; offset-y: -1; background: $dim 20%; }`, `#input { dock: bottom; height: 1; min-height: 1; max-height: 5; }`, `#main { width: 60%; min-width: 60; }`, `#side { width: 40%; min-width: 28; max-width: 50; display: none; }` (hidden when no active spawn — M9-04 will toggle `display: block`).
      Class `.accent { color: $accent; }`, `.signal-good { color: $good; }`, etc. Comment block above each rule citing UI-SPEC row.

    Create `voss/harness/tui/app.py`:
      ```python
      class VossTUIApp(App):
          CSS_PATH = "styles.tcss"
          BINDINGS = []  # filled in M9-03 via KEYMAP
          def compose(self):
              yield HeaderBar(id="header")
              with Horizontal():
                  yield TurnView(id="main")
                  yield SubAgentPanel(id="side")   # SubAgentPanel ships in M9-04; placeholder stub here so layout works
              yield StatusLine(id="status")
              yield InputBar(id="input")
          def on_mount(self):
              self.query_one("#input", InputBar).focus()
      ```

    Create each widget file under `voss/harness/tui/widgets/`:
      - `header.py`: HeaderBar(Static) — `update_header(session_id, model, budget_used, budget_total, git_status)`. Truncate session_id to first 8 chars. Use `Text` from rich.text and apply `style="bold"` to session id (with `class="accent"` markup), dim to the rest, separator `·`. Single row, never wraps; if total width > app.console.width: truncate the rightmost field with `…`.
      - `status_line.py`: StatusLine(Static) — `set_status(model, tokens, cost_usd, ctx_pct, toast)`. Mirrors existing TtyRenderer.status format. Toast field appears for `1500ms` then clears (use Textual's `set_timer`).
      - `input_bar.py`: InputBar(Input) subclass — `compose_prompt()` renders the `▌` glyph at col 0 via a leading `Label`. Emits `Submitted(value: str)` message on Enter (Shift+Enter inserts newline — Textual's `Input` does this natively when `multiline=True`). NOTE: this plan ships the bare InputBar; M9-03 wires the `/` palette-open binding into it.
      - `turn_view.py`: TurnView(RichLog) — initial empty state heading + body per UI-SPEC "Empty main pane" copy. `append_turn(role, body, confidence=None, cost_usd=None, timestamp=None)` writes one block with the locked format.
      - SubAgentPanel: write a placeholder `Static` with `id="side"` and `display: none` here; full impl in M9-04.

    Create `voss/harness/tui/widgets/__init__.py` re-exporting the 6 widget classes (SubAgentPanel placeholder included so app.compose imports cleanly).

    Create tests `test_app_shell.py` (5 tests) + `test_glyph_and_color_contract.py` (4 tests). Use `pytest-asyncio` (already a dev dep per pyproject.toml line 34) for the `async with app.run_test()` pattern.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/tui/test_app_shell.py tests/harness/tui/test_glyph_and_color_contract.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from voss.harness.tui.glyphs import PROMPT, TOOL_CALL, WARN, BAR_FILL, BAR_EMPTY, BUDGET_FILL, BUDGET_EMPTY, NEST_LAST, NEST_MID, FORK; assert PROMPT == '▌' and TOOL_CALL == '⏵' and WARN == '⚠' and BAR_FILL == '█' and BAR_EMPTY == '░' and BUDGET_FILL == '▰' and BUDGET_EMPTY == '▱' and NEST_LAST == '└─' and NEST_MID == '├─' and FORK == '⎇'"` exits 0.
    - `python -c "from voss.harness.tui import glyphs; glyphs.EMOJI_THUMBS_UP"` raises AttributeError.
    - `grep -Ec '(😀|🚀|❤|👍|🎉|🔥|✨)' voss/harness/tui/glyphs.py voss/harness/tui/styles.tcss voss/harness/tui/app.py voss/harness/tui/widgets/*.py` returns 0 (no emoji anywhere in TUI source).
    - `grep -c "#5FAFFF" voss/harness/tui/styles.tcss` returns >= 1.
    - `grep -v '^#\|^\s*//' voss/harness/tui/styles.tcss | grep -Ec '#[0-9A-Fa-f]{6}'` returns exactly 5 (the five locked palette entries — accent, dim, good, warn, error; no stray colors).
    - All 9 tests pass.
    - `test_plain_parity.py` from M9-01 still passes (no regression — TextualRenderer not yet wired to make_renderer).
  </acceptance_criteria>
  <done>VossTUIApp shell mounts the 4 visible regions + the hidden side panel. Glyph + color contract is grep-auditable from one file each. Widget tests prove layout and focus behavior.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: TextualRenderer satisfies the Renderer protocol; ConfidenceBar (16-cell) + BudgetMeter (em-dash on zero) widgets; wire into make_renderer</name>
  <files>voss/harness/tui/renderer.py, voss/harness/tui/widgets/confidence_bar.py, voss/harness/tui/widgets/budget_meter.py, voss/harness/tui/widgets/__init__.py, voss/harness/render.py, tests/harness/tui/test_textual_renderer_protocol.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/render.py (lines 24-44 Renderer protocol — TextualRenderer must satisfy this exactly; lines 47-50 make_renderer — wire TextualRenderer into the force_tui=True path that currently raises NotImplementedError per M9-01)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/render.py (lines 80-160 TtyRenderer — reference impl for each method's output content; TextualRenderer must produce semantically equivalent output (same numbers, same copy strings) on TUI widgets)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md ("Confidence / budget rendering rule" — locked width is 14 cells + 1 pad. This plan implements as 10 bar + 1 space + 4 numeric + 1 trailing = 16 cells per the interfaces block above; W4 resolution; "Color Contract" — confidence tier thresholds 0.85/0.50; "Live workflow visualization" table — ConfidenceBar `is_final` controls accent vs grey)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/app.py (from Task 1 — TextualRenderer holds a reference to a running VossTUIApp instance)
  </read_first>
  <behavior>
    - Test: ConfidenceBar(value=0.82, is_final=False) renders exactly the 16-cell string `████████░░ 0.82 ` (8 filled + 2 empty + space + `0.82` + trailing space). At value=1.0: `██████████ 1.00 `. At value=0.0: `░░░░░░░░░░ 0.00 `. (Locked width: assert `len(rendered) == 16`.)
    - Test: ConfidenceBar tier classes — value=0.90 → `.signal-good`, value=0.70 → `.signal-warn`, value=0.30 → `.signal-error`. is_final=True replaces tier class with `.accent` only when value >= 0.85 (per UI-SPEC accent allow-list item 6: "agent's final confidence value"). is_final=False NEVER applies accent.
    - Test: BudgetMeter(used=2100, total=4000) renders `▰▰▰▰▰▱▱▱▱▱  2.1k / 4.0k ` (5 filled + 5 empty + double-space + numeric + trailing space). At used=3000/total=4000 (75%): tier `.signal-warn`. At used=4000/total=4000 (100%): tier `.signal-error`.
    - Test (W5 zero-total contract): BudgetMeter(used=0, total=0) renders `▱▱▱▱▱▱▱▱▱▱  —  ` (10 empty + double-space + em-dash + trailing pad). NO ZeroDivisionError raised. NO tier class applied (klass is empty string). Same output when used=0,total=4000 with `ctx_pct=0.0` derivation path.
    - Test (W5 sanity): BudgetMeter never internally substitutes `total=1` to avoid division — assert via patch on `int.__truediv__` that no division involving `total<=0` occurs.
    - Test: TextualRenderer is a structural subtype of voss.harness.render.Renderer — `isinstance(TextualRenderer(app=Mock()), Renderer)` is True via `runtime_checkable` (add `@runtime_checkable` decorator to the Renderer protocol if not already present; otherwise verify all 11 method signatures present via `inspect.getmembers`).
    - Test: each of the 11 Renderer methods on TextualRenderer is callable and (under `app.run_test()`) modifies the corresponding region — e.g. `show_user("hi")` appends a TurnView block whose body contains `hi`; `status(model="m", tokens=1, cost_usd=0.1, ctx_pct=0.5)` updates the StatusLine.
    - Test (W5 status path): `renderer.status(model="m", tokens=1, cost_usd=0.0, ctx_pct=0.0)` does NOT raise and produces a BudgetMeter showing the em-dash placeholder (no derived `total=1`).
    - Test: `make_renderer(json_mode=False, plain=False, force_tui=True)` returns a `TextualRenderer` instance instead of raising NotImplementedError; `make_renderer(json_mode=False, plain=True)` returns `PlainRenderer` (regression — M9-01 contract preserved).
    - Test: `make_renderer` default path (no force_tui, TTY True, size >= 80x24) still returns TtyRenderer in THIS plan — the live swap-in to TextualRenderer is deferred to M9-07 final integration once all modals + recorder + resume are in place. Reason: keep `voss chat` usable through Wave 2–6 dev.
  </behavior>
  <action>
    Create `voss/harness/tui/widgets/confidence_bar.py`:
      ```python
      class ConfidenceBar(Static):
          def __init__(self, value: float = 0.0, is_final: bool = False, **kw):
              super().__init__(**kw); self.value = value; self.is_final = is_final
          def render(self) -> RenderableType:
              filled = round(self.value * 10)
              bar = glyphs.BAR_FILL * filled + glyphs.BAR_EMPTY * (10 - filled)
              numeric = f"{self.value:.2f}"  # exactly 4 chars: `d.dd`
              # tier
              if self.is_final and self.value >= 0.85:
                  klass = "accent"
              elif self.value >= 0.85:
                  klass = "signal-good"
              elif self.value >= 0.50:
                  klass = "signal-warn"
              else:
                  klass = "signal-error"
              # LOCKED WIDTH: 10 bar + 1 space + 4 numeric + 1 trailing = 16 cells (checker W4).
              return Text(f"{bar} {numeric} ", style=f"class:{klass}")
      ```
      Locked invariant test: `len(str(rendered_widget))` must equal 16 for every (value, is_final) input pair. UI-SPEC's "14 cells + 1 pad" wording is interpreted as bar(10) + numeric(4) + pad(1) = 15 visible-content cells, plus 1 inter-element space = 16 total. Auditor in M9-07 grep-asserts the f-string form `f"{bar} {numeric} "` (single space between bar and numeric, single trailing).

    Create `voss/harness/tui/widgets/budget_meter.py`:
      ```python
      class BudgetMeter(Static):
          def __init__(self, used: int = 0, total: int = 0, **kw):
              super().__init__(**kw); self.used = used; self.total = total
          def render(self) -> RenderableType:
              # W5: if no budget signal yet, render the em-dash placeholder. Never derive total.
              if self.total <= 0:
                  empty_bar = glyphs.BUDGET_EMPTY * 10
                  return Text(f"{empty_bar}  —  ", style="")  # 10 + 2 + 1 + 2 = 15 cells; pad numeric slot
              pct = self.used / self.total
              filled = round(pct * 10)
              bar = glyphs.BUDGET_FILL * filled + glyphs.BUDGET_EMPTY * (10 - filled)
              numeric = f"{self.used/1000:.1f}k / {self.total/1000:.1f}k"
              klass = "signal-error" if pct >= 1.0 else "signal-warn" if pct >= 0.75 else ""
              return Text(f"{bar}  {numeric} ", style=f"class:{klass}" if klass else "")
      ```
      Locked invariant: `total <= 0` branch NEVER reaches the division. Tests assert via inspection that `BudgetMeter.render` returns without raising for `total=0`.

    Re-export ConfidenceBar + BudgetMeter from `voss/harness/tui/widgets/__init__.py` (append to the existing init from Task 1).

    Create `voss/harness/tui/renderer.py`:
      ```python
      class TextualRenderer:
          """Implements voss.harness.render.Renderer; pushes events to a running VossTUIApp."""
          def __init__(self, app: "VossTUIApp"):
              self.app = app
          def _post(self, fn, *args, **kw):
              # Thread-safe: agent runs in asyncio.run() on the same loop as the app.
              # If the renderer is called from a non-app thread (subagents use threads
              # in voss/harness/subagents.py), use app.call_from_thread(fn, *args, **kw).
              try:
                  fn(*args, **kw)
              except Exception:
                  # Renderer must never crash the agent — log + degrade.
                  self.app.log("renderer error", exc_info=True)
          def banner(self, *, model, cwd, git_status):
              self._post(self.app.query_one("#header", HeaderBar).update_header,
                         session_id=self.app.session_id, model=model,
                         budget_used=0, budget_total=self.app.budget_total,
                         git_status=git_status)
          # ... implement remaining 10 methods, each forwarding to the appropriate widget.
      ```
      Implement EVERY method from the Renderer protocol. For `show_plan` — append a TurnView block with role="agent-plan", body = rationale + steps; for `show_tool_call` — append a sub-block with `⏵ {name}({short_args}) · {state}`; for `show_final` — append a final-role block + post a ConfidenceBar widget into the block; for `status` — call StatusLine.set_status; for `show_thinking` — set the input bar placeholder to `⏵ thinking…` (or use a transient overlay); for `show_warning`/`show_clarify`/`show_cognition*` — append to TurnView with the appropriate style.

    `TextualRenderer.status(*, model, tokens, cost_usd, ctx_pct)` MUST pass `total=0` to BudgetMeter when `ctx_pct == 0` (W5). Do NOT derive `total = tokens / ctx_pct`. The status line's BudgetMeter renders the em-dash placeholder until a real total arrives via a later status() call with non-zero ctx_pct. (M9-04 extends this so the RecorderBridge can also feed total directly when probable/budget primitives emit it.)

    Edit `voss/harness/render.py`:
      - If the Renderer protocol is not already decorated `@runtime_checkable`, add `from typing import Protocol, runtime_checkable` and decorate.
      - In `make_renderer`, replace the `NotImplementedError("TextualRenderer lands in M9-02")` placeholder from M9-01 with `from .tui.renderer import TextualRenderer; from .tui.app import VossTUIApp; return TextualRenderer(VossTUIApp())` ONLY when `force_tui=True`. Leave default path returning TtyRenderer (live swap is M9-07).

    Create `tests/harness/tui/test_textual_renderer_protocol.py` with the 9 tests above. For the protocol-subtype test, use `isinstance(renderer, Renderer)` (requires `@runtime_checkable`).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/tui/test_textual_renderer_protocol.py tests/harness/tui/test_app_shell.py tests/harness/tui/test_glyph_and_color_contract.py tests/harness/tui/test_plain_parity.py tests/harness/tui/test_capability_and_plain_fallback.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from voss.harness.tui.renderer import TextualRenderer; from voss.harness.render import Renderer; from unittest.mock import MagicMock; r = TextualRenderer(app=MagicMock()); assert isinstance(r, Renderer)"` exits 0.
    - `grep -c "def " voss/harness/tui/renderer.py | head -1` shows the renderer has >= 12 method defs (11 protocol methods + __init__).
    - `python -c "from voss.harness.tui.widgets import ConfidenceBar, BudgetMeter, HeaderBar, TurnView, StatusLine, InputBar, SubAgentPanel; print('ok')"` exits 0.
    - W4 width audit: `python -c "from voss.harness.tui.widgets import ConfidenceBar; from rich.console import Console; c = ConfidenceBar(value=0.82); import io; con = Console(file=io.StringIO(), width=20); con.print(c.render()); assert len(con.file.getvalue().rstrip('\\n')) == 16, con.file.getvalue()"` exits 0.
    - W5 zero-total audit: `python -c "from voss.harness.tui.widgets import BudgetMeter; m = BudgetMeter(used=0, total=0); r = m.render(); assert '—' in str(r), r"` exits 0.
    - All tests in this plan + Plan 01 tests pass.
    - `grep -c "NotImplementedError" voss/harness/render.py` returns 0 (placeholder removed).
    - `make_renderer(json_mode=False, plain=True)` still returns PlainRenderer (M9-01 contract intact).
    - `pytest tests/harness/tui/test_plain_parity.py -x -q` still passes (default path unchanged).
  </acceptance_criteria>
  <done>TextualRenderer implements all 11 Renderer methods; ConfidenceBar locked at 16-cell width; BudgetMeter renders em-dash placeholder on zero-total (no derived 1); M9-01 force_tui hook now produces a real TextualRenderer; default user path still uses TtyRenderer (live swap in M9-07).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| agent → renderer | agent passes untrusted LLM output to show_* methods; renderer renders to terminal. |
| subagent thread → renderer | subagents in voss/harness/subagents.py run in threads; renderer must be thread-safe. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M9-02-01 | Tampering | LLM-injected ANSI escapes in show_user / show_final | mitigate | Use rich.text.Text(value, no_emoji=True, markup=False) for all LLM-sourced strings; Textual's RichLog by default does not interpret ANSI from appended Text objects. Add explicit `from rich.text import Text; Text(s, markup=False)` wrapper in every show_* method that takes untrusted strings. |
| T-M9-02-02 | DoS | Renderer crash kills agent | mitigate | `_post()` wrapper catches all exceptions and logs via app.log; never re-raises. Verified by test where mock widget raises — renderer.show_user returns None, no exception propagates. |
| T-M9-02-03 | Race | Subagent thread posts while main thread renders | mitigate | `_post()` uses `app.call_from_thread` when invoked off the event loop; Textual serializes onto its own loop. Add unit test patching threading.current_thread to non-main and asserting call_from_thread invoked. |
| T-M9-02-04 | DoS | BudgetMeter division-by-zero on early status() call | mitigate | W5 contract: BudgetMeter renders em-dash placeholder when total<=0. Test asserts no division occurs in that branch. |
</threat_model>

<verification>
- 11+ tests across two new files (8 in widget/shell + 9 in renderer) plus Plan 01's 13 tests all green.
- Glyph + color audit greps all pass.
- ConfidenceBar locked at 16 cells per W4; BudgetMeter handles zero-total per W5.
- Renderer protocol conformance asserted via runtime_checkable isinstance.
</verification>

<success_criteria>
1. `voss.harness.tui.app.VossTUIApp` mounts the 5-region grid on an 80×24 terminal without truncation.
2. `voss.harness.tui.renderer.TextualRenderer` is a structural subtype of `voss.harness.render.Renderer`.
3. ConfidenceBar widget output is byte-stable across runs at fixed inputs AND exactly 16 cells wide.
4. BudgetMeter widget renders em-dash on zero-total; never divides by zero; never substitutes total=1.
5. Glyph + color contract enforced from single source files (one grep finds all uses).
6. M9-01 force_tui hook now returns a real TextualRenderer; default user path unchanged.
</success_criteria>

<output>
After completion, create `.planning/phases/M9-tui-shell-tui-01/M9-02-SUMMARY.md`.
</output>
</content>
</invoke>