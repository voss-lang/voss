---
phase: M9
plan: 06
type: execute
wave: 4
depends_on: [M9-03, M9-04, M9-05]
files_modified:
  - voss/harness/session.py
  - voss/harness/tui/fork.py
  - voss/harness/tui/widgets/fork_modal.py
  - voss/harness/tui/widgets/__init__.py
  - voss/harness/tui/app.py
  - voss/harness/tui/renderer.py
  - voss/harness/render.py
  - voss/harness/cli.py
  - tests/harness/tui/test_session_fork.py
  - tests/harness/tui/test_session_backward_compat.py
  - tests/harness/tui/test_cli_integration.py
  - tests/harness/tui/test_accent_allowlist_audit.py
  - tests/harness/tui/test_no_unicode_fallback.py
  - tests/harness/tui/test_windows_console_strategy.py
  - tests/harness/tui/test_plain_parity.py
autonomous: false
requirements: [TUI-08, TUI-09, TUI-10]
must_haves:
  truths:
    - "voss resume <id> on a pre-M9 session JSON file loads without crashing in both --plain and TUI modes."
    - "Pressing `f` on a focused turn opens ForkConfirmModal; on Enter, a new SessionRecord is written with parent_id field set."
    - "Default voss chat / voss do / voss edit / voss resume on a TTY uses TextualRenderer (live swap-in from M9-02 force_tui path)."
    - "--plain stdout byte-output remains identical to the M9-01 baseline; test_plain_parity green after every Wave-4 commit."
    - "Auditor grep over the entire voss/harness/tui/ tree confirms accent color (`$accent` / `.accent` / `#5FAFFF`) appears only on the 6 UI-SPEC allow-list elements."
    - "When --no-unicode is set, glyphs.py constants fall back to ASCII; box-drawing falls back to + - | characters."
    - "Windows console detection picks one of {hard-block, soft-degrade, auto-plain} strategies and emits the UI-SPEC-locked notice copy."
  artifacts:
    - path: "voss/harness/session.py"
      provides: "SessionRecord gains optional parent_id and parent_turn_index fields (additive, backward compatible)"
    - path: "voss/harness/tui/fork.py"
      provides: "fork_session(record, turn_index, cwd) -> SessionRecord; pure function, no UI"
      exports: ["fork_session"]
    - path: "voss/harness/tui/widgets/fork_modal.py"
      provides: "ForkConfirmModal — Enter to fork, Esc to cancel; locked copy"
      exports: ["ForkConfirmModal"]
    - path: "tests/harness/tui/test_accent_allowlist_audit.py"
      provides: "Grep-based accent allow-list audit per UI-SPEC Acceptance Visual Check 3"
    - path: "tests/harness/tui/test_no_unicode_fallback.py"
      provides: "--no-unicode mode glyph fallback verification"
    - path: "tests/harness/tui/test_windows_console_strategy.py"
      provides: "Windows-console fallback decision: which strategy fires under which capability set"
  key_links:
    - from: "voss/harness/cli.py"
      to: "voss/harness/tui/app.py:VossTUIApp"
      via: "make_renderer default path now constructs VossTUIApp() and returns TextualRenderer(app) when capability says yes"
      pattern: "return TextualRenderer"
    - from: "voss/harness/tui/widgets/fork_modal.py"
      to: "voss/harness/tui/fork.py:fork_session"
      via: "ForkConfirmModal posts ForkConfirmed; app handler calls fork_session() and shows resume flash"
      pattern: "fork_session"
    - from: "voss/harness/tui/fork.py"
      to: "voss/harness/session.py:SessionRecord"
      via: "fork_session creates a SessionRecord with parent_id + parent_turn_index set"
      pattern: "SessionRecord\\("
---

<objective>
Final integration wave. (1) Add fork-from-turn UX backed by additive SessionRecord fields that preserve backward compat with pre-M9 session JSON files. (2) Flip the make_renderer default path so a TTY user gets the TextualRenderer by default while `--plain` and non-TTY still get PlainRenderer byte-identically. (3) Wire the TUI permissions bridge from M9-05 into cli.py at the four interactive entry points. (4) Land the UI-SPEC Acceptance Visual Checks as automated audits: accent allow-list, --no-unicode fallback, Windows console strategy.

Purpose: TUI-08 (fork + resume in TUI), final TUI-09 (full keymap wired), final TUI-10 (parity acceptance + Windows strategy). This is the only plan with a checkpoint: the live swap-in is user-visible, and a single human-verify checkpoint at the end gives the user a chance to bless or back out before the phase closes.

Output: backward-compat session schema, fork modal + pure fork function, cli.py wiring, three audit test files, and the final phase-level visual checkpoint.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md
@.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md
@voss/harness/session.py
@voss/harness/cli.py
@voss/harness/render.py
@voss/harness/permissions.py

<interfaces>
<!-- SessionRecord today (voss/harness/session.py lines 84-107): -->
```python
@dataclass
class SessionRecord:
    id: str
    name: str
    cwd: str
    model: str
    started_at: str
    updated_at: str
    total_cost_usd: float = 0.0
    turns: list[dict] = field(default_factory=list)
    runs: list[dict] = field(default_factory=list)
```

<!-- Backward-compat rehydrator (lines 116-123): -->
```python
_SESSION_FIELDS = {f.name for f in dataclasses.fields(SessionRecord)}
def _hydrate(data: dict) -> SessionRecord:
    kept = {k: v for k, v in data.items() if k in _SESSION_FIELDS}
    kept.setdefault("turns", [])
    kept.setdefault("runs", [])
    return SessionRecord(**kept)
```

<!-- _hydrate ALREADY drops unknown keys, so adding new fields is safe in BOTH directions:
     - Old reader + new file: new keys dropped (fine; old reader didn't need them).
     - New reader + old file: missing fields take their default values (fine).
-->

<!-- cli.py entry-point call sites that need plain= + force_tui= plumbing finalized: -->
- do_cmd line 538: renderer = make_renderer(json_mode=json_mode)         → add plain=plain
- _run_repl line 701: renderer = make_renderer(json_mode=json_mode)       → add plain=plain
- resume_cmd line ~970 (passes plain via _run_repl)
- edit_cmd line ~676 (passes plain via _run_repl)

<!-- UI-SPEC accent allow-list (the only 6 elements that may carry `.accent` / `$accent` / `#5FAFFF`): -->
1. The user-input glyph `▌` at input bar.
2. The session id in the header.
3. The current model name in the status line.
4. The active sub-agent name banner in the side panel header.
5. The current selection in the slash palette (combined with reverse-video).
6. Confidence bars at the agent's FINAL confidence value (per-step bars stay grey).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: SessionRecord additive fields + fork_session + ForkConfirmModal + backward-compat tests</name>
  <files>voss/harness/session.py, voss/harness/tui/fork.py, voss/harness/tui/widgets/fork_modal.py, voss/harness/tui/widgets/__init__.py, voss/harness/tui/app.py, tests/harness/tui/test_session_fork.py, tests/harness/tui/test_session_backward_compat.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/session.py (full file; confirm _hydrate behavior; confirm save() uses dataclasses.asdict; new fields auto-roundtrip)
    - /Users/benjaminmarks/Projects/Voss/tests/harness/test_session.py + test_session_redaction.py (existing test patterns + redaction invariants; new fields must NOT carry credentials — parent_id is just a UUID-shaped string, parent_turn_index is an int)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md (Copywriting: Fork-from-turn confirmation modal heading + body + buttons verbatim; Session resume opens flash copy)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md (Fork-from-turn data model is at planner's discretion; this plan picks "new session row with parent_id pointer", NOT a tree of children in a single file — keeps `voss sessions` listing flat)
  </read_first>
  <behavior>
    - Test (test_session_backward_compat): write a SessionRecord WITHOUT parent_id (pre-M9 shape), load it, assert `record.parent_id is None` (default) and no crash.
    - Test: write a new SessionRecord WITH parent_id="abc...", round-trip through save/load, assert parent_id and parent_turn_index survive intact.
    - Test: parent_id and parent_turn_index appear in `_SESSION_FIELDS` AFTER the schema change.
    - Test (test_session_redaction.py expansion): an explicit assertion that parent_id is a 12-char hex string and parent_turn_index is a non-negative int — both fail-closed under the existing redaction invariant test.
    - Test (test_session_fork): `fork_session(record=R, turn_index=3, cwd=tmp)` returns a new SessionRecord with `parent_id == R.id`, `parent_turn_index == 3`, `turns == R.turns[:3+1]`, `runs == R.runs[:N]` where N is the count of runs whose started_at is on or before turn 3's timestamp (best-effort). It writes via existing `session.save()` and returns the persisted record.
    - Test: fork_session does NOT modify or delete the original record; original file on disk unchanged.
    - Test (ForkConfirmModal): heading exactly `Fork session from turn 3?`; body exactly per UI-SPEC `Creates a new session starting from this turn. The current session keeps its history.`; Enter posts ForkConfirmed; Esc posts ForkCancelled.
  </behavior>
  <action>
    Edit `voss/harness/session.py`:
      - Add to SessionRecord: `parent_id: Optional[str] = None` and `parent_turn_index: Optional[int] = None`.
      - `_SESSION_FIELDS` auto-updates because it iterates fields().
      - Update the module docstring's "Redaction guarantee" paragraph to note the two new fields and confirm neither can carry credentials.

    Create `voss/harness/tui/fork.py`:
      ```python
      from pathlib import Path
      from voss.harness.session import SessionRecord, save
      from voss_runtime import EpisodicMemory
      from datetime import datetime, timezone
      import uuid

      def fork_session(record: SessionRecord, turn_index: int, cwd: Path) -> SessionRecord:
          """Create a new SessionRecord seeded from record's first turn_index+1 turns.

          Original record is NEVER modified. Returns the persisted new record.
          """
          if turn_index < 0 or turn_index >= len(record.turns):
              raise ValueError(f"turn_index {turn_index} out of range for {len(record.turns)} turns")
          new = SessionRecord(
              id=uuid.uuid4().hex[:12],
              name=f"fork-of-{record.id[:8]}-t{turn_index}",
              cwd=record.cwd,
              model=record.model,
              started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
              updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
              total_cost_usd=0.0,
              turns=list(record.turns[: turn_index + 1]),
              runs=[],
              parent_id=record.id,
              parent_turn_index=turn_index,
          )
          # Rebuild EpisodicMemory from the kept turns so save() can persist.
          history = EpisodicMemory(capacity=40)
          for t in new.turns:
              history.add(t.get("content", ""), role=t.get("role", "user"))
          save(new, history)
          return new
      ```

    Create `voss/harness/tui/widgets/fork_modal.py`:
      - ForkConfirmModal(turn_n: int) renders heading + body + footer per UI-SPEC verbatim. BINDINGS `[("enter","confirm"),("escape","cancel")]`. Posts ForkConfirmed(turn_n) or ForkCancelled.
      - Re-export from widgets/__init__.py.

    Wire app handler in `voss/harness/tui/app.py`: bind `f` key (already in KEYMAP from M9-03) to `action_fork_turn` which reads the focused turn index from TurnView, pushes ForkConfirmModal, on confirm calls `fork_session(self.record, idx, Path(self.record.cwd))`, then flashes the StatusLine with `Resumed {new_id} · {n} turns` per UI-SPEC.

    Tests: 7 tests across two files.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/tui/test_session_fork.py tests/harness/tui/test_session_backward_compat.py tests/harness/test_session.py tests/harness/test_session_redaction.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from dataclasses import fields; from voss.harness.session import SessionRecord; names = {f.name for f in fields(SessionRecord)}; assert 'parent_id' in names and 'parent_turn_index' in names"` exits 0.
    - `python -c "from voss.harness.tui.fork import fork_session; print('ok')"` exits 0.
    - `grep -c "Fork session from turn " voss/harness/tui/widgets/fork_modal.py` returns >= 1.
    - `pytest tests/harness/test_session.py tests/harness/test_session_redaction.py -x -q` green (no regression).
    - All new fork tests pass.
  </acceptance_criteria>
  <done>parent_id + parent_turn_index added as additive optional fields; old session files load without crash; new fork_session pure function + ForkConfirmModal ship; redaction invariant extended over both new fields.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: cli.py wiring + make_renderer default flip + install_tui_permissions invocation + accent + no-unicode + Windows-console audits</name>
  <files>voss/harness/cli.py, voss/harness/render.py, voss/harness/tui/renderer.py, voss/harness/tui/app.py, voss/harness/tui/glyphs.py, tests/harness/tui/test_cli_integration.py, tests/harness/tui/test_accent_allowlist_audit.py, tests/harness/tui/test_no_unicode_fallback.py, tests/harness/tui/test_windows_console_strategy.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cli.py (lines 511-575 do_cmd; 599-620 chat_cmd; 647-685 edit_cmd; 955-981 resume_cmd; 688-740 _run_repl)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/render.py (M9-02 make_renderer; the default path currently still returns TtyRenderer when TTY+no-plain+no-force_tui — flip this in Task 2 so the default becomes TextualRenderer)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/permissions_bridge.py (M9-05 — install_tui_permissions hook to wire)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/styles.tcss (M9-02 — accent variable lives here)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/glyphs.py (M9-02 — add NO_UNICODE_FALLBACK dict mapping each glyph to ASCII)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md (Acceptance Visual Checks 1-10 — they are the audit checklist for this task; "Color Contract" Monochrome row; "Windows console limitation hit" copy)
  </read_first>
  <behavior>
    - Test (test_cli_integration): `CliRunner().invoke(do_cmd, ["x"])` (default, no --plain, CliRunner stdout is non-TTY) → uses PlainRenderer (auto non-TTY rule); stdout matches the M9-01 baseline byte-for-byte.
    - Test: `CliRunner().invoke(do_cmd, ["x"], env={"FORCE_TUI":"1"})` → uses TextualRenderer (force_tui hook from M9-01).
    - Test: `CliRunner().invoke(chat_cmd, [])` with monkeypatched `sys.stdout.isatty=lambda:True`, `shutil.get_terminal_size=(100,30)` → returns a renderer of type TextualRenderer.
    - Test (test_accent_allowlist_audit): walk voss/harness/tui/, grep every occurrence of `accent`, `#5FAFFF`, or `$accent` (case-insensitive). For each match, classify by file + line context (which widget it lives in). Assert classifications fall ONLY into the 6 UI-SPEC allow-list buckets: input-prompt glyph (input_bar.py), header session id (header.py), status-line model field (status_line.py), sub-agent header (sub_agent_panel.py), slash-palette selection (slash_palette.py), final confidence bar (confidence_bar.py is_final path). Any other file containing accent → test fails with the offending location.
    - Test (test_no_unicode_fallback): set env `VOSS_NO_UNICODE=1`. Importing glyphs returns the fallback mapping: `PROMPT="|"`, `TOOL_CALL=">"`, `WARN="!"`, `BAR_FILL="#"`, `BAR_EMPTY="."`, `BUDGET_FILL="="`, `BUDGET_EMPTY="-"`, `NEST_LAST="+-"`, `NEST_MID="+-"`, `FORK="+"`. Without the env, the locked Unicode values remain.
    - Test (test_windows_console_strategy): monkeypatch `sys.platform="win32"` and `os.environ["WT_SESSION"]` absent (Windows console, not Windows Terminal). `tui_should_activate()` returns `TUIDecision(activate=False, reason="Windows console missing capability")` and the auto-fallback stderr notice matches the UI-SPEC locked string `voss: Windows console missing capability {cap} · using --plain mode`. With `WT_SESSION` SET (Windows Terminal), activate=True.
    - Test (test_plain_parity, expanded): the M9-01 baseline still passes byte-for-byte after the default-path flip (sanity gate — Wave 4 must NOT regress --plain).
  </behavior>
  <action>
    Edit `voss/harness/render.py` `make_renderer`:
      - When `json_mode=True` → JsonRenderer (unchanged).
      - Else compute `decision = tui_should_activate(plain=plain, ...)`.
      - If `decision.activate is True`: `from .tui.app import VossTUIApp; from .tui.renderer import TextualRenderer; app = VossTUIApp(); return TextualRenderer(app=app)` AND mark the app to start asynchronously when the first render call lands (or expose a `start()` method the CLI calls before run_turn).
      - Else if `sys.stdout.isatty()` and NOT plain: `return TtyRenderer()` (fallback path retained for env where Textual fails — e.g. Windows console without Terminal).
      - Else: `return PlainRenderer()`.

    Edit `voss/harness/cli.py`:
      - For each of `do_cmd`, `_run_repl`: after gate construction (lines ~541-555 do_cmd, ~722-727 _run_repl), check if renderer is a TextualRenderer (use isinstance with a deferred import); if yes, call `install_tui_permissions(gate, renderer.app)`. This is the only cli.py logic addition.
      - Make sure the app is started/stopped around the asyncio.run(run_turn(...)) block — Textual's typical pattern is `await app.run_async()` in the same loop. The exact API call depends on Textual's `run_async` / `_run_pilot` surface; use Context7 for `textual app run async` if unsure.

    Edit `voss/harness/tui/glyphs.py`:
      - Add a module-level `_NO_UNICODE = os.environ.get("VOSS_NO_UNICODE") == "1"` check at import time.
      - If True, replace each constant's value with the ASCII fallback.
      - If False, keep the locked Unicode codepoints.

    Edit `voss/harness/tui/app.py` to call `os.environ.get("FORCE_TUI")` honoring (already handled by capability), and add a Windows-console detection branch in `tui_should_activate` (M9-01): if `sys.platform == "win32"` AND no `WT_SESSION` env, return inactive with the locked notice copy.

    Create three audit test files:
      - test_accent_allowlist_audit.py: walk `voss/harness/tui/` with `Path.rglob("*.py")` + `.tcss`; for each file, grep matches; assert file basename ∈ the allow-list set.
      - test_no_unicode_fallback.py: subprocess invocation of `python -c "from voss.harness.tui import glyphs; print(glyphs.PROMPT)"` with `VOSS_NO_UNICODE=1` in env; assert stdout is `|`. Without env, assert `▌`.
      - test_windows_console_strategy.py: monkeypatch `sys.platform`, `os.environ`, call `tui_should_activate`, assert reason string.

    Update `tests/harness/tui/test_plain_parity.py` to ALSO assert the post-flip default path (no --plain, no FORCE_TUI, CliRunner non-TTY): still byte-identical to baseline.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/tui/ tests/harness/test_cli.py tests/harness/test_permissions_modes.py tests/harness/test_session.py tests/harness/test_session_redaction.py tests/harness/test_happy_path_integration.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "install_tui_permissions" voss/harness/cli.py` returns >= 2 (do_cmd + _run_repl).
    - `grep -c "return TextualRenderer" voss/harness/render.py` returns >= 1 (default path now constructs the TUI renderer).
    - test_accent_allowlist_audit passes — confirms accent appears ONLY in the 6 allow-listed widget files.
    - test_no_unicode_fallback passes for both env states.
    - test_windows_console_strategy passes for both Windows console and Windows Terminal.
    - test_plain_parity passes (M9-10 contract intact through Wave 4).
    - Full test suite green: `pytest tests/ -x -q` exit code 0.
  </acceptance_criteria>
  <done>Default TTY user gets the Textual TUI. --plain user gets byte-identical plain output. Permissions bridge installed at all 4 entry points. UI-SPEC accent allow-list, --no-unicode fallback, and Windows console strategy are automated gates.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Phase-final human verification of UI-SPEC Acceptance Visual Checks 1-10</name>
  <what-built>
    The full M9 TUI shell is live. `voss chat` on a TTY opens a Textual full-screen app with header / main / status / input regions; the side panel appears when subagents spawn; slash palette opens on `/`; `?` opens help; diff approval, permission prompts, and budget exhaustion are modals; fork-from-turn (`f`) creates a backward-compat-additive new session; `--plain` and non-TTY paths are byte-identical to pre-M9 output.

    Automated audits cover Acceptance Visual Checks 2 (glyph vocabulary), 3 (accent allow-list), 4 (--plain parity), 5 (NO_COLOR / --no-unicode), 6 (no new runtime hooks), 7 (destructive confirmations present), 10 (reserved slash names not occupied).

    Checks 1 (80x24 minimum honored), 8 (empty states render), and 9 (help overlay reachable) need a human eye on a real terminal because they involve visual layout judgment.
  </what-built>
  <how-to-verify>
    Run each of the following in a separate terminal. Take a screenshot or visual note for each; no need to commit screenshots.

    1. Min-size guard:
       a. Resize your terminal to 79 cols × 24 rows. Run `voss chat`. Expected: exits with code 2 and stderr message `voss: terminal must be at least 80×24 (current: 79×24). Resize or use --plain.`.
       b. Resize to 80 × 24 exactly. Run `voss chat`. Expected: app mounts, all four regions visible, no truncation of header glyphs or status fields.
    2. Empty states (UI-SPEC Acceptance Visual Check 8):
       a. Run `voss chat` in a fresh repo (no prior sessions). Expected: main pane shows `No turns yet` heading + `Type a task below to start. Use / for commands, ? for help.` body.
       b. Press `/` then type `sessions` and Enter (or type `/sessions`). Expected: empty session list shows `No sessions in this repo` heading + `Run voss do "<task>" to create one.` body.
       c. With no active spawn, the side panel is collapsed to 0 columns (no placeholder copy visible).
    3. Help overlay reachable (Acceptance Visual Check 9):
       a. From the main pane (or input bar — `?` is global), press `?`. Expected: HelpOverlay opens with heading `voss tui · keys + commands`, lists every keybinding and every visible slash command. Press `Esc`. Expected: overlay dismisses.
    4. Sanity check on a real model:
       a. `voss do --plain "summarize this repo"` — output should look identical to pre-M9 plain stream.
       b. `voss chat` (TUI), type `/help`, press Enter — slash should dispatch through the registry, output appears in main pane.
       c. (Optional) `voss chat`, type `summarize this repo`, observe the live BudgetMeter and ConfidenceBar render at each step.
  </how-to-verify>
  <resume-signal>
    Type one of:
    - `approved` — Acceptance Visual Checks 1, 8, 9 all confirmed; phase complete.
    - `gap: <description>` — A specific check failed; describe what you saw vs UI-SPEC. The phase-checker will route this to a gap-closure plan.
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pre-M9 session JSON → new reader | malicious additional keys could attempt to set unexpected SessionRecord fields. |
| user terminal → fork_session | turn_index must be bounded. |
| modal Future → cli main loop | install_tui_permissions runs futures across the asyncio + Textual event loops. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M9-06-01 | Tampering | Crafted session JSON with extra keys to set credential-shaped fields | mitigate | `_hydrate` (session.py line 119) already filters to `_SESSION_FIELDS`. Adding parent_id/parent_turn_index does not add credential-shaped fields. Redaction test extended to cover both. |
| T-M9-06-02 | DoS | fork_session with turn_index >= len(turns) | mitigate | fork_session raises ValueError; ForkConfirmModal disables Enter when turn_index is out of range. |
| T-M9-06-03 | Confused-deputy | TUI permissions bridge bypass via mis-wiring | mitigate | install_tui_permissions only sets prompt_fn / scope_prompt_fn. mode_allows tier check (permissions.py:49) runs BEFORE prompt_fn regardless. Test verifies `mode="plan"` still denies fs_write even with TUI active. |
| T-M9-06-04 | Information disclosure | Forked sessions inherit cwd; running fork from outside the cwd | accept | fork_session preserves record.cwd; same property as resume. No new exposure. |
</threat_model>

<verification>
- All M9 tests green (~50 tests total across 6 plans).
- Full repo test suite green.
- Phase-final human-verify checkpoint approved.
- Accent allow-list, no-unicode fallback, Windows console strategy all automated gates.
- pre-M9 session JSON files roundtrip via new reader without loss.
</verification>

<success_criteria>
1. `voss chat` on a TTY ≥ 80×24 opens the Textual TUI by default.
2. `voss chat --plain` and piped invocations stay byte-identical to the M9-01 baseline.
3. `voss resume <old-session-id>` loads pre-M9 sessions without crash and shows them in the TUI.
4. Pressing `f` on a focused turn creates a forked SessionRecord with parent_id set.
5. install_tui_permissions wires DiffModal, PermissionModal, BudgetExhaustedModal into PermissionGate at all four interactive entry points.
6. test_accent_allowlist_audit, test_no_unicode_fallback, test_windows_console_strategy all green.
7. UI-SPEC Acceptance Visual Checks 1, 8, 9 confirmed by human-verify checkpoint.
</success_criteria>

<output>
After completion, create `.planning/phases/M9-tui-shell-tui-01/M9-06-SUMMARY.md` AND `.planning/phases/M9-tui-shell-tui-01/M9-PHASE-SUMMARY.md` (phase-level aggregate; lists which CONTEXT decisions and UI-SPEC checks landed, which were deferred to follow-up, and per-hunk surgical diff apply follow-up noted from M9-05).
</output>
