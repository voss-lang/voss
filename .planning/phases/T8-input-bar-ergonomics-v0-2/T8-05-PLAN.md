---
phase: T8-input-bar-ergonomics-v0-2
plan: 05
type: execute
wave: 3
depends_on: ["T8-03", "T8-04"]
files_modified:
  - voss/harness/tui/widgets/input_bar.py
  - voss/harness/tui/widgets/local_block.py
  - voss/harness/tui/widgets/__init__.py
  - pyproject.toml
  - tests/harness/tui/test_reverse_search.py
  - tests/harness/tui/test_paste_image.py
  - tests/harness/tui/snapshots
autonomous: true
requirements: [INPUT-04, INPUT-05]
user_setup: []

must_haves:
  truths:
    - "Ctrl-R toggles an inline (NOT modal) reverse-i-search render mode on InputBar: prompt `▌ (reverse-i-search)\\`query': match`, TextArea read-only, pre-search content saved/restored on Esc"
    - "Ctrl-R corpus = submitted task inputs only from the current project's live EpisodicMemory (self.app.history), most-recent-first, consecutive duplicates collapsed; excludes !cmd/#note//-palette lines"
    - "Typing filters incrementally (case-insensitive substring); repeated Ctrl-R steps to the next older match; Enter loads the match into the bar EDITABLE (NOT auto-submit); Esc cancels restoring prior content; no-match shows dim `(no match)`"
    - "Paste keypress probes the OS clipboard for an image before text paste; PIL.ImageGrab.grabclipboard() wrapped so ImportError/NotImplementedError/ChildProcessError/OSError → graceful no-op (falls back to text paste, no error block)"
    - "Image + vision-capable model (name-based _model_supports_vision gate) → image held as pending attachment, dim `[image attached · 1 image]` indicator, cleared on submit; image + no-vision → image dropped, any text preserved, transient LocalBlockNotice (signal-warn, auto-removes 3000ms or next submit)"
    - "Pillow is added to pyproject [dev] (test/probe dep); Linux-without-wl-paste/xclip degrades to text paste via the NotImplementedError catch"
  artifacts:
    - path: "voss/harness/tui/widgets/input_bar.py"
      provides: "reverse_search mode + _build_corpus + _probe_clipboard_image + _model_supports_vision + action_paste override"
      contains: "def action_reverse_search"
      min_lines: 120
    - path: "voss/harness/tui/widgets/local_block.py"
      provides: "LocalBlockNotice with 3000ms set_timer auto-remove + .dismiss()"
      contains: "class LocalBlockNotice"
  key_links:
    - from: "voss/harness/tui/widgets/input_bar.py"
      to: "self.app.history (EpisodicMemory)"
      via: "_build_corpus reads reversed user-role turns, dedups consecutive"
      pattern: "_build_corpus"
    - from: "voss/harness/tui/widgets/input_bar.py"
      to: "PIL.ImageGrab.grabclipboard"
      via: "_probe_clipboard_image guarded probe in action_paste override"
      pattern: "ImageGrab"
    - from: "voss/harness/tui/widgets/input_bar.py"
      to: "LocalBlockNotice"
      via: "no-vision paste mounts a transient notice via app.on_local_event('notice', ...)"
      pattern: "LocalBlockNotice|on_local_event\\(\"notice\""
---

<objective>
Implement Ctrl-R inline reverse-i-search over the per-project episodic corpus (INPUT-04, D-06/D-07) and paste-image detection with the vision-capability gate (INPUT-05, D-08/D-09). Ctrl-R is a render-mode of InputBar (not a modal); the corpus is the live `self.app.history` (wired by Plan 04). Paste probes the OS clipboard via Pillow with full graceful-degradation; no-vision shows a transient auto-removing notice.

Purpose: INPUT-04 bash/zsh/Claude-Code history parity; INPUT-05 vision-from-terminal with no silent data loss.
Output: reverse-search + paste-image logic in input_bar.py, LocalBlockNotice timer widget, Pillow dev dep, green INPUT-04/05 tests + snapshots 8-11.
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
@.planning/phases/T8-input-bar-ergonomics-v0-2/T8-03-SUMMARY.md
@.planning/phases/T8-input-bar-ergonomics-v0-2/T8-04-SUMMARY.md

<interfaces>
voss_runtime/memory/episodic.py (VERIFIED): `EpisodicMemory.turns: list[Turn]`; `Turn.role` ("user"|"assistant"|"system"), `Turn.content`. Submitted task prompts are role="user". Plan 04 stores the live instance on `VossTUIApp.history` (read via `self.app.history`).

Ctrl-R corpus algorithm (VERIFIED — RESEARCH §Code Examples): `[t.content for t in reversed(history.turns) if t.role=="user"]` then collapse consecutive duplicates (keep first of each run). Excludes !cmd/#note//-palette because those never call run_turn → never `.add(role="user")`.

Textual 8.2.6 (VERIFIED): `events.Paste` carries ONLY `text: str` (no binary) — image probe MUST be in an `action_paste()` override, NOT `on_paste`. `app.clipboard` is Textual-internal (NOT OS clipboard) — only `PIL.ImageGrab.grabclipboard()` reads OS clipboard. TextArea `read_only` attribute toggles editability for search mode; `load_text`/`text` from Plan 02.

PIL.ImageGrab (VERIFIED — Pillow 12.1.1): `ImageGrab.grabclipboard()` → `Image.Image` if image, `list[str]` (Win32 CF_HDROP) if files, `None` if none; raises `NotImplementedError` on Linux w/o wl-paste/xclip, `ChildProcessError`/`OSError` on subprocess failure. Guard: `if isinstance(result, Image.Image): return result; return None` inside `except (ImportError, NotImplementedError, ChildProcessError, OSError): return None`.

_model_supports_vision (VERIFIED — Pitfall 6: NO provider capability API exists): name-based allow-list of prefixes — `claude-3`, `claude-opus`, `gpt-4o`, `gpt-4-vision`, `gemini` → True; `claude-instant`, `gpt-3.5` → False. Mark `[ASSUMED]` in code comment; gate on the active model name (`self.app.model`).

LocalBlockNotice (Plan 03 defined the class stub / Plan 05 completes timer): UI-SPEC — transient `.local-block--notice` signal-warn; `set_timer(3.0, self.remove)` in `on_mount`; `.dismiss()` cancels timer + removes; auto-remove at 3000ms OR next submit (whichever first). Mounted via `app.on_local_event("notice", payload)` (Plan 04 handler).

input_bar.py after Plan 03 (analog): `InputBar(Widget)` + child TextArea, `_on_key` already intercepts enter/shift+enter/slash/ctrl+r (ctrl+r branch currently calls `self.action_reverse_search()` stub-or-absent — Plan 02 reserved `_search_mode` flag default False); `action_submit` with `!`/`#` dispatch. keymap.py `ctrl+r→reverse_search` binding already added by Plan 02.

T8-UI-SPEC locked copy: prompt prefix `(reverse-i-search)\`` ; separator `':` ; no-match suffix `(no match)` (dim); `[image attached · 1 image]` (dim); no-vision notice `current model has no vision — image not attached` (signal-warn); NO_COLOR variants `[no vision] ...`. Snapshot anchors 8 (search mode), 9 (no match), 10 (image attached), 11 (no-vision notice).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Pillow dev dep + clipboard probe + vision gate (pure-logic core)</name>
  <behavior>
    - _probe_clipboard_image() returns the Image when grabclipboard() yields an Image.Image; returns None for list[str], None, or any of ImportError/NotImplementedError/ChildProcessError/OSError (graceful no-op)
    - _model_supports_vision("claude-3-5-sonnet") / "gpt-4o" / "gemini-1.5-pro" → True; "claude-instant-1" / "gpt-3.5-turbo" → False
    - _build_corpus(history): reversed user-role contents, consecutive duplicates collapsed, most-recent-first; ignores assistant/system turns; empty history → []
  </behavior>
  <read_first>
    - pyproject.toml lines 36-46 (`dev = [...]` — add Pillow alongside the Plan-01 pytest-textual-snapshot entry; NOT prod deps)
    - T8-RESEARCH.md Pattern 6 (`_build_corpus` verified algorithm), Pattern 7 (PIL.ImageGrab probe + exact exception set), Pitfall 6 (name-based vision gate — no provider API), Pitfall 7 (live in-memory EpisodicMemory only), §"Package Legitimacy Audit" (Pillow APPROVED — 13yr, python-pillow org), §"Code Examples" (clipboard probe + corpus snippets)
    - T8-PATTERNS.md §"test_paste_image.py" (monkeypatch grabclipboard; NotImplementedError fallback; _model_supports_vision truth table), §"test_reverse_search.py" (`_build_corpus` as standalone pure function — unit-test without a Textual app, `_seeded_history` via Plan-01 fixture)
  </read_first>
  <action>Add `"Pillow>=10.0"` to the `dev = [...]` list in `pyproject.toml` (test/probe dependency only — NOT prod `dependencies`, NOT `search`; Pillow is APPROVED in the Legitimacy Audit so no human checkpoint), then `python -m pip install -e '.[dev]'`. In `input_bar.py` add three pure/near-pure helpers: `_build_corpus(history) -> list[str]` (the verified reversed-user-turns + consecutive-dedup algorithm; tolerate `history is None` → `[]`); `_probe_clipboard_image() -> Image | None` (import PIL lazily inside the function, `grabclipboard()`, `isinstance(result, Image.Image)` else None, wrapped in `except (ImportError, NotImplementedError, ChildProcessError, OSError): return None` — the graceful no-op); `_model_supports_vision(model_name: str) -> bool` (name-prefix allow-list, `[ASSUMED]` comment citing Pitfall 6, defensive `(model_name or "").lower()`). Keep these importable for pure unit tests (module-level functions or static methods — no Textual app needed). Fill the pure-logic portions of `test_reverse_search.py` (corpus dedup/role-filter/recency/empty via Plan-01 `seeded_history`) and `test_paste_image.py` (`_probe_clipboard_image` monkeypatched to Image / list / None / each raising exception; `_model_supports_vision` truth table). Remove the corresponding xfail markers.</action>
  <verify>
    <automated>pytest tests/harness/tui/test_reverse_search.py tests/harness/tui/test_paste_image.py -q -x -k "corpus or probe or vision or build"</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from PIL import ImageGrab, Image; print('ok')"` exits 0; `grep -v '^#' pyproject.toml | grep -c 'Pillow'` ≥ 1; Pillow absent from prod deps (`python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); assert 'Pillow' not in ' '.join(d['project']['dependencies'])"` exits 0)
    - `pytest tests/harness/tui/test_reverse_search.py -q -k corpus` PASS: dedup collapses only CONSECUTIVE dupes, assistant/system turns excluded, most-recent-first, empty → []
    - `pytest tests/harness/tui/test_paste_image.py -q -k "probe or vision"` PASS: NotImplementedError/ChildProcessError/OSError/ImportError all → None; list[str] → None; Image → the image; vision truth table holds
    - the four exception types are caught as a tuple in `_probe_clipboard_image` — `grep -A8 'def _probe_clipboard_image' voss/harness/tui/widgets/input_bar.py | grep -c 'NotImplementedError'` returns ≥ 1
  </acceptance_criteria>
  <done>Pillow dev-only; corpus/probe/vision helpers pure-testable and green; clipboard probe degrades gracefully on every documented failure mode.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Ctrl-R inline reverse-i-search render mode</name>
  <behavior>
    - ctrl+r enters search mode: `_search_mode=True`, pre-search bar text saved, TextArea read_only, bar shows `▌ (reverse-i-search)\`': ` (empty query, no match yet)
    - typing printable chars appends to the query and re-filters _build_corpus(self.app.history) by case-insensitive substring; display shows first (most-recent) match
    - repeated ctrl+r advances to the next older match; wrapping/end behavior shows `(no match)` dim when exhausted or no corpus
    - Enter in search mode loads the matched text into the bar as editable content (NOT auto-submit, NOT Submitted posted), exits search mode (`_search_mode=False`, read_only cleared)
    - Esc in search mode restores the saved pre-search content (or empty) and exits search mode; no Submitted, no toast
    - ctrl+r with empty corpus immediately shows `(no match)`
  </behavior>
  <read_first>
    - voss/harness/tui/widgets/input_bar.py (post-Plan-03 file — `_on_key` already routes `ctrl+r`; `_search_mode` flag reserved by Plan 02 so `enter` is NOT intercepted-as-submit while searching)
    - T8-RESEARCH.md §"Architecture > Ctrl+R" branch (read_only=True, query filter, Enter loads, Esc restores), Pattern 6 (corpus), Pitfall 1/2 (TextArea ctrl bindings — search mode is read-only so edit bindings inert), Anti-Pattern "Reading episodic store from session.py"
    - T8-PATTERNS.md §"test_reverse_search.py" (async pilot pattern: `VossTUIApp(history=seeded)`, press ctrl+r, type, assert display string)
    - T8-UI-SPEC.md §"Inline reverse-i-search prompt layout", §"INPUT-04 — Ctrl-R reverse-i-search interaction contract", §"Copywriting Contract" (exact `(reverse-i-search)\`` / `':` / `(no match)` strings), §"Snapshot-Test Anchors" 8/9, Acceptance Check 16 (stays inline — no modal) / 18 (no ctrl+f shadow)
  </read_first>
  <action>In `input_bar.py` implement `action_reverse_search()` and the search-mode key handling. State: `_search_mode: bool` (default False from Plan 02), `_search_query: str`, `_search_saved_text: str`, `_search_matches: list[str]`, `_search_idx: int`. `action_reverse_search`: if not in search mode, save `self.text` to `_search_saved_text`, set `_search_mode=True`, child TextArea `read_only=True`, build `_search_matches=_build_corpus(getattr(self.app,"history",None))` filtered by the (empty) query, render the reverse-i-search prompt string (exact UI-SPEC copy, `.dim` label / `.accent` query / matched body) into the bar's display area; if already in search mode, advance `_search_idx` to the next older match (clamp; show `(no match)` dim when no matches). Extend `_on_key`: while `_search_mode`, printable keys append to `_search_query` and re-filter+re-render (case-insensitive substring over the corpus, most-recent-first); `enter` → load `_search_matches[_search_idx]` (if any) into the bar via TextArea `load_text(...)`, exit search mode (clear `_search_mode`, `read_only=False`), do NOT post Submitted; `escape` → `load_text(_search_saved_text)`, exit search mode, no Submitted; `ctrl+r` → advance (handled by `action_reverse_search`). Ensure the existing `enter`-submit intercept (Plan 02) is gated by `not self._search_mode` so search-mode Enter does the load, not a submit. Fill `test_reverse_search.py` async-pilot tests + snapshot anchors 8 (search mode with match) and 9 (no match), `pytest tests/harness/tui/ --snapshot-update -k "snap8 or snap9"`, commit baselines, remove xfail markers.</action>
  <verify>
    <automated>pytest tests/harness/tui/test_reverse_search.py -q -x</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/tui/test_reverse_search.py -q` exits 0: ctrl+r enters mode, typing filters, repeated ctrl+r steps older, Enter loads editable (assert NO `InputBar.Submitted` posted and bar text == matched entry, `_search_mode` False after), Esc restores saved text, empty corpus → `(no match)`
    - snapshot anchors 8 + 9 green with committed baselines
    - inline-only assertion: test confirms NO modal/screen pushed by ctrl+r (`len(pilot.app.screen_stack)` unchanged) — UI-SPEC Acceptance Check 16
    - `pytest tests/harness/tui/test_keymap_baseline.py -q` exits 0 — ctrl+f (main context) unaffected (Acceptance Check 18)
    - search-mode Enter does NOT trigger run_turn: test asserts the Plan-04 `_turn_dispatch` is not called on Enter while `_search_mode`
  </acceptance_criteria>
  <done>Ctrl-R inline reverse-i-search over per-project corpus: incremental filter, step-older, Enter-loads-editable (no submit), Esc-restores, no-match, no modal; snapshots 8-9 green; ctrl+f intact.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Paste-image attach / no-vision transient notice</name>
  <behavior>
    - action_paste override: probe clipboard image first; no image → super().action_paste() (normal text paste, no block)
    - image + _model_supports_vision(self.app.model) True → store image as self._pending_image, render dim `[image attached · 1 image]` indicator in the bar, skip text insertion of image; indicator cleared on submit (pending image consumed/cleared)
    - image + no vision → drop image (no attachment), preserve any clipboard text (fall through to text paste), mount a transient LocalBlockNotice via app.on_local_event("notice", {...}) with `current model has no vision — image not attached` (signal-warn)
    - LocalBlockNotice auto-removes after 3000ms (set_timer) OR on next submit (whichever first); .dismiss() cancels timer + removes
    - clipboard-image unsupported (probe → None via NotImplementedError) → plain text paste, NO notice, NO error
  </behavior>
  <read_first>
    - voss/harness/tui/widgets/local_block.py (Plan-03 file — complete `LocalBlockNotice` with the timer; LocalBlock base + Text/no-markup render)
    - voss/harness/tui/widgets/input_bar.py (post-Task-2 file — add `action_paste` override + `_pending_image`; clear pending on submit in `action_submit`)
    - T8-RESEARCH.md Pattern 8 (action_paste override NOT on_paste; events.Paste is text-only), Pattern 7 (probe), Pitfall 6 (vision gate), Pattern 10 / A2 (LocalBlockNotice separate widget for `.remove()` handle)
    - T8-PATTERNS.md §"local_block.py" (`set_timer(3.0, self.remove)` in on_mount; `.dismiss()` cancels+removes), §"test_paste_image.py" (monkeypatch grabclipboard; timer mock; notice mount assertion)
    - T8-UI-SPEC.md §"INPUT-05 — Paste-image interaction contract", §"Image attachment affordance", §"Copywriting Contract" (locked `[image attached · 1 image]` / no-vision strings + NO_COLOR variants), §"Snapshot-Test Anchors" 10/11, Acceptance Check 14 (notice not in model history) / 17 (notice transient)
  </read_first>
  <action>Complete `LocalBlockNotice(message)` in `local_block.py`: `.local-block--notice` signal-warn render via plain `Text`; `on_mount` calls `self.set_timer(3.0, self.remove)`; `.dismiss()` cancels the stored timer handle then `self.remove()`. Export it from `widgets/__init__.py`. In `input_bar.py` override `action_paste()`: call `_probe_clipboard_image()`; if None → `await super().action_paste()` (normal text paste; no block — covers the unsupported-platform graceful path) and return; if Image and `_model_supports_vision(getattr(self.app,"model",""))` → set `self._pending_image = image`, render the dim `[image attached · 1 image]` inline indicator (cleared in `action_submit` when the bar is submitted/cleared — also drop `_pending_image` there), do NOT insert image bytes as text; if Image and no vision → set `_pending_image=None`, mount a transient notice via `self.app.on_local_event("notice", {"message": "current model has no vision — image not attached"})` (Plan-04 handler mounts the `LocalBlockNotice`; honor NO_COLOR `[no vision] ` prefix per UI-SPEC), then fall through to `await super().action_paste()` so any clipboard text is still pasted (no silent loss of text). In `action_submit`, before/after dispatch, clear `_pending_image` and the indicator (next-submit also dismisses an outstanding notice per UI-SPEC "whichever first"). Fill `test_paste_image.py` remaining tests (attach indicator anchor 10, no-vision notice anchor 11, notice auto-remove via timer mock, unsupported→text-paste-no-block) + `pytest tests/harness/tui/ --snapshot-update -k "snap10 or snap11"`, commit baselines, remove xfail markers.</action>
  <verify>
    <automated>pytest tests/harness/tui/test_paste_image.py -q -x</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/tui/test_paste_image.py -q` exits 0: vision model → `_pending_image` set + indicator shown + cleared on submit; no-vision → `_pending_image` None + text preserved + LocalBlockNotice mounted; unsupported (probe None) → text paste, zero notice/block; notice auto-removes (timer-mock fires `.remove()`); `.dismiss()` cancels timer
    - snapshot anchors 10 + 11 green with committed baselines
    - notice never enters model history: test asserts the notice message is absent from any messages/EpisodicMemory list reaching run_turn (UI-SPEC Acceptance Check 14)
    - `python -c "from voss.harness.tui.widgets import LocalBlockNotice; assert hasattr(LocalBlockNotice,'dismiss')"` exits 0
    - full T8 suite: `pytest tests/harness/tui/ -q` exits 0 (all 11 snapshot anchors + R1/R2 + INPUT-01..05 green; no Wave 0-2 regression)
  </acceptance_criteria>
  <done>Paste-image: vision→attach indicator (cleared on submit), no-vision→drop image+keep text+transient auto-removing signal-warn notice, unsupported→silent text-paste fallback; notice never in model history; snapshots 10-11 + full T8 suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| OS clipboard → InputBar | untrusted clipboard image/text crosses into the widget |
| episodic corpus → bar display | prior user inputs re-surfaced via Ctrl-R |
| pending image → run_turn vision input | attached image crosses into the model |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T8-13 | Tampering / DoS | `PIL.ImageGrab.grabclipboard()` reading OS clipboard (INPUT-05) | mitigate | all four documented exceptions (`ImportError`/`NotImplementedError`/`ChildProcessError`/`OSError`) caught → graceful no-op; no shell-out beyond Pillow's own (osascript/wl-paste/xclip are Pillow-internal); image held as opaque object, only forwarded as a vision input (no code execution from image bytes); test asserts every failure mode degrades to text paste |
| T-T8-14 | Information disclosure | cross-project / non-task history leak via Ctrl-R (INPUT-04, D-07) | mitigate | corpus = `self.app.history` (the CURRENT project's live EpisodicMemory only — Plan 04 wires the per-project instance, Pitfall 7 no disk read); only `role=="user"` submitted-task turns; `!cmd`/`#note`/`/`-palette never call run_turn so never enter the corpus — test asserts they are excluded |
| T-T8-15 | Spoofing | malicious clipboard image as visual deception | accept | image is attached as a vision input only — no execution; user explicitly pastes; same trust as any model image input |
| T-T8-16 | Information disclosure | no-vision notice leaking into model conversation | mitigate | notice mounted via `on_local_event` into the scroll container only; test asserts the notice message never appears in the messages/EpisodicMemory list reaching run_turn (Acceptance Check 14); transient (3000ms / next-submit) |
| T-T8-SC | Tampering | npm/pip installs (Pillow) | mitigate | Pillow APPROVED in RESEARCH Package Legitimacy Audit (13yr, python-pillow org, 50M+/wk, PyPI-verified) — not `[ASSUMED]`/`[SUS]`, no blocking-human checkpoint required; dev-only, never in prod `dependencies`; slopcheck crates.io false-positive documented in RESEARCH |
</threat_model>

<verification>
- `pytest tests/harness/tui/ -q` exits 0 (full T8 suite: 11 snapshot anchors + R1/R2 + INPUT-01..05)
- `pytest tests/ -q --ignore=tests/e2e` exits 0 (phase gate — no broader regression)
- Ctrl-R corpus excludes !cmd/#note//-palette and is current-project-only (D-07 asserted)
- Clipboard probe degrades to text paste on every documented failure mode
</verification>

<success_criteria>
- Ctrl-R inline reverse-i-search over per-project corpus: incremental filter, step-older, Enter-loads-editable (no submit), Esc-restores, no-match, no modal, ctrl+f intact
- Paste-image: vision→indicator (cleared on submit), no-vision→drop+keep-text+transient signal-warn notice, unsupported→silent text fallback; notice never in model history
- Pillow dev-only; clipboard probe graceful on all documented errors
- Snapshots 8-11 green; full T8 suite + phase gate green
</success_criteria>

<output>
Create `.planning/phases/T8-input-bar-ergonomics-v0-2/T8-05-SUMMARY.md` when done
</output>
