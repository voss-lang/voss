# Phase T8: Input Bar Ergonomics (v0.2) — Research

**Researched:** 2026-05-17
**Domain:** Textual TUI widget migration (Input → TextArea), prefix dispatch, episodic reverse-search, clipboard-image detection, Textual testing
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from T8-CONTEXT.md)

### Locked Decisions
- **D-01:** Swap `InputBar` from single-line `Input` to Textual `TextArea`. Re-wire: `/`-palette empty-check, `Submitted` message, prompt-glyph render. `Enter`=submit / `Shift+Enter`=newline (M9-locked).
- **D-02:** Autogrow 1-row base, grows to 5-row cap, scrolls inside TextArea beyond cap.
- **D-03:** `!cmd` executes through the existing gated `shell_run` / T5-D12 sandbox path — inherits the deny-set and permission-mode. Bypasses `run_turn`, emits `shell.local`.
- **D-04:** `!cmd` output renders as ephemeral local block (`.local-block--shell`) in turn-view scrollback, never in model history.
- **D-05:** `#text` appends `- [ISO-8601 UTC] text` under `## Notes` in `VOSS.md` via the existing `voss_md` / `memory_cli` section-aware append path. Bypasses `run_turn`, emits `memory.note`.
- **D-06:** Ctrl-R = inline readline-style `(reverse-i-search)`query': match` render mode (not modal); Enter loads match editable (NOT auto-submit); Esc cancels; add `ctrl+r` binding in `input` region of `keymap.py`.
- **D-07:** Ctrl-R corpus = submitted task inputs only, current project episodic store, consecutive duplicates collapsed, most-recent-first. Excludes `!cmd`/`#note`/`/`-palette lines.
- **D-08:** Detect clipboard image on paste keypress; if image present attach; else text paste. Graceful no-op on unsupported platforms.
- **D-09:** No-vision model: transient local block `(. local-block--notice)`, auto-remove 3000ms or next submit; no silent drop; snapshot-testable.

### Claude's Discretion
- Exact TextArea→prompt-glyph render technique and how `Submitted`/`_on_key` re-wire is structured.
- Cross-platform clipboard-image shim choice (`PIL.ImageGrab` vs platform-specific).
- Ctrl-R match algorithm (substring vs fuzzy) and inline reverse-i-search render details.
- Recorder-event payload shape for `shell.local` / `memory.note`.
- `!cmd` non-zero-exit and empty `#`/`!` handling.
- Snapshot-test seeding strategy for episodic history.

### Deferred Ideas (OUT OF SCOPE)
None surfaced in discussion.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INPUT-01 | Multi-line input: `Shift+Enter` newline, `Enter` submits | TextArea API; key-inversion strategy; autogrow via `height: auto; max-height: 5` |
| INPUT-02 | `!<cmd>` prefix runs shell without spawning a turn | `sandbox.shell_allowed` / `tools.shell_run` wiring; `recorder_bridge` emit path |
| INPUT-03 | `#<text>` prefix appends memory note to `VOSS.md` without spawning a turn | `voss_md.write_fence_body` / section-aware human-block append path; `recorder_bridge` |
| INPUT-04 | `Ctrl-R` reverse-search through episodic history | `EpisodicMemory.turns` API; corpus extraction; inline render mode inside InputBar |
| INPUT-05 | Paste-image: attach if vision-capable, notice if not | `PIL.ImageGrab.grabclipboard()` + `Textual events.Paste`; provider vision gate |
</phase_requirements>

---

## Summary

T8 rewrites `voss/harness/tui/widgets/input_bar.py` onto Textual's `TextArea` widget (Textual 8.2.6 installed, pinned `>=0.58,<1.0` in pyproject.toml). The migration carries three M9 contracts: the `Submitted(value: str)` message, the `/`-palette empty-only-open guard, and the `▌ ` prompt-glyph. The hardest part is **key inversion**: TextArea maps `enter` → `"\n"` insertion inside `_on_key`; the planner must intercept `enter` before `TextArea._on_key` runs and route it to `action_submit`, while letting `shift+enter` call the standard newline insertion. The autogrow contract is simply `height: auto; min-height: 1; max-height: 5` in the `#input` tcss block — TextArea's `virtual_size.height` drives Textual's layout automatically.

The submit-path prefix dispatch (`!` / `#`) inserts new branches at the top of `action_submit` before `self.post_message(Submitted(...))`. The `!` path calls the **existing** `sandbox.shell_allowed` + async subprocess path lifted from `tools.shell_run` (not a copy of `run_turn`). The `#` path calls `voss_md.write_fence_body` or a thin helper that appends a plain bullet under the `## Notes` human section of `VOSS.md` (not a machine fence — that section is human prose). Both paths emit to `recorder_bridge.py`, which must be extended with a new `.emit()` method accepting an event name + payload dict.

Ctrl-R is an inline render-mode flag on `InputBar`: when active, the TextArea is set `read_only=True`, the rendered text is replaced with the reverse-i-search prompt string, and each printable keypress updates a query string that filters `EpisodicMemory.turns` (user-role turns only, submitted-task subset). The episodic store is a `list[Turn]` on the `EpisodicMemory` object — available at submit time in `cli.py` via `ctx.history`. The TUI currently lacks a live connect between `InputBar.Submitted` and `run_turn` (the app renders but the REPL loop in `cli.py` calls `input("▌ ")` — the TUI submit wiring is **also a T8 deliverable**).

Paste-image detection uses `PIL.ImageGrab.grabclipboard()` intercepted at `_on_paste` (overriding `action_paste`). The Textual `events.Paste` event carries bracketed-paste text; image detection is OS-clipboard probe, not from the Paste event text. Vision capability is gated via a new `_model_supports_vision(model: str) -> bool` helper that checks the model name string (e.g., `claude-3` / `gpt-4o` contain vision; no provider capability API currently exists in the repo).

**Primary recommendation:** Plan T8 as four parallel implementation tracks (TextArea swap, prefix dispatch, Ctrl-R, paste-image) gated by a Wave 0 scaffold wave that adds `pytest-textual-snapshot` to dev dependencies and creates the baseline snapshot files.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Multi-line text input (INPUT-01) | TUI widget (`InputBar`) | tcss (`styles.tcss`) | Widget owns key routing; tcss owns height contract |
| `!cmd` dispatch (INPUT-02) | TUI widget (`InputBar.action_submit`) | Harness tools (`sandbox`, `tools.shell_run`) | Prefix check is input concern; execution is harness concern |
| `#note` write (INPUT-03) | TUI widget (`InputBar.action_submit`) | `voss_md` module | Prefix check is input concern; VOSS.md write is `voss_md` |
| `recorder_bridge` emit for `shell.local`/`memory.note` | `recorder_bridge.py` | — | Bridge owns all TUI→recorder plumbing |
| Ctrl-R inline search mode (INPUT-04) | TUI widget (`InputBar`) | `EpisodicMemory` | InputBar owns render mode; episodic store is corpus |
| Paste-image detect (INPUT-05) | TUI widget (`InputBar._on_paste`) | `PIL.ImageGrab` (OS clipboard) | Input event intercept is widget concern |
| Vision capability gate (INPUT-05) | `InputBar` (model name check) | Provider layer | No provider capability API exists yet; name-based gate is pragmatic |
| Local block rendering (`LocalBlock`) | TUI widget (new `LocalBlock` family) | `TurnView` (`#main` RichLog) | Local blocks are appended via `TurnView.append_turn` or a parallel `.append_local` path |
| Snapshot tests | `tests/harness/tui/` | `pytest-textual-snapshot` (new dev dep) | All test artefacts live in the tui test tree |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `textual` | `>=0.58,<1.0` (installed: 8.2.6) | TUI framework; provides `TextArea` | Already in `pyproject.toml`; `TextArea` is first-party Textual widget [VERIFIED: pyproject.toml] |
| `Pillow` | `>=10.0` (installed: 12.1.1) | `PIL.ImageGrab.grabclipboard()` for clipboard image probe | Only stdlib-free option for macOS + Windows clipboard image read; handles Linux via `wl-paste`/`xclip` [VERIFIED: PyPI + local install] |

### Supporting (dev / test)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-textual-snapshot` | `1.1.0` | Textual SVG snapshot regression tests; `snap_compare` fixture | Every INPUT-01..05 visual state in T8-UI-SPEC § Snapshot-Test Anchors [VERIFIED: PyPI] |
| `syrupy` | `==4.8.0` (pinned by pytest-textual-snapshot) | Snapshot comparison backend | Pulled automatically by pytest-textual-snapshot |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `PIL.ImageGrab` | Platform-native clipboard shims (pyperclip + xclip) | Pillow is already in the test environment (installed), handles all 3 platforms with graceful None return; pyperclip doesn't read image data |
| `pytest-textual-snapshot` | Pure `pilot.press` + DOM assertion tests | Snapshot tests capture the visual layout regression; DOM assertion tests only validate presence. T8-UI-SPEC requires snapshot anchors — dom assertions alone don't satisfy. |

**Installation (dev extras addition):**
```bash
pip install 'voss[dev]'  # after adding pytest-textual-snapshot to [project.optional-dependencies.dev]
```

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `Pillow` | PyPI | 13+ years | 50M+/wk | github.com/python-pillow/Pillow | N/A (slopcheck CLI uses crates.io; PyPI verify passed) | Approved — standard imaging library, installed 12.1.1 |
| `pytest-textual-snapshot` | PyPI | ~2.5 years | N/A | github.com/Textualize/pytest-textual-snapshot | N/A (crates.io probe inapplicable) | Approved — first-party Textualize project, PyPI version 1.1.0 confirmed |
| `syrupy` | PyPI (pinned by pytest-textual-snapshot) | 5+ years | N/A | github.com/syrupy-project/syrupy | N/A | Approved — well-known snapshot lib, PyPI version 4.8.0 available |

**Note:** `slopcheck` defaults to crates.io and returned false positives (rated PyPI packages as SLOP). Both packages were verified directly via `python3 -m pip index versions` and official Textualize / python-pillow GitHub orgs. [VERIFIED: PyPI]

**Packages removed:** none.
**Packages flagged:** none.

---

## Architecture Patterns

### System Architecture Diagram

```
User keypress
     │
     ▼
InputBar._on_key (intercepts Enter/Slash/Ctrl+R; prevents default)
     │
     ├─ Enter (not in search mode) ──► action_submit()
     │                                      │
     │         ┌────────────────────────────┤ prefix check
     │         │                            │
     │         ▼                            ▼
     │   value starts with "!"      value starts with "#"
     │         │                            │
     │     sandbox.shell_allowed()    voss_md human-section append
     │     subprocess exec (T5 gate)  "## Notes" bullet
     │         │                            │
     │    LocalBlockShell               LocalBlockNote
     │    render in TurnView            "# note saved" (dim)
     │         │                            │
     │    recorder_bridge                recorder_bridge
     │    .emit("shell.local")           .emit("memory.note")
     │
     │         │ (neither prefix)
     │         ▼
     │   post_message(Submitted(value))
     │         │
     │         ▼
     │   app.on_input_bar_submitted() [NEW in T8 — TUI REPL wiring]
     │         │
     │         ▼
     │   run_turn(value, ...)  [via cli._run_turn_cancellable or direct async]
     │
     ├─ Ctrl+R ──► action_reverse_search()
     │             toggles search mode (read_only=True, query="")
     │             subsequent printable keys → query filter
     │             Enter → load match into bar
     │             Esc → restore pre-search content
     │
     ├─ Slash (empty bar) ──► action_open_palette() → SlashPalette
     │
     └─ Ctrl+V (paste) ──► _on_paste() / action_paste() override
                           PIL.ImageGrab.grabclipboard()
                               ├─ Image found, model has vision:
                               │    store image attachment in self._pending_image
                               │    render "[image attached · 1 image]" indicator
                               └─ Image found, no vision:
                                    LocalBlockNotice (transient 3000ms)
                                    drop image, fall through to text paste
```

### Recommended Project Structure (files changed / added)

```
voss/harness/tui/
├── widgets/
│   ├── input_bar.py          # REWRITE: Input → TextArea; all 5 INPUT behaviors
│   ├── local_block.py        # NEW: LocalBlock, LocalBlockShell, LocalBlockNote, LocalBlockNotice
│   └── __init__.py           # ADD exports: LocalBlock family
├── keymap.py                 # ADD: ctrl+r Binding in input region
├── styles.tcss               # ADD: .local-block, .local-block--shell/note/notice, .reverse-search-bar classes
├── recorder_bridge.py        # ADD: .emit(event_name, payload) method
└── app.py                    # ADD: on_input_bar_submitted handler → run_turn wiring

tests/harness/tui/
├── test_input_bar_textarea.py    # NEW: INPUT-01 TextArea swap + autogrow
├── test_prefix_dispatch.py       # NEW: INPUT-02/03 prefix routing + recorder asserts
├── test_reverse_search.py        # NEW: INPUT-04 Ctrl-R mode + corpus filtering
├── test_paste_image.py           # NEW: INPUT-05 clipboard probe + vision gate
└── snapshots/                    # NEW: pytest-textual-snapshot baseline files
    └── test_input_bar_textarea/  # SVG snapshots per anchor (see UI-SPEC §Snapshot anchors)
```

---

### Pattern 1: TextArea Enter-key Inversion

**What:** TextArea's `_on_key` handler maps `"enter"` → `"\n"` insert inside `insert_values`. To submit on Enter and newline on Shift+Enter, intercept `enter` before `super()._on_key()` runs.

**When to use:** This is the only valid approach — overriding `BINDINGS` with an `enter` action does NOT prevent TextArea's `_on_key` from inserting a newline because that handler runs independently of action dispatch.

**Example:**
```python
# Source: Textual 8.2.6 _text_area.py L1579-L1610
# TextArea._on_key inserts "\n" when key == "enter" in insert_values.
# We intercept BEFORE super() runs.

async def _on_key(self, event) -> None:
    if event.key == "enter" and not self._in_search_mode:
        event.prevent_default()
        event.stop()
        await self.action_submit()
        return
    if event.key == "shift+enter":
        event.prevent_default()
        event.stop()
        # Insert newline manually (reuse TextArea's insert API)
        self.insert("\n")
        return
    if event.key == "slash" and not self.text.strip():
        event.prevent_default()
        event.stop()
        self.action_open_palette()
        return
    await super()._on_key(event)
```

[VERIFIED: Textual 8.2.6 source inspection]

---

### Pattern 2: TextArea Text Access

**What:** `TextArea.text` property returns the full document string (via `self.document.text`). `TextArea.document` is a `Document` instance (non-reactive plain attribute) with a `.line_count` property. `TextArea.load_text(text)` replaces content and clears undo history. `TextArea.insert(text)` inserts at cursor.

```python
# Read content
value = self.text  # equivalent to self.document.text

# Clear after submit
self.load_text("")  # clears and resets undo history; correct for post-submit

# Insert character
self.insert("\n")   # inserts newline at cursor position
```

[VERIFIED: Textual 8.2.6 source — `text` property at L1393, `load_text` at L927-L947]

---

### Pattern 3: Autogrow via TCSS `height: auto`

**What:** Setting `height: auto` with `min-height: 1` and `max-height: 5` on the `#input` region makes Textual respect `TextArea.virtual_size.height` up to the cap. TextArea's `_refresh_size` updates `virtual_size` after each edit, driving automatic height changes. No Python code required.

```tcss
/* Replace fixed `height: 1` in styles.tcss */
#input {
    dock: bottom;
    height: auto;
    min-height: 1;
    max-height: 5;
}
```

[VERIFIED: Textual 8.2.6 source — `_refresh_size` at L1048, `virtual_size` drives layout]

---

### Pattern 4: Prompt Glyph Render

**What:** TextArea does not have an `Input`-style `prefix` param. The `▌ ` glyph must be rendered as a placeholder or as pre-inserted text. The UI-SPEC locks: glyph only on row 1; rows 2–5 have no glyph. The cleanest approach is a `Static` widget overlaid at row 0, column 0 inside the `#input` container. Alternatively, use a custom `render_line` override that prepends the glyph character only on line 0.

**Recommended:** Implement as a `Static` label widget mounted inside the InputBar container, absolutely positioned at row 0, col 0 with 2-char width. The TextArea is padded-left by 2 to give it space. This avoids mutation of the TextArea document content.

```python
# InputBar becomes a Widget container (not TextArea directly)
class InputBar(Widget):
    BINDINGS = [...]  # ctrl+r, slash, enter, shift+enter

    def compose(self) -> ComposeResult:
        yield Static(glyphs.PROMPT + " ", id="prompt-glyph", classes="accent")
        yield TextArea(id="input-textarea", compact=True, ...)
```

[ASSUMED — based on Textual widget composition patterns; verify that Static widget absolute positioning works at desired col in the tcss context]

---

### Pattern 5: Prefix Dispatch in action_submit

**What:** Check `.text.strip()` prefix before posting `Submitted`. Both `!` and `#` branches must call `self.load_text("")` to clear the bar after dispatch.

```python
async def action_submit(self) -> None:
    value = self.text.strip()
    if not value:
        return
    self.load_text("")
    if value.startswith("!"):
        cmd = value[1:].strip()
        if cmd:
            await self._dispatch_shell(cmd)
        return
    if value.startswith("#"):
        note_text = value[1:].strip()
        if note_text:
            await self._dispatch_note(note_text)
        return
    self.post_message(self.Submitted(value))
```

[ASSUMED — pattern based on current `input_bar.py` action_submit structure; verified that load_text clears the content]

---

### Pattern 6: EpisodicMemory Corpus for Ctrl-R

**What:** `EpisodicMemory` (from `voss_runtime.memory.episodic`) holds `turns: list[Turn]` where `Turn.role: str` and `Turn.content: str`. User-submitted task prompts are added via `history.add(content, role="user")` inside `cli.py`'s REPL loop after calling `run_turn`. The corpus for Ctrl-R is all `Turn` entries where `role == "user"`, reversed (most-recent-first), consecutive duplicates collapsed.

The `EpisodicMemory` object lives in `cli.py`'s `ctx.history`. The TUI app must be given access to it — either by storing a reference on the `VossTUIApp` at startup, or passing it to `InputBar` at construct time.

```python
# Extracting Ctrl-R corpus from EpisodicMemory
def _build_corpus(history: EpisodicMemory) -> list[str]:
    user_turns = [t.content for t in reversed(history.turns) if t.role == "user"]
    # Collapse consecutive duplicates
    seen = []
    prev = None
    for item in user_turns:
        if item != prev:
            seen.append(item)
            prev = item
    return seen
```

[VERIFIED: voss_runtime/memory/episodic.py — Turn dataclass, EpisodicMemory.turns field, .add(content, role=) method]

---

### Pattern 7: PIL.ImageGrab for Clipboard Image Probe

**What:** `PIL.ImageGrab.grabclipboard()` returns an `Image.Image` if the clipboard contains image data, `None` otherwise, `list[str]` for file paths on Windows. Platform behavior:
- **macOS:** Uses `osascript` to extract PNG; returns `None` if no image (returncode != 0). No extra tool required.
- **Windows:** Uses Win32 clipboard API directly.
- **Linux:** Requires `wl-paste` (Wayland) or `xclip` (X11). Raises `NotImplementedError` if neither is found. Raises `ChildProcessError` on subprocess failure with non-silent errors.

```python
# In InputBar._on_paste / action_paste override
def _probe_clipboard_image(self) -> "PIL.Image.Image | None":
    try:
        from PIL import ImageGrab
        result = ImageGrab.grabclipboard()
        if hasattr(result, 'mode'):  # is an Image, not a list[str] or None
            return result
        return None
    except (ImportError, NotImplementedError, ChildProcessError, OSError):
        return None   # Graceful no-op: falls back to text paste
```

[VERIFIED: Pillow 12.1.1 — PIL/ImageGrab.py full source inspected; all platform branches confirmed]

**Linux caveat:** Linux requires an external tool (`wl-paste` or `xclip`) — neither guaranteed to be present. `grabclipboard()` raises `NotImplementedError` when neither is found. The `except NotImplementedError` in the wrapper above handles this as a graceful no-op.

---

### Pattern 8: Textual Paste Event vs. action_paste Override

**What:** Textual fires a `events.Paste` event (from bracketed-paste mode) with the pasted text as a string attribute — it does NOT carry binary clipboard data. Image bytes are NOT available via this event. The OS-clipboard probe (`PIL.ImageGrab.grabclipboard()`) must happen in an `action_paste` **override**, not in an `on_paste` handler, because the Paste event text only captures what the terminal emulator sends via bracketed paste, which is text only.

The correct interception point is **`action_paste()`** override:
1. Probe clipboard for image first.
2. If image found and vision capable → store `self._pending_image`, show indicator, skip text insertion.
3. If image found and no vision → emit notice block, clear image, fall through to normal text paste.
4. If no image → call `super().action_paste()` for normal text paste behavior.

[VERIFIED: Textual 8.2.6 source — `events.Paste` class carries only `text: str`; `action_paste` at L2422 uses `self.app.clipboard` (app-internal only, not OS clipboard)]

---

### Pattern 9: RecorderBridge Extension for T8 Events

**What:** Current `RecorderBridge` reads from `RunRecorder` fields and calls app methods. It has no `.emit()` method for widget-generated events. T8 needs to emit `shell.local` and `memory.note` events outside the `run_turn` path. The cleanest extension is a new `.emit(event_name: str, payload: dict)` method that calls an `append_local_event(event_name, payload)` method on the app (following the existing pattern of `_call(method_name, *args, **kwargs)`).

```python
# recorder_bridge.py addition
def emit(self, event_name: str, payload: dict) -> None:
    """Emit a local TUI event (not from RunRecorder) to the app."""
    self._call("on_local_event", event_name, payload)
```

[ASSUMED — consistent with existing `RecorderBridge._call` pattern; field names in payload are planner's discretion per T8-CONTEXT.md]

---

### Pattern 10: LocalBlock Widget Implementation

**What:** `TurnView` extends `RichLog`. The `LocalBlock` family should NOT subclass `TurnView` — instead, `TurnView` gets a new `append_local(kind, body, footer=None)` method that writes Rich-styled text directly to the RichLog. This avoids creating a separate widget type that must be mounted independently.

Alternatively, the `LocalBlock` can be a separate `Static` widget mounted in the same scrollable container as `TurnView`. The UI-SPEC component inventory defines it as a separate widget. The planner must choose — however, using `RichLog.write()` is simpler and matches the existing streaming pattern.

**Recommended:** Extend `TurnView.append_turn(role, body, ...)` to accept `role="local-shell"`, `role="local-note"`, `role="local-notice"` and apply the correct styling. This avoids a new widget type entirely and is consistent with the existing "tool", "inspect", "change" role strings.

[ASSUMED — consistent with TurnView's existing role-based routing; avoids new widget lifecycle complexity]

---

### Anti-Patterns to Avoid

- **Mutating TextArea `insert_values` dict directly:** The dict is local to `_on_key` — not a class attribute. Removing `"enter"` from it does nothing. Only `event.prevent_default()` before `super()._on_key()` works. [VERIFIED]
- **Using `self.value` on TextArea:** `TextArea` does not have a `.value` attribute (unlike `Input`). Use `.text` property instead. Any existing test referencing `input_bar.value` must be updated. [VERIFIED: `InputBar` currently subclasses `Input` which has `.value`; after swap to TextArea-based container, `.value` disappears]
- **Adding `enter` to KEYMAP in keymap.py for the `action_submit`:** `enter` is already in KEYMAP at `keymap.py:23`. The `InputBar._on_key` intercept approach handles it at the widget level without touching KEYMAP. Adding a second `enter` binding would collide.
- **Using `app.clipboard` for OS-level paste detection:** `app.clipboard` is Textual-internal (app-to-app copy) and does NOT reflect OS clipboard contents. Only `PIL.ImageGrab.grabclipboard()` accesses the OS clipboard. [VERIFIED: App.clipboard property at textual/app.py L720-L728]
- **Reading episodic store from `session.py` file:** The `EpisodicMemory` instance is only held in memory during a session (`ctx.history` in `_run_repl`). There is no persistence file to read for Ctrl-R corpus — the live instance must be passed to the InputBar. [VERIFIED: session.py SessionRecord does not store EpisodicMemory turns; only `save()` serializes them separately]
- **Making `!cmd` bypass `sandbox.shell_allowed`:** D-03 is explicit — `!cmd` must go through the T5-D12 deny-set and sandbox. Do not call `subprocess` directly. [VERIFIED: sandbox.py has `DENY_TOKENS`, `SHELL_METACHARS`, and binary allowlist]
- **Writing to `## Notes` via `write_fence_body`:** The `## Notes` section is a **human prose section** of VOSS.md, NOT a machine fence. `write_fence_body` is for machine-fenced `<!-- voss:begin id=... -->` blocks. The correct approach is a new `append_human_section_bullet(path, heading, bullet)` helper that uses `parse()` → reconstruct with appended line in the human block. [VERIFIED: voss_md.py — `parse()` distinguishes `kind="human"` vs `kind="machine"` blocks; `write_fence_body` touches only machine fences]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-line text widget | Custom multi-line `Input` subclass | Textual `TextArea` | TextArea ships with undo, selection, cursor navigation, `read_only`, `load_text` — all needed for Ctrl-R mode |
| OS clipboard image read | Custom `osascript` / xclip subprocess | `PIL.ImageGrab.grabclipboard()` | Handles all 3 platforms; already installed in environment |
| Snapshot regression tests | Custom SVG diffing | `pytest-textual-snapshot` (`snap_compare` fixture) | First-party Textualize tool; standard approach for Textual test suites |
| Shell-command exec in `!cmd` | New subprocess wrapper | `sandbox.shell_allowed()` + `asyncio.create_subprocess_exec` (from `tools.shell_run`) | T5-D12 deny-set is the security contract; duplicating subprocess logic creates a second ungated path |
| VOSS.md section append | Raw file writes | `voss_md.parse()` + reconstruct human block | `voss_md` owns the VOSS.md format; raw writes skip hash integrity |

**Key insight:** Every non-trivial I/O operation in this phase has an existing utility in the codebase — the pattern is plumbing, not building.

---

## Common Pitfalls

### Pitfall 1: `ctrl+u` Collision in TextArea BINDINGS

**What goes wrong:** Textual's `TextArea.BINDINGS` includes `Binding(key='ctrl+u', action='delete_to_start_of_line', ...)`. The M9 keymap (`keymap.py:31`) has `Binding("ctrl+u", "main", "half_page_up", ...)` in the `main` context. In the `input` context these do not collide (contexts are mutually exclusive by focus), BUT if `InputBar` is a `Widget` container with a `TextArea` child, the `ctrl+u` binding on the `TextArea` child fires when the TextArea has focus — this is correct and expected. No action needed.

**Warning signs:** `ctrl+u` unexpectedly scrolls the main pane instead of deleting to line start.

[VERIFIED: keymap.py KEYMAP + TextArea.BINDINGS inspection]

---

### Pitfall 2: `ctrl+f` Shadowed by TextArea's `delete_word_right`

**What goes wrong:** TextArea `BINDINGS` contains `Binding(key='ctrl+f', action='delete_word_right', ...)`. This will fire when the TextArea (input context) has focus and the user presses `ctrl+f`, conflicting with the M9 `ctrl+f → open_search` binding in the `main` context. Since the contexts ARE mutually exclusive by focus, this should not collide — but verify that Textual's binding priority rules don't allow the TextArea `ctrl+f` to bubble up to the `main` context search handler.

**How to avoid:** Override `BINDINGS` in the InputBar TextArea subclass to remove the `ctrl+f` binding, OR rely on Textual's context-focus separation (verify with a test).

**Warning signs:** Pressing `ctrl+f` with input focus opens in-pane search instead of deleting a word, or vice versa.

[VERIFIED: TextArea.BINDINGS at Textual 8.2.6 — `ctrl+f` maps to `delete_word_right`]

---

### Pitfall 3: TextArea Has No `.value` — Tests Break

**What goes wrong:** The existing `test_slash_palette.py:test_input_bar_open_palette_only_when_empty` and `test_full_flow_pilot.py:test_pilot_input_submit_triggers_widget` both reference `input_bar.value`. After the Input→TextArea swap, `.value` does not exist on the new widget (or its container). Tests that read `.value` must be updated to read `.text`.

**How to avoid:** Wave 0 includes explicit task to update all existing TUI tests that reference `.value` on `#input`.

[VERIFIED: `tests/harness/tui/test_slash_palette.py:121-122`, `test_full_flow_pilot.py:66-70`]

---

### Pitfall 4: TUI submit is NOT currently wired to `run_turn`

**What goes wrong:** The current `InputBar.Submitted` message is posted but there is no `on_input_bar_submitted` handler in `VossTUIApp`. The `cli.py` REPL loop uses `input("▌ ")` for the headless path AND for the TUI path (Textual's `app.run()` is never called from `_run_repl`). **T8 must wire the TUI submit to `run_turn`** — this is an implicit deliverable that is not stated in INPUT-01..05 but is required for the phase to be functional.

**Resolution path:** Add `on_input_bar_submitted(self, event: InputBar.Submitted)` to `VossTUIApp`, wire it to call `run_turn` via a worker thread (Textual workers pattern), and switch `_run_repl` to call `app.run()` when the renderer is a `TextualRenderer`.

**Warning signs:** The TUI renders but submitting a task does nothing (no turn appears, agent never fires).

[VERIFIED: `app.py` has no `on_input_bar_submitted`; `cli.py` `_run_repl` uses `input("▌ ")` loop; `app.run()` is never called from `_run_repl`]

---

### Pitfall 5: `## Notes` in VOSS.md is a Human Block, Not a Machine Fence

**What goes wrong:** Using `write_fence_body(path, fence_id="notes", body=...)` will create a machine fence `<!-- voss:begin id=notes -->` which is not what D-05 specifies. The `## Notes` heading is plain markdown prose (human block in VOSS.md's block model).

**How to avoid:** Implement a `append_voss_notes_bullet(path, text, timestamp)` function that: (1) reads the file, (2) calls `parse()`, (3) finds the human block containing `## Notes` or creates it, (4) appends the bullet `- [ISO] text\n`, (5) reconstructs via `_render(new_blocks)`, (6) atomic-writes. Never uses `write_fence_body`.

[VERIFIED: `voss_md.py` — `parse()` returns `kind="human"` blocks for plain markdown sections; `write_fence_body` is machine-fence-only]

---

### Pitfall 6: No Vision Capability API Exists — Name-Based Gate Required

**What goes wrong:** There is no `provider.supports_vision(model)` method in `providers.py` or `voss_runtime`. The `capability.py` file is TUI-activation-only (decides whether to use Textual at all, not whether models have vision).

**How to avoid:** Implement a thin `_model_supports_vision(model_name: str) -> bool` helper using a hardcoded allow-list of known vision-capable model name prefixes (e.g., `"claude-3"`, `"claude-opus"`, `"gpt-4o"`, `"gemini"`, `"gpt-4-vision"`). Gate INPUT-05 on this. Mark as `[ASSUMED]` until a provider capability API is added.

[VERIFIED: providers.py, capability.py, voss_runtime — no vision capability API found]

---

### Pitfall 7: EpisodicMemory is Per-Session In-Memory Only

**What goes wrong:** Attempting to read episodic history from disk (looking for a `.json` or database file) will fail — `EpisodicMemory` is purely in-memory during a session. The `session.py:save()` function serializes it for session resume, but the Ctrl-R corpus is the LIVE `ctx.history` object.

**How to avoid:** Pass the live `EpisodicMemory` instance to `InputBar` at construction time (or store it on `VossTUIApp` and access via `self.app`).

[VERIFIED: `session.py:save()` writes history separately; `EpisodicMemory.turns` is a `list[Turn]` only in memory during a session]

---

### Pitfall 8: Snapshot Tests Require `--snapshot-update` on First Run

**What goes wrong:** `pytest-textual-snapshot` with `snap_compare` will FAIL on the first run because no baseline snapshot files exist. This is expected behavior — tests go red until `--snapshot-update` is run to generate baseline SVGs.

**How to avoid:** Wave 0 task includes running `pytest tests/harness/tui/ --snapshot-update -k T8` to generate all baseline snapshots before any implementation. Baseline SVGs are committed to the repo.

[VERIFIED: pytest-textual-snapshot 1.1.0 — confirmed via WebFetch on official Textualize GitHub]

---

## Code Examples

### TextArea Key Inversion (verified pattern)
```python
# Source: Textual 8.2.6 TextArea._on_key (L1579-L1610)
# TextArea maps "enter" -> "\n" in its insert_values dict.
# Intercept before super() to route Enter to submit.

class InputBar(Widget):
    async def _on_key(self, event) -> None:
        key = event.key
        if key == "enter" and not self._search_mode:
            event.prevent_default()
            event.stop()
            await self.action_submit()
            return
        if key == "shift+enter":
            event.prevent_default()
            event.stop()
            ta = self.query_one(TextArea)
            ta.insert("\n")
            return
        if key == "slash":
            ta = self.query_one(TextArea)
            if not ta.text.strip():
                event.prevent_default()
                event.stop()
                self.action_open_palette()
                return
        if key == "ctrl+r":
            event.prevent_default()
            event.stop()
            self.action_reverse_search()
            return
        # All other keys propagate to child TextArea
```

### TextArea Autogrow (tcss only)
```tcss
/* Source: T8-UI-SPEC.md + verified Textual layout */
#input {
    dock: bottom;
    height: auto;
    min-height: 1;
    max-height: 5;
}
```

### Clipboard Image Probe
```python
# Source: Pillow 12.1.1 PIL/ImageGrab.py (full source inspected)
def _probe_clipboard_image(self):
    try:
        from PIL import ImageGrab, Image
        result = ImageGrab.grabclipboard()
        # isinstance check: Image vs list[str] (Win32 CF_HDROP) vs None
        if isinstance(result, Image.Image):
            return result
        return None
    except (ImportError, NotImplementedError, ChildProcessError, OSError):
        return None  # graceful no-op on Linux without wl-paste/xclip
```

### EpisodicMemory Ctrl-R Corpus
```python
# Source: voss_runtime/memory/episodic.py — Turn dataclass confirmed
from voss_runtime.memory.episodic import EpisodicMemory

def _ctrl_r_corpus(history: EpisodicMemory) -> list[str]:
    """Submitted task inputs, most-recent-first, consecutive dupes collapsed."""
    user_contents = [t.content for t in reversed(history.turns) if t.role == "user"]
    result, prev = [], None
    for item in user_contents:
        if item != prev:
            result.append(item)
            prev = item
    return result
```

### VOSS.md Notes Append (human section)
```python
# Source: voss_md.py parse() + _render() — human block structure confirmed
# D-05: append "- [ISO-8601 UTC] text" under "## Notes" human heading
# DO NOT use write_fence_body (machine fences only)

def append_voss_notes_bullet(path: Path, text: str, timestamp: str) -> None:
    """Append a dated bullet to the ## Notes human section of VOSS.md."""
    existing = path.read_text() if path.exists() else ""
    bullet = f"- [{timestamp}] {text}\n"
    if "## Notes" in existing:
        # Find the heading and append after it (before next ##)
        idx = existing.index("## Notes")
        # Find next section boundary or EOF
        rest_start = idx + len("## Notes")
        next_section = existing.find("\n##", rest_start)
        if next_section == -1:
            new_text = existing.rstrip("\n") + "\n" + bullet
        else:
            new_text = existing[:next_section] + bullet + existing[next_section:]
    else:
        new_text = existing.rstrip("\n") + "\n\n## Notes\n" + bullet
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(new_text)
    import os; os.replace(tmp, path)
```

---

## Runtime State Inventory

Not applicable. T8 is a greenfield widget rewrite — no renames or data migrations.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-line `Input` for prompt bar | `TextArea` for multi-line support | T8 | Unlock multi-line input; requires key inversion |
| No prefix dispatch in TUI | `!cmd` / `#note` prefix dispatch at submit time | T8 | Claude Code `!`/`#`-mode parity |
| No reverse-search in TUI | Ctrl-R inline readline-style search | T8 | bash/zsh/Claude Code history parity |
| No clipboard image support | `PIL.ImageGrab` + vision gate | T8 | Vision workflow from terminal |
| `Input.value` for content access | `TextArea.text` (property) | T8 | API surface change; existing tests must update |

**Deprecated/outdated:**
- `InputBar(Input)` inheritance: will be replaced by `InputBar(Widget)` containing a `TextArea` child.
- `input_bar.value` attribute: does not exist on TextArea; use `input_bar.textarea.text` or expose a `.text` property on the new `InputBar` wrapper.
- `input_bar.insert_text_at_cursor("/")` in `action_open_palette`: not a TextArea method; replace with `self.query_one(TextArea).insert("/")`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `textual` | All widgets | ✓ | 8.2.6 | — (hard dep) |
| `Pillow` / `PIL.ImageGrab` | INPUT-05 | ✓ | 12.1.1 | `None` return path in `_probe_clipboard_image` |
| `wl-paste` (Linux Wayland) | INPUT-05 clipboard on Linux | ✗ (macOS dev env) | — | `NotImplementedError` caught → graceful no-op |
| `xclip` (Linux X11) | INPUT-05 clipboard on Linux | ✗ (macOS dev env) | — | `NotImplementedError` caught → graceful no-op |
| `pytest-textual-snapshot` | Snapshot tests | ✗ (not in pyproject.toml dev deps yet) | 1.1.0 on PyPI | Must add to `[project.optional-dependencies.dev]` |
| `osascript` (macOS) | `PIL.ImageGrab` macOS path | ✓ (standard macOS) | — | `PIL.ImageGrab.grabclipboard()` returns `None` on failure |

**Missing dependencies with no fallback:**
- `pytest-textual-snapshot` — must be added to `pyproject.toml [dev]` before Wave 0 snapshot generation. Not optional.

**Missing dependencies with fallback:**
- `wl-paste` / `xclip` on Linux — graceful `None` return path already coded in the design.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23+ (already in dev deps) + pytest-textual-snapshot 1.1.0 (NEW) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `asyncio_mode = "auto"` already set |
| Quick run command | `pytest tests/harness/tui/ -q -x` |
| Full suite command | `pytest tests/harness/tui/ -q` |
| Snapshot update command | `pytest tests/harness/tui/ --snapshot-update -k T8` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File |
|--------|----------|-----------|-------------------|------|
| INPUT-01 | Single-line bar shows 1 row + prompt glyph | Snapshot (anchor 1) | `pytest tests/harness/tui/ --snapshot-update -k snap1` | Wave 0 |
| INPUT-01 | Multi-line bar shows 3 rows; glyph only on row 1 | Snapshot (anchor 2) | `pytest tests/harness/tui/ -k snap2` | Wave 0 |
| INPUT-01 | Bar capped at 5 rows | Snapshot (anchor 3) | `pytest tests/harness/tui/ -k snap3` | Wave 0 |
| INPUT-01 | Enter submits, Shift+Enter inserts newline | Unit (async pilot) | `pytest tests/harness/tui/test_input_bar_textarea.py -x` | Wave 1 |
| INPUT-01 | Slash palette guard preserved after TextArea swap | Snapshot (anchor 4) | `pytest tests/harness/tui/ -k snap4` | Wave 1 |
| INPUT-02 | `!cmd` local block renders with exit 0 | Snapshot (anchor 5) | `pytest tests/harness/tui/ -k snap5` | Wave 2 |
| INPUT-02 | `!cmd` local block renders with non-zero exit | Snapshot (anchor 6) | `pytest tests/harness/tui/ -k snap6` | Wave 2 |
| INPUT-02 | `shell.local` recorder event emitted | Unit (recorder assert) | `pytest tests/harness/tui/test_prefix_dispatch.py -k shell_local` | Wave 2 |
| INPUT-03 | `#note` confirmation line renders | Snapshot (anchor 7) | `pytest tests/harness/tui/ -k snap7` | Wave 2 |
| INPUT-03 | `memory.note` recorder event emitted | Unit (recorder assert) | `pytest tests/harness/tui/test_prefix_dispatch.py -k memory_note` | Wave 2 |
| INPUT-04 | Ctrl-R search mode shows correct prompt | Snapshot (anchor 8) | `pytest tests/harness/tui/ -k snap8` | Wave 3 |
| INPUT-04 | Ctrl-R no-match shows dim `(no match)` | Snapshot (anchor 9) | `pytest tests/harness/tui/ -k snap9` | Wave 3 |
| INPUT-04 | Corpus: only user-submitted task turns; dupes collapsed | Unit | `pytest tests/harness/tui/test_reverse_search.py -x` | Wave 3 |
| INPUT-05 | Image attached indicator shows in bar | Snapshot (anchor 10) | `pytest tests/harness/tui/ -k snap10` | Wave 4 |
| INPUT-05 | No-vision notice block renders | Snapshot (anchor 11) | `pytest tests/harness/tui/ -k snap11` | Wave 4 |
| INPUT-05 | No-vision notice auto-removes after 3s | Unit (async timing mock) | `pytest tests/harness/tui/test_paste_image.py -k notice_remove` | Wave 4 |

### Sampling Rate
- **Per task commit:** `pytest tests/harness/tui/ -q -x`
- **Per wave merge:** `pytest tests/harness/ -q` (full harness suite)
- **Phase gate:** Full suite green (`pytest tests/ -q --ignore=tests/e2e`) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/harness/tui/test_input_bar_textarea.py` — INPUT-01 unit tests
- [ ] `tests/harness/tui/test_prefix_dispatch.py` — INPUT-02/03 recorder assertions (R1, R2)
- [ ] `tests/harness/tui/test_reverse_search.py` — INPUT-04 corpus + mode tests
- [ ] `tests/harness/tui/test_paste_image.py` — INPUT-05 clipboard probe + vision gate
- [ ] Add `pytest-textual-snapshot>=1.1.0` to `[project.optional-dependencies.dev]` in `pyproject.toml`
- [ ] Run `pytest tests/harness/tui/ --snapshot-update` to generate baseline SVGs (11 anchors)
- [ ] Update `tests/harness/tui/test_slash_palette.py:test_input_bar_open_palette_only_when_empty` — must update `.value` → `.text` reference after TextArea swap
- [ ] Update `tests/harness/tui/test_full_flow_pilot.py:test_pilot_input_submit_triggers_widget` — same `.value` reference

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | yes (INPUT-02) | `sandbox.shell_allowed()` + T5-D12 deny-set; `PermissionGate.mode_allows()` |
| V5 Input Validation | yes (INPUT-02/03) | `.strip()` prefix check; empty-prefix no-op guards |
| V6 Cryptography | no | — |

### Known Threat Patterns for T8 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Shell injection via `!cmd` | Tampering | `sandbox.shell_allowed()` rejects metacharacters (`|`, `>`, `;`, `&&`, `$(`, backtick, etc.); binary allowlist |
| `!cmd` bypassing permission mode | Elevation of privilege | `PermissionGate.mode_allows("edit", "shell_run", ...)` returns `(False, "denied by mode edit")` — plan mode refuses, edit mode denies shell |
| Malicious clipboard image (visual deception) | Spoofing | Image is attached as vision input only — no code execution from image content |
| VOSS.md injection via `#note` | Tampering | Content appended as plain text bullet; no code execution; `voss_md.parse()` isolates human blocks from machine fences |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `InputBar` should become a `Widget` container holding a child `TextArea` (not subclass TextArea directly) for the prompt-glyph positioning | Pattern 4 — Prompt Glyph Render | If TextArea is subclassed directly, the prompt glyph may need a different render approach (e.g., custom `render_line` override), adding complexity |
| A2 | `TurnView.append_turn(role, body)` with new role strings like `"local-shell"` is the correct approach for LocalBlock rendering (vs. a separate widget class) | Pattern 10 — LocalBlock | If a separate `LocalBlock` widget class is required (as implied by UI-SPEC component inventory), the planner must wire mount/unmount lifecycle for it |
| A3 | `RecorderBridge.emit(event_name, payload)` calling `app.on_local_event(event_name, payload)` is the right extension point | Pattern 9 — RecorderBridge | If the recorder contract requires events to go through `RunRecorder` directly (not via app methods), a different emit path is needed |
| A4 | The TUI submit-to-run_turn wiring (`on_input_bar_submitted` in app + worker thread) is a T8 deliverable | Pitfall 4 | If this was intentionally deferred (app renders but is not interactive), T8 scope must be adjusted |
| A5 | `_model_supports_vision(model_name: str) -> bool` is a name-based check (no provider API exists) | Pattern — Vision Gate | If a provider capability API is added before T8 execution, use that instead |
| A6 | `EpisodicMemory` instance is passed to `InputBar` or stored on `VossTUIApp` at construction time | Pattern 6 — Ctrl-R Corpus | If the history object is only in `cli.py`'s `_run_repl` locals, InputBar cannot access it without an explicit plumbing step |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.
(Table is not empty — A1-A6 need planner attention.)

---

## Open Questions

1. **TUI submit wiring scope (Pitfall 4)**
   - What we know: `InputBar.Submitted` is posted but there is no `on_input_bar_submitted` handler in `VossTUIApp`; `cli.py` uses `input("▌ ")` for the headless REPL; `app.run()` is never called from `_run_repl`.
   - What's unclear: Was this intentional (deferred to T8) or an oversight?
   - Recommendation: **Include in T8 scope.** Without it, the TUI is visually complete but non-interactive. The planner should add `on_input_bar_submitted` to `VossTUIApp` and a worker-thread `run_turn` call, and update `_run_repl` to dispatch `app.run()` for `TextualRenderer`.

2. **LocalBlock as separate widget vs. TurnView role string (A2)**
   - What we know: UI-SPEC component inventory defines `LocalBlock`, `LocalBlockShell`, `LocalBlockNote`, `LocalBlockNotice` as distinct components.
   - What's unclear: Whether these are standalone `Widget` instances mounted in the scroll container, or styling conventions applied inside `TurnView`.
   - Recommendation: Use `TurnView.append_turn` with new role strings for simplicity. The `LocalBlockNotice` (3s auto-remove) needs a handle to call `.remove()` — this is easier if it's mounted as a child widget, so `LocalBlockNotice` should be a separate widget. `LocalBlockShell` and `LocalBlockNote` can be inline `TurnView` entries.

3. **Episodic history access from InputBar (A6)**
   - What we know: `ctx.history` is a local `EpisodicMemory` in `_run_repl`; not stored on `VossTUIApp` currently.
   - What's unclear: Whether T8's TUI submit wiring will store history on `VossTUIApp` as a side effect.
   - Recommendation: Store `history: EpisodicMemory` on `VossTUIApp.__init__` and pass it in `_run_repl` when constructing the app. InputBar accesses via `self.app.history`.

---

## Sources

### Primary (HIGH confidence)
- Textual 8.2.6 installed source — `TextArea._on_key`, `TextArea.text`, `TextArea.load_text`, `TextArea.insert`, `TextArea.BINDINGS`, `App.clipboard`, `events.Paste` — all directly inspected via `python3 -c "import inspect; ..."` [VERIFIED]
- `voss/harness/tui/widgets/input_bar.py` — current `InputBar(Input)` implementation, `Submitted` message, `action_submit`, `action_open_palette`, `_on_key` guard [VERIFIED]
- `voss/harness/tui/keymap.py` — KEYMAP tuple, existing bindings, no `ctrl+r` [VERIFIED]
- `voss/harness/tui/styles.tcss` — current `#input` tcss block [VERIFIED]
- `voss/harness/tui/recorder_bridge.py` — `RecorderBridge` API; no `.emit()` method currently [VERIFIED]
- `voss/harness/tui/app.py` — `VossTUIApp`; no `on_input_bar_submitted` handler; `app.run()` never called from REPL [VERIFIED]
- `voss/harness/sandbox.py` — `shell_allowed()`, `DENY_TOKENS`, `SHELL_METACHARS`, binary `DEFAULT_SHELL_ALLOWLIST` [VERIFIED]
- `voss/harness/voss_md.py` — `parse()`, `write_fence_body()`, `Block(kind="human"|"machine")`, `_render()` [VERIFIED]
- `voss_runtime/memory/episodic.py` — `EpisodicMemory`, `Turn.role`, `Turn.content`, `.turns: list[Turn]`, `.add(content, role=)` [VERIFIED]
- `pyproject.toml` — Textual `>=0.58,<1.0`, no `pytest-textual-snapshot`, no `Pillow` in prod deps; `asyncio_mode = "auto"` [VERIFIED]
- `PIL.ImageGrab.grabclipboard()` — full source inspected for macOS/Windows/Linux branches, exception types, None return semantics [VERIFIED]

### Secondary (MEDIUM confidence)
- pytest-textual-snapshot 1.1.0 — `snap_compare` fixture API, `--snapshot-update` flag, Textualize org ownership [VERIFIED: WebFetch on github.com/Textualize/pytest-textual-snapshot]
- PyPI version confirm for `pytest-textual-snapshot` (1.1.0) and `Pillow` (12.2.0) via `python3 -m pip index versions` [VERIFIED: PyPI registry]

### Tertiary (LOW confidence)
- A1: Widget container vs. TextArea subclass approach for prompt-glyph rendering [ASSUMED]
- A4: TUI submit wiring is a T8 deliverable (inferred from architecture, not explicit in CONTEXT.md) [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Textual 8.2.6 source directly inspected; Pillow installed + source confirmed; pytest-textual-snapshot on PyPI and Textualize-owned
- Architecture: HIGH for existing code seams; MEDIUM for new wiring (A1, A2, A4 assumptions)
- Pitfalls: HIGH — all verified against actual source code (not training data)

**Research date:** 2026-05-17
**Valid until:** 2026-06-17 (Textual 8.x is stable; 30 days for fast-moving harness codebase)
