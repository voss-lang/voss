---
phase: F4
plan_id: F4-02
title: "Python ContextTracker + context OSC emission + pin file reader"
wave: 1
depends_on: []
files_modified:
  - voss/harness/recorder.py
  - voss/harness/agent.py
  - voss/harness/test_context_osc.py
autonomous: true
status: pending
---

<objective>
Add a `ContextTracker` class to `recorder.py` that accumulates per-file context state during `observe()` calls, emit context data as `voss-context=` OSC sequences at `end_iteration()`, and read pin commands from `.voss/context-pins.json` at iteration start. This is the Python harness side of the F4 data pipeline.

Purpose: Without context emission from the harness, the ADE has no context heatmap data. This plan is file-disjoint from F4-01 (Rust side) and runs in parallel.

Output: `ContextTracker`/`FileContextState` classes, `_emit_context_osc()` function, pin file reader, wiring in `agent.py`, and focused Python tests.

**RESEARCH DEVIATION from D-19:** CONTEXT.md D-19 specified "PTY stdin injection" for pin commands. Research (F4-RESEARCH.md OQ-1) found this WON'T WORK -- the harness reads stdin through the shell, not raw bytes. OSC sequences injected via `pty_write` go to the PTY master then to the shell, which displays them as garbage. This plan uses a file-based pin channel (`.voss/context-pins.json`) instead. The ADE writes this file; the harness reads it at iteration start. This is simpler and more reliable.
</objective>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Harness stdout -> PTY byte stream | Harness writes `voss-context=` OSC to stdout; Rust reader parses it |
| `.voss/context-pins.json` file -> harness | ADE writes pin commands to file; harness reads at iteration start |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-F4-05 | Tampering | context-pins.json | mitigate | Pin only validates against existing `files_in_context` keys (D-22). Arbitrary paths rejected. |
| T-F4-06 | Race | context-pins.json read/write | mitigate | ADE uses atomic write (write-then-rename). Harness reads at iteration start (single point). |
| T-F4-07 | DoS | Context payload size | mitigate | File list capped at 200 entries in `_emit_context_osc()`. Truncate oldest files beyond cap. |
| T-F4-08 | Info Disclosure | File paths in OSC | accept | Paths are relative project paths, data stays local within the PTY stream. |
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add FileContextState dataclass + ContextTracker class to recorder.py</name>
  <files>voss/harness/recorder.py</files>
  <read_first>
    - voss/harness/recorder.py (full file — 354 lines)
    - .planning/phases/F4-visual-context-heatmap/F4-RESEARCH.md (lines 72-92 — ContextTracker design)
    - .planning/phases/F4-visual-context-heatmap/F4-CONTEXT.md (D-14, D-20, D-21, D-22, D-25 — state model and pinning rules)
  </read_first>
  <action>
    **Add `FileContextState` dataclass** after the existing imports and before `_emit_budget_osc`. Fields:
    - `path: str`
    - `tokens: int`
    - `state: str` (default `"full"`) — values: "full" | "dropped"
    - `pinned: bool` (default `False`)

    **Add `ContextTracker` class** after `FileContextState`. This is a standalone class, NOT a method on RunRecorder (same pattern as `_emit_budget_osc` being module-level). Fields:
    - `files: dict[str, FileContextState]` — keyed by path
    - `pinned: set[str]` — paths that are pinned
    - `prev_prompt_tokens: int` — for drop detection

    Methods:
    - `__init__(self)` — initialize empty files dict, empty pinned set, prev_prompt_tokens=0
    - `track_file(self, path: str, content: str)` — estimate tokens as `max(len(content) // 4, 1)`, create or update `FileContextState(path=path, tokens=tokens, state="full", pinned=path in self.pinned)`. Called from `observe()` when `fs_read` succeeds.
    - `detect_drops(self, prompt_tokens: int)` — if `self.prev_prompt_tokens > 0` and `prompt_tokens < self.prev_prompt_tokens`, mark oldest non-pinned files as `"dropped"` (sort files by insertion order, mark from oldest until token deficit is accounted for). Update `self.prev_prompt_tokens = prompt_tokens`.
    - `load_pins(self, pin_file: Path)` — read `.voss/context-pins.json` if it exists. Expected format: `{"pinned": ["path1", "path2"]}`. Validate each path against current `self.files` keys (D-22). Update `self.pinned` set and set `pinned=True` on matching `FileContextState` entries.
    - `snapshot(self) -> dict` — return the D-25 payload dict: `{"system_tokens": 0, "conversation_tokens": 0, "total_tokens": sum(f.tokens for f in files), "token_limit": None, "files": [{"path": f.path, "tokens": f.tokens, "state": f.state, "pinned": f.pinned} for f in files sorted by tokens desc]}`. Limit files list to 200 entries (truncate smallest). `system_tokens` and `conversation_tokens` are 0 for now — the harness doesn't track these separately yet.

    **Add `_context_tracker` field to `RunRecorder.__init__`:** `self._context_tracker = ContextTracker()`. This makes each run have its own tracker.
  </action>
  <acceptance_criteria>
    - `grep -c "class ContextTracker" voss/harness/recorder.py` returns 1
    - `grep -c "class FileContextState" voss/harness/recorder.py` returns 1
    - `grep -c "_context_tracker" voss/harness/recorder.py` returns at least 1
    - `.venv/bin/python -c "from voss.harness.recorder import ContextTracker, FileContextState; print('import ok')"` exits 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Add _emit_context_osc() function</name>
  <files>voss/harness/recorder.py</files>
  <read_first>
    - voss/harness/recorder.py (lines 22-48 — _emit_budget_osc as pattern reference)
    - .planning/phases/F4-visual-context-heatmap/F4-CONTEXT.md (D-23, D-24, D-26 — OSC format, cadence, full snapshot)
    - .planning/phases/F4-visual-context-heatmap/F4-PATTERNS.md (Pattern 4 — OSC emission pattern)
  </read_first>
  <action>
    **Add `_emit_context_osc` module-level function** after `_emit_budget_osc`. Signature: `def _emit_context_osc(payload: dict) -> None`. The function:
    1. Serializes `payload` with `json.dumps(payload, separators=(",", ":"))` for compact output.
    2. Writes `f"\x1b]1337;voss-context={json_str}\x07"` to `sys.stdout`.
    3. Calls `sys.stdout.flush()`.

    Doc comment: `"""Write an OSC 1337 voss-context= sequence to stdout (F4 D-23, D-24). Stripped by reader.rs extract_voss_osc before bytes reach xterm."""`

    This mirrors `_emit_budget_osc` exactly, with a different prefix.
  </action>
  <acceptance_criteria>
    - `grep -c "_emit_context_osc" voss/harness/recorder.py` returns at least 1
    - `grep "voss-context=" voss/harness/recorder.py` finds the OSC write line
    - `.venv/bin/python -c "from voss.harness.recorder import _emit_context_osc; print('import ok')"` exits 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Wire ContextTracker into observe() and end_iteration(), emit context OSC in agent.py</name>
  <files>voss/harness/recorder.py, voss/harness/agent.py</files>
  <read_first>
    - voss/harness/recorder.py (lines 90-116 — observe() method with INSPECT_TOOLS check)
    - voss/harness/agent.py (lines 42-43 — existing imports from recorder)
    - voss/harness/agent.py (lines 756-862 — all 3 _emit_budget_osc call sites)
    - .planning/phases/F4-visual-context-heatmap/F4-CONTEXT.md (D-24 — emit after budget emission at end_iteration)
  </read_first>
  <action>
    **recorder.py observe() update:** In the `observe` method, after the existing `if tool_name in INSPECT_TOOLS:` block (which records path to `self.inspected`), add: if `tool_name == "fs_read"` and `ok is True` and `result` is a non-empty string, call `self._context_tracker.track_file(path, str(result))` where `path = args.get("path", "")`.

    **recorder.py end_iteration() update:** At the end of `end_iteration` (after setting `target.ended_at`), add:
    ```python
    self._context_tracker.detect_drops(prompt_tokens)
    ```
    This updates the tracker's drop detection state each iteration.

    **agent.py import update:** Add `_emit_context_osc` to the import from `voss.harness.recorder`:
    ```python
    from .recorder import RunRecorder, _emit_budget_osc, _emit_context_osc, write_decisions_md
    ```

    **agent.py pin file loading:** At the top of the `while iteration_index < max_iterations:` loop body (around line 591, before `iter_rec = rec.begin_iteration()`), add:
    ```python
    # F4: load pin commands from file-based channel
    _pin_file = cwd / ".voss" / "context-pins.json"
    rec._context_tracker.load_pins(_pin_file)
    ```

    **agent.py context OSC emission:** After EACH of the three existing `_emit_budget_osc(...)` calls, add:
    ```python
    _emit_context_osc(rec._context_tracker.snapshot())
    ```
    This emits context state right after budget state, at the same cadence (D-24).
  </action>
  <acceptance_criteria>
    - `grep -c "_emit_context_osc" voss/harness/agent.py` returns at least 4 (1 import + 3 call sites)
    - `grep -c "context_tracker" voss/harness/agent.py` returns at least 1 (pin file loading)
    - `grep -c "track_file" voss/harness/recorder.py` returns at least 2 (definition + call in observe)
    - `grep -c "detect_drops" voss/harness/recorder.py` returns at least 2 (definition + call in end_iteration)
    - `.venv/bin/python -c "from voss.harness.recorder import _emit_context_osc; print('ok')"` exits 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Python unit tests for ContextTracker and _emit_context_osc</name>
  <files>voss/harness/test_context_osc.py</files>
  <read_first>
    - voss/harness/recorder.py (ContextTracker class + _emit_context_osc from Tasks 1-2)
    - voss/harness/test_budget_osc.py (pattern reference for stdout capture tests)
    - .planning/phases/F4-visual-context-heatmap/F4-RESEARCH.md (lines 143-158 — test seams T-F4-05..T-F4-08)
  </read_first>
  <action>
    **Create `voss/harness/test_context_osc.py`** with the following tests:

    1. `test_context_tracker_track_file` — create a ContextTracker, call `track_file("src/main.rs", "fn main() { ... }")`, assert the file appears in `tracker.files` with estimated tokens and state "full".

    2. `test_context_tracker_detect_drops` — track 3 files, then call `detect_drops(100)` followed by `detect_drops(50)` (simulating token decrease). Assert at least one non-pinned file is marked "dropped".

    3. `test_context_tracker_pinned_immune_to_drops` — track 2 files, pin one, call detect_drops with decreasing tokens. Assert pinned file stays "full", non-pinned file gets "dropped".

    4. `test_context_tracker_load_pins` — write a `context-pins.json` file via `tmp_path`, track a file matching one of the pin paths, call `load_pins`, assert the file's `pinned` field is True.

    5. `test_context_tracker_load_pins_rejects_unknown_paths` — write pins with a path not in tracked files, call `load_pins`, assert pinned set does not include the unknown path (D-22).

    6. `test_context_tracker_snapshot_sorted_by_tokens` — track 3 files with different content lengths, call `snapshot()`, assert `files` list is sorted by tokens descending.

    7. `test_context_tracker_snapshot_caps_at_200` — track 201 files, call `snapshot()`, assert `files` list has exactly 200 entries.

    8. `test_emit_context_osc_writes_to_stdout` — monkeypatch stdout, call `_emit_context_osc({"total_tokens": 100, "files": []})`, assert output starts with `\x1b]1337;voss-context=` and ends with `\x07`.

    9. `test_emit_context_osc_payload_is_valid_json` — extract JSON between prefix and BEL, parse with `json.loads`, assert fields match input.

    10. `test_pin_file_roundtrip` — write a pins file, read it with `load_pins`, verify tracked files get `pinned=True`, then verify `snapshot()` reflects the pin state.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest voss/harness/test_context_osc.py -x -v` shows 10 tests passing
    - Tests cover: track_file, detect_drops, pin immunity, pin loading, pin rejection (D-22), snapshot sorting, snapshot cap, OSC emission, JSON validity, pin roundtrip
    - No test imports anything from the frontend (pure Python testing)
  </acceptance_criteria>
</task>

</tasks>

<must_haves>
  truths:
    - "ContextTracker.track_file estimates tokens via len(content) // 4 heuristic and stores as FileContextState with state='full'"
    - "ContextTracker.detect_drops marks oldest non-pinned files as 'dropped' when prompt_tokens decreases"
    - "ContextTracker.load_pins only accepts paths that exist in self.files (D-22 enforcement)"
    - "ContextTracker.snapshot returns a dict matching D-25 payload shape with files sorted by tokens desc and capped at 200"
    - "_emit_context_osc writes ESC]1337;voss-context={json}BEL to sys.stdout with flush"
    - "Context OSC is emitted after budget OSC at all 3 end_iteration call sites in agent.py (D-24)"
    - "Pin file (.voss/context-pins.json) is read at iteration start, not mid-turn (D-20)"
  artifacts:
    - path: "voss/harness/recorder.py"
      provides: "ContextTracker + FileContextState classes + _emit_context_osc function"
      contains: "_emit_context_osc"
    - path: "voss/harness/agent.py"
      provides: "Context OSC emission at 3 call sites + pin file loading at iteration start"
      contains: "_emit_context_osc"
    - path: "voss/harness/test_context_osc.py"
      provides: "10 unit tests for ContextTracker and _emit_context_osc"
      contains: "test_context_tracker"
  key_links:
    - from: "voss/harness/agent.py"
      to: "voss/harness/recorder.py"
      via: "from .recorder import _emit_context_osc"
      pattern: "_emit_context_osc"
</must_haves>
