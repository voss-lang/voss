---
phase: T8-input-bar-ergonomics-v0-2
plan: 03
type: execute
wave: 2
depends_on: ["T8-02"]
files_modified:
  - voss/harness/tui/widgets/input_bar.py
  - voss/harness/tui/widgets/local_block.py
  - voss/harness/tui/widgets/__init__.py
  - voss/harness/tui/recorder_bridge.py
  - voss/harness/tui/styles.tcss
  - voss/harness/voss_md.py
  - tests/harness/tui/test_prefix_dispatch.py
  - tests/harness/tui/snapshots
autonomous: true
requirements: [INPUT-02, INPUT-03]
user_setup: []

must_haves:
  truths:
    - "Bare `!cmd` at submit runs through sandbox.shell_allowed + split_command + create_subprocess_exec (the existing T5-D12 gate) — never raw subprocess, never a parallel allowlist"
    - "`!cmd` bypasses run_turn entirely, renders an ephemeral local-shell block (cmd + stdout/stderr + exit code), and is NEVER added to model conversation history"
    - "`!cmd` emits recorder_bridge.emit('shell.local', payload) with cmd, exit_code, stdout, stderr"
    - "Bare `#text` appends `- [ISO-8601 UTC] text` under a `## Notes` HUMAN section of VOSS.md via a new voss_md helper (NOT write_fence_body), bypasses run_turn, renders `# note saved`, emits recorder_bridge.emit('memory.note', payload) with text + timestamp"
    - "Empty `!` or `#` (no body) is a silent no-op: input cleared, no block, no recorder event, no run_turn"
    - "A `!cmd` rejected by shell_allowed (deny token / metachar / non-allowlisted binary) surfaces the rejection reason in the local block and does NOT execute"
  artifacts:
    - path: "voss/harness/tui/widgets/local_block.py"
      provides: "LocalBlockShell + LocalBlockNote render (Text, no markup)"
      contains: "class LocalBlock"
      min_lines: 30
    - path: "voss/harness/voss_md.py"
      provides: "append_voss_notes_bullet human-section append helper"
      contains: "def append_voss_notes_bullet"
    - path: "voss/harness/tui/recorder_bridge.py"
      provides: ".emit(event_name, payload) delegating to app.on_local_event"
      contains: "def emit"
  key_links:
    - from: "voss/harness/tui/widgets/input_bar.py"
      to: "voss.harness.sandbox.shell_allowed"
      via: "_dispatch_shell calls shell_allowed then split_command before create_subprocess_exec"
      pattern: "shell_allowed\\("
    - from: "voss/harness/tui/widgets/input_bar.py"
      to: "voss.harness.voss_md.append_voss_notes_bullet"
      via: "_dispatch_note calls the human-section append helper"
      pattern: "append_voss_notes_bullet"
    - from: "voss/harness/tui/widgets/input_bar.py"
      to: "recorder_bridge.emit"
      via: "shell.local / memory.note emitted on dispatch completion"
      pattern: "emit\\(\"(shell\\.local|memory\\.note)\""
---

<objective>
Implement submit-time `!`/`#` prefix dispatch (INPUT-02/03, D-03/D-04/D-05): `!cmd` executes through the EXISTING gated shell-exec path (T5-D12 deny-set, permission-mode behavior — no parallel allowlist, no second security surface), `#text` appends a dated bullet to the `## Notes` HUMAN section of VOSS.md via a new `voss_md` helper (NOT `write_fence_body` — Pitfall 5). Both bypass `run_turn`, render ephemeral local blocks never entering model history, and emit `shell.local`/`memory.note` via a new `recorder_bridge.emit()`.

Purpose: INPUT-02/03 — Claude Code `!`/`#`-mode parity with the locked run_turn-bypass + recorder-event contract, riding the central permission gate.
Output: prefix-dispatch branches in input_bar.py, new local_block.py, recorder_bridge.emit, voss_md.append_voss_notes_bullet, local-block tcss classes, green INPUT-02/03 tests + snapshots 5-7 + R1/R2.
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
@.planning/phases/T5-shell-ergonomics/T5-CONTEXT.md
@.planning/phases/T8-input-bar-ergonomics-v0-2/T8-02-SUMMARY.md

<interfaces>
voss/harness/sandbox.py (VERIFIED — the T5-D12 gate, do NOT duplicate):
- `shell_allowed(cmd: str, allowlist=DEFAULT_SHELL_ALLOWLIST) -> tuple[bool, str]` — scans `DENY_TOKENS`, rejects `SHELL_METACHARS`, allowlist-checks the binary; returns `(False, reason)` on rejection
- `split_command(cmd: str) -> list[str]` — argv for `create_subprocess_exec`; caller MUST have passed `shell_allowed` first
- `DEFAULT_SHELL_ALLOWLIST`, `DENY_TOKENS`, `SHELL_METACHARS`, `class SandboxError`

voss/harness/voss_md.py (VERIFIED):
- `parse(text: str) -> list[Block]` — `Block(kind, id, body, recorded_hash)`; `kind="human"` for plain markdown sections, `kind="machine"` for `<!-- voss:begin id=... -->` fences
- `_render(blocks: list[Block]) -> str` — serializes back; human blocks emitted as raw `block.body`
- `write_fence_body(...)` — MACHINE-FENCE ONLY; D-05/Pitfall 5 FORBID using it for `## Notes`
- atomic-write idiom (lines 267-270): `tmp = path.with_suffix(path.suffix+".tmp"); tmp.write_text(...); os.replace(tmp, path)`

voss/harness/tui/recorder_bridge.py (VERIFIED):
- `class RecorderBridge: __init__(self, recorder, app)`; `_call(self, method_name, *args, **kwargs)` — getattr app method, swallow-all `except Exception: pass` (# noqa: BLE001)
- M9-04 contract: ZERO changes to recorder.py or voss_runtime — only add `.emit()` delegating via `_call`

voss/harness/tui/widgets/turn_view.py (analog for local-block render):
- `TurnView(RichLog)` ; `append_turn(role, body, *, ...)` ; renders via `self.write(Text(body, no_wrap=False))` — plain Text, NO markup (untrusted-content rule)
- `set_timer(secs, cb)` reserved for Plan 05 notice; LocalBlockShell/Note here have no timer

input_bar.py after Plan 02 (the analog for adding dispatch branches): `InputBar(Widget)` with child `TextArea`, `.text` property, `action_submit` posts `Submitted` only on non-empty stripped value, `load_text("")` clears.

T8-UI-SPEC locked copy: `!cmd` header `! {cmd}`; footer exit-0 `· exit 0` (signal-good), non-zero `· exit {N}` (signal-error); `#note` block is the single dim line `# note saved` (no note-text echo); empty `!`/`#` → no block. tcss: `.local-block`, `.local-block--shell > .sigil` ($warn bold), `.local-block--note > .sigil` ($accent bold) — verbatim from UI-SPEC §"tcss Additions".
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: LocalBlock widgets + recorder_bridge.emit + voss_md notes helper</name>
  <behavior>
    - LocalBlockShell renders `! {cmd}` header, stdout+stderr body, `· exit {N}` footer (signal-good when 0, signal-error otherwise) — all via plain Text, no markup
    - LocalBlockNote renders exactly the single dim line `# note saved` — no echo of the note text
    - recorder_bridge.emit("shell.local", payload) calls app.on_local_event("shell.local", payload); never raises (swallow-all)
    - append_voss_notes_bullet(path, text, timestamp): creates `## Notes` HUMAN section if absent, appends `- [{timestamp}] {text}` under it, leaves every other block (human + machine fences) byte-identical, atomic-writes
    - append_voss_notes_bullet round-trips through parse(): after append, parse() shows the bullet inside a kind="human" block and zero kind="machine" blocks were altered
  </behavior>
  <read_first>
    - voss/harness/tui/widgets/turn_view.py (Text/no-markup render analog; LocalBlock must NOT subclass TurnView per A2 — separate widget family)
    - voss/harness/tui/recorder_bridge.py (full file — `_call` pattern to extend with `.emit`; M9-04 zero-recorder-change contract)
    - voss/harness/voss_md.py lines 59-101 (parse + Block kinds), 206-295 (write_fence_body atomic idiom + _render — DO NOT call write_fence_body for Notes)
    - T8-RESEARCH.md Pattern 9 (RecorderBridge.emit — A3 ASSUMED, app.on_local_event extension point), Pattern 10 (LocalBlock — A2: separate widget family, not TurnView roles), Pitfall 5 (`## Notes` is a human block — new `append_voss_notes_bullet` helper, never write_fence_body), §"Code Examples > VOSS.md Notes Append"
    - T8-UI-SPEC.md §"tcss Additions" (verbatim classes), §"Copywriting Contract" (locked `! {cmd}` / `· exit N` / `# note saved` strings), §"Component Inventory" (LocalBlock/LocalBlockShell/LocalBlockNote)
    - T8-PATTERNS.md §"local_block.py", §"recorder_bridge.py", §"voss_md.parse() + _render() atomic-write pattern"
  </read_first>
  <action>Create `voss/harness/tui/widgets/local_block.py` with a `LocalBlock` base (`Static` subclass) and `LocalBlockShell(cmd, stdout, stderr, exit_code)` + `LocalBlockNote()` variants, rendering via `rich.text.Text` segment-append with named styles (`.sigil` = bold; footer style `signal-good`/`signal-error` keyed on exit_code) — NO markup strings, all body content wrapped in `Text(...)` (untrusted-content rule). Export the LocalBlock family from `voss/harness/tui/widgets/__init__.py`. Add `def emit(self, event_name: str, payload: dict) -> None` to `RecorderBridge` delegating via `self._call("on_local_event", event_name, payload)` (same swallow-all guard); do NOT touch `flush()`, `_seen`, recorder.py, or voss_runtime (M9-04). Add `def append_voss_notes_bullet(path: Path, text: str, timestamp: str) -> None` to `voss_md.py`: read file, `parse()`, locate the human block containing `## Notes` (or synthesize one at EOF if absent), append the `- [{timestamp}] {text}\n` bullet inside that human block's body, `_render()` the reconstructed block list, atomic-write via the verified tmp+os.replace idiom. Append the 6 T8 tcss classes from UI-SPEC §"tcss Additions" verbatim to `styles.tcss` (after `.dim`) — `.local-block`, `.local-block--shell > .sigil`, `.local-block--note > .sigil`, `.local-block--notice`, `.reverse-search-bar .rs-label`, `.reverse-search-bar .rs-query` (notice/reverse-search classes are defined here but consumed by Plan 05; defining them now keeps styles.tcss single-owned within Wave 2); add NO new palette hex entries.</action>
  <verify>
    <automated>pytest tests/harness/tui/test_prefix_dispatch.py -q -x -k "local_block or notes_helper or emit"</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from voss.harness.tui.widgets import LocalBlockShell, LocalBlockNote; from voss.harness.voss_md import append_voss_notes_bullet; from voss.harness.tui.recorder_bridge import RecorderBridge; assert hasattr(RecorderBridge,'emit')"` exits 0
    - voss_md round-trip test: append a bullet to a VOSS.md containing a machine fence, then assert `parse()` shows the machine block's `recorded_hash` unchanged and the bullet present in a `kind=="human"` block — PASS in test_prefix_dispatch.py
    - `grep -c 'write_fence_body' voss/harness/tui/widgets/input_bar.py voss/harness/voss_md.py | grep -v ':0' | grep -q 'voss_md.py'` (write_fence_body remains only its own def in voss_md.py; the new helper does NOT call it) — assert via `grep -A20 'def append_voss_notes_bullet' voss/harness/voss_md.py | grep -c write_fence_body` returns 0
    - `grep -v '^[/ ]*\*' voss/harness/tui/styles.tcss | grep -c '#[0-9A-Fa-f]\{6\}'` returns exactly 5 (palette not extended — UI-SPEC Acceptance Check 13 surface)
    - `grep -c 'def emit' voss/harness/tui/recorder_bridge.py` returns 1; `git diff voss/harness/tui/recorder_bridge.py` shows no edits to `flush`/`_seen`
  </acceptance_criteria>
  <done>LocalBlock family + recorder emit + voss_md notes helper exist; Notes append never uses write_fence_body and preserves machine fences; palette intact.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: !cmd / #note dispatch in action_submit via the existing gate</name>
  <behavior>
    - `!ls` submitted → shell_allowed("ls") passes → split_command + create_subprocess_exec runs it → LocalBlockShell mounted with stdout + `· exit 0`; recorder_bridge.emit("shell.local", {cmd, exit_code, stdout, stderr}); NO Submitted posted; NO run_turn
    - `!rm -rf /` submitted → shell_allowed returns (False, "denied token: 'rm -rf'") → LocalBlockShell shows the rejection reason; create_subprocess_exec NOT called; NO run_turn
    - `!false` (or any non-zero exit) → LocalBlockShell footer `· exit 1` signal-error; full stdout+stderr shown
    - `#remember to ship` submitted → append_voss_notes_bullet(VOSS.md, "remember to ship", <ISO-8601 UTC, no microseconds>); LocalBlockNote `# note saved`; recorder_bridge.emit("memory.note", {text, timestamp}); NO Submitted; NO run_turn
    - bare `!` / `#` / `!   ` → input cleared, NO block, NO emit, NO Submitted (silent no-op)
    - neither prefix → normal `Submitted(value)` posted (regression guard from Plan 02)
  </behavior>
  <read_first>
    - voss/harness/tui/widgets/input_bar.py (post-Plan-02 file — the analog; add `_dispatch_shell`/`_dispatch_note` + branch `action_submit` before `post_message(Submitted)`)
    - .planning/phases/T5-shell-ergonomics/T5-CONTEXT.md D-12 (edit-mode explicit deny-set / no permission escalation — the carry-forward contract `!cmd` inherits; plan-mode refuses cleanly)
    - T8-RESEARCH.md Pattern 5 (dispatch structure: strip prefix, empty→no-op, else dispatch, return — never fall through to Submitted), §"Don't Hand-Roll" (`!cmd` MUST use sandbox.shell_allowed + asyncio.create_subprocess_exec; duplicating subprocess logic creates a second ungated path = blocker), Anti-Pattern "Making !cmd bypass sandbox.shell_allowed"
    - T8-PATTERNS.md §"sandbox.shell_allowed call contract" (`allowed, reason = shell_allowed(cmd); if not allowed: render local block with reason; return` then `create_subprocess_exec(*split_command(cmd))`)
    - T8-UI-SPEC.md §"INPUT-02 — !cmd dispatch interaction contract", §"INPUT-03 — #note dispatch interaction contract", §"Snapshot-Test Anchors" (5/6/7 + R1/R2)
  </read_first>
  <action>In `input_bar.py`, branch `action_submit` AFTER reading `self.text.strip()` and clearing via `load_text("")`, BEFORE `post_message(Submitted)`: if value starts with `!` → `cmd = value[1:].strip()`; empty → return (no-op); else `await self._dispatch_shell(cmd)`; return. If value starts with `#` → `note = value[1:].strip()`; empty → return; else `await self._dispatch_note(note)`; return. Otherwise post `Submitted` (Plan 02 behavior). `_dispatch_shell(cmd)`: call `sandbox.shell_allowed(cmd)`; on `(False, reason)` mount a `LocalBlockShell` carrying the reason as body + no exec + return (do NOT raise); on `(True, _)` run `asyncio.create_subprocess_exec(*sandbox.split_command(cmd), stdout=PIPE, stderr=PIPE)` (NO `shell=True`, NO `_shell`, NO raw `subprocess` — the existing gate is the only path), capture stdout/stderr/returncode, mount `LocalBlockShell(cmd, stdout, stderr, exit_code)` into the `#main` TurnView's scroll container via the app (NEVER append to the `messages`/conversation list — local blocks must not enter model history), then `self.app.recorder_bridge.emit("shell.local", {"cmd": cmd, "exit_code": rc, "stdout": out, "stderr": err})` guarded so a missing bridge is a no-op. `_dispatch_note(note)`: compute `timestamp` as UTC ISO-8601 without microseconds (`datetime.now(timezone.utc).replace(microsecond=0).isoformat()`), call `voss_md.append_voss_notes_bullet(cwd/"VOSS.md", note, timestamp)` (resolve cwd from the app), mount a `LocalBlockNote`, then `recorder_bridge.emit("memory.note", {"text": note, "timestamp": timestamp})`. Fill `test_prefix_dispatch.py` INPUT-02/03 tests (monkeypatch `sandbox.shell_allowed` per PATTERNS for the allow path; real call for the deny path; assert `recorder_bridge.emit` call args for R1/R2; assert local blocks never reach a conversation/messages list) and the 3 snapshot anchors (5 exit-0, 6 non-zero, 7 `# note saved`), then `pytest tests/harness/tui/ --snapshot-update -k "snap5 or snap6 or snap7"` and commit baselines. Remove the xfail markers on these tests.</action>
  <verify>
    <automated>pytest tests/harness/tui/test_prefix_dispatch.py -q -x</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/tui/test_prefix_dispatch.py -q` exits 0 — including: R1 `recorder_bridge.emit.assert_called_once_with("shell.local", ...)` with cmd/exit_code/stdout/stderr; R2 `emit("memory.note", ...)` with text/timestamp; deny-path test (`!rm -rf /` → reason rendered, exec NOT called — assert via a `create_subprocess_exec` mock that records zero calls); no-op tests (bare `!`/`#` → no emit, no block); regression (plain text → `Submitted` posted)
    - snapshot anchors 5, 6, 7 green with committed baselines under `tests/harness/tui/snapshots/`
    - `grep -nE 'subprocess\.(run|Popen|call|check_)' voss/harness/tui/widgets/input_bar.py` returns nothing (no raw subprocess; only `asyncio.create_subprocess_exec` via `sandbox.split_command`)
    - `grep -c 'shell_allowed' voss/harness/tui/widgets/input_bar.py` returns ≥ 1 and shell_allowed is called BEFORE any exec in `_dispatch_shell` (assert via test: monkeypatch shell_allowed→(False,"x"); assert create_subprocess_exec mock never called)
    - test asserts the `!cmd`/`#note` body never appears in any `EpisodicMemory`/messages list passed to run_turn (UI-SPEC Acceptance Check 14)
  </acceptance_criteria>
  <done>`!cmd` rides the existing T5-D12 gate (deny path proven, no raw subprocess); `#note` writes the human Notes section; both bypass run_turn, render local-only blocks, emit R1/R2; empty-prefix no-op; snapshots 5-7 green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user `!cmd` text → OS process | arbitrary command string crosses into subprocess execution |
| user `#note` text → VOSS.md on disk | arbitrary text written to a project file |
| local block → model conversation | local blocks MUST NOT cross into model history |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T8-06 | Tampering / EoP | `!cmd` arbitrary shell execution (INPUT-02, highest-risk) | mitigate | D-03 LOCKED: route through the EXISTING `sandbox.shell_allowed()` (DENY_TOKENS + SHELL_METACHARS + binary allowlist) then `split_command()` + `asyncio.create_subprocess_exec` (no shell, no `_shell`). NO parallel allowlist, NO raw `subprocess`. Deny-path test proves rejected commands never exec. `grep` gate forbids `subprocess.run/Popen/call`. Permission-mode behavior inherited from the gate (plan-mode refuses cleanly, no escalation) — T5-D12 carry-forward |
| T-T8-07 | Tampering | `#note` write to VOSS.md (INPUT-03) | mitigate | path-constrained append under project `## Notes` via new `append_voss_notes_bullet` (NOT `write_fence_body` — Pitfall 5); note text is literal body content (not a path → no traversal); machine fences proven byte-stable by round-trip test; atomic tmp+os.replace |
| T-T8-08 | Information disclosure | local `!cmd` output leaking into model context | mitigate | local blocks rendered into the scroll container only; test asserts `!cmd`/`#note` bodies never appear in the messages/EpisodicMemory list reaching run_turn (UI-SPEC Acceptance Check 14) |
| T-T8-09 | Tampering | recorder_bridge.emit corrupting RunRecorder | mitigate | `.emit` delegates via existing swallow-all `_call`; M9-04 contract — zero edits to recorder.py/voss_runtime; `git diff` gate confirms flush/_seen untouched |
| T-T8-SC | Tampering | npm/pip installs | mitigate | no package installs in this plan (Plan 01 owns dev-dep install) |
</threat_model>

<verification>
- `pytest tests/harness/tui/test_prefix_dispatch.py -q` exits 0 (R1/R2 + deny-path + no-op + snapshots 5-7)
- `grep -nE 'subprocess\.(run|Popen|call|check_)' voss/harness/tui/widgets/input_bar.py` empty
- `pytest tests/harness/tui/ -q` exits 0 (no Wave-1 regression)
- voss_md machine-fence round-trip preserved (hash unchanged after Notes append)
</verification>

<success_criteria>
- `!cmd` executes ONLY via sandbox.shell_allowed + split_command + create_subprocess_exec; deny-set rejection surfaces and blocks exec
- `#note` appends to `## Notes` human section without write_fence_body; machine fences untouched
- Both bypass run_turn, render local-only blocks (never in model history), emit shell.local / memory.note
- Empty `!`/`#` silent no-op; plain text still posts Submitted
- Snapshots 5-7 + R1/R2 green; palette/keymap/recorder M9 contracts intact
</success_criteria>

<output>
Create `.planning/phases/T8-input-bar-ergonomics-v0-2/T8-03-SUMMARY.md` when done
</output>
