# Phase T8: Input Bar Ergonomics (v0.2) - Pattern Map

**Mapped:** 2026-05-17
**Files analyzed:** 11 (7 modified, 4 new source, 4 new test + snapshot dir)
**Analogs found:** 10 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/tui/widgets/input_bar.py` | widget (rewrite) | event-driven | self (current `input_bar.py`) | exact |
| `voss/harness/tui/widgets/local_block.py` | widget (new) | event-driven | `turn_view.py` (`append_turn` pattern) | role-match |
| `voss/harness/tui/widgets/__init__.py` | config | — | self (current `__init__.py`) | exact |
| `voss/harness/tui/keymap.py` | config | — | self (current `keymap.py`) | exact |
| `voss/harness/tui/styles.tcss` | config | — | self (current `styles.tcss`) | exact |
| `voss/harness/tui/recorder_bridge.py` | service (extend) | event-driven | self (current `recorder_bridge.py`) | exact |
| `voss/harness/tui/app.py` | controller (extend) | request-response | self (current `app.py`) + `recorder_bridge.py` pattern | exact |
| `tests/harness/tui/test_input_bar_textarea.py` | test | — | `test_app_shell.py`, `test_full_flow_pilot.py` | exact |
| `tests/harness/tui/test_prefix_dispatch.py` | test | — | `test_recorder_bridge.py` | exact |
| `tests/harness/tui/test_reverse_search.py` | test | — | `test_slash_palette.py` (pure-logic unit + async pilot) | role-match |
| `tests/harness/tui/test_paste_image.py` | test | — | `test_capability_and_plain_fallback.py` (monkeypatch + probe) | role-match |

---

## Pattern Assignments

### `voss/harness/tui/widgets/input_bar.py` (widget, rewrite — INPUT-01..05)

**Analog:** `voss/harness/tui/widgets/input_bar.py` (current, to be replaced)

**Imports pattern** (lines 1-13):
```python
from __future__ import annotations

from textual.message import Message
from textual.widgets import Input

from .. import glyphs
```
T8 replacement imports:
```python
from textual.message import Message
from textual.widgets import TextArea, Static
from textual.widget import Widget

from .. import glyphs
```

**`Submitted` message contract** — preserve exactly (lines 30-35):
```python
class Submitted(Message):
    """Posted when user presses Enter on a non-empty input."""

    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value
```
This contract is M9-locked. T8 must not rename it or change the `value: str` field.

**`_on_key` key-intercept pattern** (lines 20-28, current slash guard):
```python
async def _on_key(self, event) -> None:
    # Intercept `/` ONLY when the input is currently empty so the palette
    # opens before Input's printable-character handler inserts a literal.
    if event.key == "slash" and not self.value:
        event.prevent_default()
        event.stop()
        self.action_open_palette()
        return
    await super()._on_key(event)
```
T8 extends this to intercept `enter`, `shift+enter`, and `ctrl+r` BEFORE calling `super()._on_key()`. See RESEARCH.md Pattern 1 for the full verified intercept order. **Key discipline:** `event.prevent_default()` + `event.stop()` must come before any awaited call; `return` must follow each handled branch.

**`action_submit` pattern** (lines 49-53, current):
```python
async def action_submit(self) -> None:
    value = self.value
    await super().action_submit()
    if value.strip():
        self.post_message(self.Submitted(value))
```
T8 replacement uses `self.text` (not `.value`; TextArea API), `self.load_text("")` to clear, and inserts `!`/`#` prefix dispatch branches BEFORE posting `Submitted`. See RESEARCH.md Pattern 5 for the verified dispatch structure.

**`action_open_palette` pattern** (lines 55-77 — slash palette mount):
```python
def action_open_palette(self) -> None:
    if self.value:
        self.insert_text_at_cursor("/")
        return
    from .slash_palette import SlashPalette
    registry = getattr(self.app, "slash_registry", None)
    if registry is None:
        return
    try:
        existing = self.app.query_one(SlashPalette)
    except Exception:  # noqa: BLE001
        existing = None
    if existing is not None:
        return
    palette = SlashPalette(registry)
    self.app.mount(palette, before=self)
```
T8: replace `self.value` guard with `self.query_one(TextArea).text.strip()` check; replace `self.insert_text_at_cursor("/")` with `self.query_one(TextArea).insert("/")`. Everything else carries forward.

**Anti-pattern to avoid:** `self.value` does not exist on TextArea. After the widget swap, all `.value` accesses (including tests `test_slash_palette.py:122` and `test_full_flow_pilot.py:66-70`) must change to `.text`.

---

### `voss/harness/tui/widgets/local_block.py` (widget, new)

**Analog:** `voss/harness/tui/widgets/turn_view.py`

**Widget base + `Rich.Text` render pattern** (lines 18-55 of `turn_view.py`):
```python
from rich.text import Text
from textual.widgets import RichLog

class TurnView(RichLog):
    def __init__(self, **kw) -> None:
        super().__init__(highlight=False, markup=False, wrap=True, **kw)

    def append_turn(self, role: str, body: str, ...) -> None:
        head = Text()
        head.append(role, style="bold")
        head.append(f"  · {timestamp}", style="dim")
        self.write(head)
        self.write(Text(body, no_wrap=False))
```
`LocalBlock` variants follow the same `Text` composition pattern: construct a `Text`, `.append()` segments with named styles from the palette (`"bold"`, `"dim"`, `"$warn"`, `"$accent"`, etc.), then `self.write(text)`. Do not use markup strings.

**`LocalBlockNotice` auto-remove pattern** — analog from `app.py` worker pattern:
```python
# Textual timer-based remove (use call_later, not asyncio.sleep)
self.set_timer(3.0, self.remove)   # call inside on_mount of LocalBlockNotice
```
T8-UI-SPEC locks: auto-remove at 3000ms OR next submit, whichever fires first. The widget must also expose a `.dismiss()` method that cancels the timer and calls `self.remove()`.

**Note from RESEARCH.md A2:** The planner chose `LocalBlockNotice` as a separate mounted widget (because it needs a `.remove()` handle for the timer). `LocalBlockShell` and `LocalBlockNote` can be appended via `TurnView.append_local(kind, body, footer)` or as a similar `Static` widget — planner decides. The invariant: they must never be added to the `messages` list that `run_turn` receives.

---

### `voss/harness/tui/keymap.py` (config, add `ctrl+r` binding)

**Analog:** `voss/harness/tui/keymap.py` (self)

**`Binding` dataclass + `KEYMAP` tuple pattern** (lines 12-38, full file):
```python
@dataclass(frozen=True)
class Binding:
    key: str
    context: str  # "global" | "input" | "main" | "modal"
    action: str
    description: str

KEYMAP: tuple[Binding, ...] = (
    ...
    Binding("enter", "input", "submit", "Submit task"),
    Binding("shift+enter", "input", "newline", "Insert newline"),
    Binding("slash", "input", "open_palette", "Open slash command palette"),
    ...
)
```
T8 adds exactly **one line** after the existing `input` context bindings:
```python
Binding("ctrl+r", "input", "reverse_search", "Reverse-search input history"),
```
No other line in `keymap.py` is touched. The existing `ctrl+f → open_search` (`main` context, line 35) must not be moved or modified.

---

### `voss/harness/tui/styles.tcss` (config, add T8 classes)

**Analog:** `voss/harness/tui/styles.tcss` (self)

**Existing `#input` block** (lines 49-54):
```tcss
#input {
    dock: bottom;
    height: 1;
    min-height: 1;
    max-height: 5;
}
```
T8 replaces `height: 1` with `height: auto` (the only change to this block):
```tcss
#input {
    dock: bottom;
    height: auto;
    min-height: 1;
    max-height: 5;
}
```

**Existing utility class pattern** (lines 56-74) — follow exactly; new classes append after `.dim`:
```tcss
.accent {
    color: $accent;
}
.signal-good { color: $good; }
.signal-warn  { color: $warn; }
.signal-error { color: $error; }
.dim          { color: $dim; }
```
T8 appends the 5 new classes defined in `T8-UI-SPEC.md §tcss Additions` verbatim — `.local-block`, `.local-block--shell > .sigil`, `.local-block--note > .sigil`, `.local-block--notice`, `.reverse-search-bar .rs-label`, `.reverse-search-bar .rs-query`. No existing class is modified. The hex palette comment block at the top of the file must not acquire new entries — T8 uses only existing `$accent`, `$dim`, `$warn`, `$good`, `$error` variables.

---

### `voss/harness/tui/recorder_bridge.py` (service, extend with `.emit()`)

**Analog:** `voss/harness/tui/recorder_bridge.py` (self)

**`_call` helper pattern** (lines 58-65):
```python
def _call(self, method_name: str, *args, **kwargs) -> None:
    fn = getattr(self.app, method_name, None)
    if fn is None:
        return
    try:
        fn(*args, **kwargs)
    except Exception:  # noqa: BLE001 — bridge must never crash the agent
        pass
```
T8 adds one new public method using the exact same `_call` delegation and the same `except Exception: pass` guard:
```python
def emit(self, event_name: str, payload: dict) -> None:
    """Emit a local TUI event (not from RunRecorder) to the app."""
    self._call("on_local_event", event_name, payload)
```
The `flush()` method and `_seen` dict are **not modified**. The M9-04 contract ("zero changes to recorder.py or voss_runtime") still applies.

---

### `voss/harness/tui/app.py` (controller, add handler + run_turn wiring)

**Analog:** `voss/harness/tui/app.py` (self)

**`__init__` extension pattern** (lines 41-61):
```python
def __init__(self, *, session_id: str = "", model: str = "", ..., **kw) -> None:
    super().__init__(**kw)
    self.session_id = session_id
    self.model = model
    ...
    self.active_turn_task: Optional[asyncio.Task] = None
```
T8 adds `history: EpisodicMemory | None = None` parameter to `__init__` and stores it as `self.history`. This wires the Ctrl-R corpus access from `InputBar` (via `self.app.history`).

**Existing mutator method pattern** (lines 187-209, `update_inspected` / `append_tool_line`):
```python
def update_inspected(self, paths: list[str]) -> None:
    try:
        tv = self.query_one("#main", TurnView)
    except Exception:  # noqa: BLE001
        return
    for path in paths:
        tv.append_turn("inspect", path)
```
T8 adds `on_input_bar_submitted` and `on_local_event` handlers following the same pattern: `try: ... query_one("#main", TurnView) ... except Exception: return`. The `on_local_event` handler dispatches to `tv.append_local(...)` or mounts a `LocalBlockNotice`.

**`register_turn_task` / worker pattern** (lines 63-78):
```python
def register_turn_task(self, task: asyncio.Task) -> None:
    if self.active_turn_task is not None and not self.active_turn_task.done():
        raise RuntimeError("active turn task already registered")
    self.active_turn_task = task
    task.add_done_callback(self._clear_turn_task)
```
T8's `on_input_bar_submitted` creates a new `asyncio.Task` (via `asyncio.create_task`) wrapping `run_turn`, then calls `self.register_turn_task(task)`. This reuses the existing cancellation plumbing (`action_interrupt`). See RESEARCH.md §Pitfall 4 for the full wiring path.

**NOTE — RESEARCH.md A4:** The TUI submit→`run_turn` wiring is an implicit T8 deliverable (there is currently no `on_input_bar_submitted` handler in `app.py`). The planner must include this in scope.

---

### `tests/harness/tui/test_input_bar_textarea.py` (test, new — INPUT-01)

**Analog:** `tests/harness/tui/test_app_shell.py` + `test_full_flow_pilot.py`

**App-fixture pattern** (lines 16-95 of `test_app_shell.py`):
```python
@pytest.mark.asyncio
async def test_app_default_focus_is_input_bar() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        focused = pilot.app.focused
        assert focused is not None
        assert focused.id == "input"
```
Repeat for all INPUT-01 unit tests. Use `app.run_test()` context manager, `await pilot.press(...)`, `await pilot.pause()` to flush the event loop. Use `pilot.app.query_one("#input", InputBar)` to get the widget.

**Key tests required** (per RESEARCH.md Pitfall 3 — `.value` → `.text`):
- Test that `InputBar` no longer has `.value` attribute after the TextArea swap.
- Test that `InputBar.textarea.text` (or exposed `.text` property) returns typed content.
- Must also update the two existing tests that break: `test_slash_palette.py:121-122` (`input_bar.value = ""`) and `test_full_flow_pilot.py:66-70` (`getattr(input_bar, "value", None)`).

**`await pilot.pause()` pattern** — always call after `pilot.press(...)` sequences to flush posted messages before asserting DOM state.

---

### `tests/harness/tui/test_prefix_dispatch.py` (test, new — INPUT-02/03 + recorder asserts R1/R2)

**Analog:** `tests/harness/tui/test_recorder_bridge.py`

**Recorder mock pattern** (lines 13-16 of `test_recorder_bridge.py`):
```python
def _bridge_with_app() -> tuple[RecorderBridge, MagicMock]:
    rec = RunRecorder.start()
    app = MagicMock()
    return RecorderBridge(rec, app), app
```
For prefix-dispatch tests, use `MagicMock()` to stub `recorder_bridge.emit` and assert it was called with `"shell.local"` / `"memory.note"` and the expected payload fields. Use `unittest.mock.MagicMock` or `pytest-mock`'s `mocker.Mock()`.

**Assertion pattern** (lines 43-48):
```python
bridge.flush()
app.append_tool_line.assert_called_once()
args, kwargs = app.append_tool_line.call_args
assert kwargs.get("state") == "ok"
assert "pytest -q" in args[0]
```
Apply same pattern for emit assertions:
```python
recorder_bridge.emit.assert_called_once_with("shell.local", ...)
call_kwargs = recorder_bridge.emit.call_args[0][1]  # payload dict
assert call_kwargs["cmd"] == "ls -la"
assert "exit_code" in call_kwargs
```

**`sandbox.shell_allowed` stub:** Use `monkeypatch.setattr("voss.harness.sandbox.shell_allowed", lambda cmd, **kw: (True, "ok"))` to isolate the dispatch test from the real deny-set.

---

### `tests/harness/tui/test_reverse_search.py` (test, new — INPUT-04)

**Analog:** `tests/harness/tui/test_slash_palette.py` (pure-logic unit tests + async pilot tests)

**Pure-logic unit test pattern** (lines 17-66 of `test_slash_palette.py`):
```python
def test_rank_substring_match_first() -> None:
    out = rank_commands("he", ["/help", "/cost", "/exit", "/agents"])
    assert out[0] == "/help"
```
Extract `_build_corpus(history: EpisodicMemory) -> list[str]` as a standalone pure function (similar to `rank_commands`) so it can be unit-tested without a Textual app. Test the deduplication logic, role filtering, and most-recent-first ordering in pure unit tests (no `async with app.run_test()`).

**Episodic store seeding pattern** — use the same approach as `conftest.py:fake_session_corpus` for deterministic seeding. For Ctrl-R tests, construct a minimal `EpisodicMemory` with known `Turn` entries:
```python
from voss_runtime.memory.episodic import EpisodicMemory

def _seeded_history(*user_prompts: str) -> EpisodicMemory:
    h = EpisodicMemory()
    for p in user_prompts:
        h.add(p, role="user")
    return h
```

**Async pilot test pattern for search mode** (lines 80-96 of `test_slash_palette.py`):
```python
@pytest.mark.asyncio
async def test_palette_mount_shows_filtered_results() -> None:
    app = VossTUIApp(slash_registry=registry)
    async with app.run_test() as pilot:
        ...
        palette.update_query("he")
        labels = getattr(palette, "_labels", [])
        assert any("/help" in label for label in labels)
```
For Ctrl-R: inject seeded `EpisodicMemory` into `VossTUIApp(history=seeded)`, press `ctrl+r`, type query chars, assert the search-mode display string.

---

### `tests/harness/tui/test_paste_image.py` (test, new — INPUT-05)

**Analog:** `tests/harness/tui/test_capability_and_plain_fallback.py` (monkeypatch + probe pattern)

**Monkeypatch pattern for OS-level probe** (from `capability.py` tests):
```python
def test_tui_should_activate_plain_flag(monkeypatch) -> None:
    decision = tui_should_activate(argv=["--plain"], ...)
    assert decision.activate is False
```
For paste-image tests, monkeypatch `PIL.ImageGrab.grabclipboard` to return either a mock `Image.Image` instance or `None`:
```python
def test_image_paste_vision_capable(monkeypatch):
    mock_img = MagicMock()
    mock_img.mode = "RGB"  # makes isinstance(result, Image.Image) True
    monkeypatch.setattr(
        "voss.harness.tui.widgets.input_bar.ImageGrab.grabclipboard",
        lambda: mock_img,
    )
    ...
```

**`NotImplementedError` fallback test** — test that `_probe_clipboard_image` returns `None` (graceful no-op) when `grabclipboard` raises `NotImplementedError` (Linux without `wl-paste`/`xclip`):
```python
monkeypatch.setattr(
    "voss.harness.tui.widgets.input_bar.ImageGrab.grabclipboard",
    lambda: (_ for _ in ()).throw(NotImplementedError),
)
result = input_bar._probe_clipboard_image()
assert result is None
```

**`_model_supports_vision` test** — test that `"claude-3-sonnet"`, `"gpt-4o"`, `"gemini-1.5-pro"` return `True` and `"claude-instant-1"`, `"gpt-3.5-turbo"` return `False`. This function is name-based (RESEARCH.md Pitfall 6 — no provider API exists).

**Timer mock for 3s auto-remove** — use `pytest-asyncio` + `app.run_test()` pilot, monkeypatch `call_later`/`set_timer` to fire immediately:
```python
async with app.run_test() as pilot:
    ...  # trigger no-vision paste
    await pilot.pause()
    # advance timer: mock set_timer to call callback synchronously in test
    notice = pilot.app.query(LocalBlockNotice).first()  # asserts it mounted
    notice.remove()  # test removal contract manually if timer mock is complex
```

---

## Shared Patterns

### `pytest.mark.asyncio` + `app.run_test()` fixture
**Source:** All TUI tests (`test_app_shell.py`, `test_full_flow_pilot.py`, `test_slash_palette.py:80+`, `test_turn_view_streaming.py`)
**Apply to:** All four new test files
```python
@pytest.mark.asyncio
async def test_foo() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        await pilot.press("...")
        await pilot.pause()
        widget = pilot.app.query_one("#input", InputBar)
        assert ...
```
`asyncio_mode = "auto"` is set in `pyproject.toml:68` — the `@pytest.mark.asyncio` decorator is technically optional but all existing tests use it explicitly; match that style.

### Error guard in app mutators
**Source:** `voss/harness/tui/app.py` lines 187-209
**Apply to:** All new app mutator methods (`on_input_bar_submitted`, `on_local_event`)
```python
try:
    tv = self.query_one("#main", TurnView)
except Exception:  # noqa: BLE001
    return
```
Every Textual DOM query in app mutators wraps in `try/except Exception: return` with `# noqa: BLE001`. This matches the existing pattern in `update_inspected`, `update_changed`, `append_tool_line`, `collapse_subagent`.

### `from __future__ import annotations` + `# noqa: BLE001`
**Source:** Every file in `voss/harness/tui/` (checked: `app.py:1`, `recorder_bridge.py:1`, `input_bar.py:7`, `slash_palette.py:1`)
**Apply to:** All new and modified source files. All bare `except Exception:` blocks get the `# noqa: BLE001` comment.

### `Text` + no-markup pattern for untrusted content
**Source:** `voss/harness/tui/widgets/turn_view.py` line 55
**Apply to:** `local_block.py` and any new widget writing user-originated content
```python
# `body` is untrusted (LLM output / user input) — render via plain Text, no markup.
self.write(Text(body, no_wrap=False))
```
All content derived from user input (`!cmd` output, `#note` text, search results) must be wrapped in `Text(...)` with no markup interpolation.

### `sandbox.shell_allowed` call contract
**Source:** `voss/harness/sandbox.py` lines 43-73
**Apply to:** `input_bar.py` `_dispatch_shell` method (INPUT-02)
```python
from voss.harness.sandbox import shell_allowed, split_command

allowed, reason = shell_allowed(cmd)
if not allowed:
    # Render local block with reason; do not proceed
    return
# Then: asyncio.create_subprocess_exec(*split_command(cmd), ...)
```
`split_command(cmd)` returns the argv list. `shell_allowed` must be called first and its `(False, reason)` result surfaces in a local block (not silently dropped).

### `voss_md.parse()` + `_render()` atomic-write pattern
**Source:** `voss/harness/voss_md.py` lines 59-101, 206-270
**Apply to:** The new `append_voss_notes_bullet()` helper (INPUT-03)
```python
# atomic write pattern from write_fence_body (lines 267-270):
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(new_text)
import os; os.replace(tmp, path)
```
Do NOT use `write_fence_body` for the `## Notes` section — it is a human block, not a machine fence. See RESEARCH.md Pitfall 5 for the verified distinction (`parse()` returns `kind="human"` for plain markdown sections).

---

## Snapshot Tests (pytest-textual-snapshot)

**No existing analog in this repo** — `pytest-textual-snapshot` is not yet installed (absent from `pyproject.toml`).

Wave 0 must:
1. Add `"pytest-textual-snapshot>=1.1.0"` to `[project.optional-dependencies.dev]` in `pyproject.toml` (after line 40).
2. Create `tests/harness/tui/snapshots/` directory.
3. Run `pytest tests/harness/tui/ --snapshot-update -k T8` to generate 11 baseline SVG files (RESEARCH.md Pitfall 8).

**`snap_compare` fixture pattern** (from pytest-textual-snapshot docs; no in-repo example yet):
```python
from pytest_textual_snapshot import snap_compare

def test_input_bar_single_line(snap_compare):
    async def run_before(pilot):
        await pilot.pause()

    assert snap_compare(
        "voss/harness/tui/app.py",  # or pass app instance
        run_before=run_before,
        terminal_size=(80, 24),
    )
```
See T8-RESEARCH.md §Validation Architecture for the 11 required snapshot anchors and their test file assignments.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/harness/tui/snapshots/` | test artefacts | — | No snapshot tests exist in the repo yet; `pytest-textual-snapshot` not yet installed |

---

## Metadata

**Analog search scope:** `voss/harness/tui/`, `voss/harness/`, `tests/harness/tui/`, `tests/harness/conftest.py`
**Files read:** 17 source/test files
**Pattern extraction date:** 2026-05-17
