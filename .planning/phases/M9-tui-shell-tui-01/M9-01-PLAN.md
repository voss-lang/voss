---
phase: M9
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - voss/harness/tui/__init__.py
  - voss/harness/tui/capability.py
  - voss/harness/render.py
  - voss/harness/cli.py
  - tests/harness/tui/__init__.py
  - tests/harness/tui/test_capability_and_plain_fallback.py
  - tests/harness/tui/baseline/plain_baseline.txt
  - tests/harness/tui/test_plain_parity.py
autonomous: false
requirements: [TUI-01, TUI-10]
must_haves:
  truths:
    - "Textual is a declared dependency, pinned with a version range."
    - "`--plain` flag is recognized by voss chat / voss do / voss resume / voss edit."
    - "When stdout is not a TTY, the harness uses PlainRenderer with zero TUI bootstrap cost."
    - "When VOSS_PLAIN=1 is set, the harness uses PlainRenderer regardless of TTY state."
    - "Stdout byte-output for `voss do` on a canned task is byte-identical to the captured baseline, and the capture itself is deterministic (locked FakeProvider, locked cwd, locked env)."
    - "If terminal is below 80x24, voss exits 2 with the locked stderr message."
    - "Baseline file is idempotent: first run with no baseline writes it; subsequent runs compare bytes; never overwrites silently."
  artifacts:
    - path: "voss/harness/tui/capability.py"
      provides: "tui_available(), tui_should_activate(argv,env,stdin,stdout,size), min_size_guard()"
      exports: ["tui_available", "tui_should_activate", "TUIDecision", "min_size_guard"]
    - path: "voss/harness/tui/__init__.py"
      provides: "TUI subpackage entry point"
    - path: "tests/harness/tui/test_capability_and_plain_fallback.py"
      provides: "Capability + --plain + VOSS_PLAIN + non-TTY auto-fallback + min-size guard tests"
    - path: "tests/harness/tui/baseline/plain_baseline.txt"
      provides: "Locked-FakeProvider stdout byte baseline for parity diff"
    - path: "tests/harness/tui/test_plain_parity.py"
      provides: "Stdout byte-diff acceptance gate; idempotent capture step (writes baseline only if absent)"
  key_links:
    - from: "voss/harness/cli.py"
      to: "voss/harness/tui/capability.py"
      via: "tui_should_activate() called before make_renderer()"
      pattern: "tui_should_activate"
    - from: "voss/harness/render.py:make_renderer"
      to: "voss/harness/tui/capability.py"
      via: "make_renderer gains plain=bool, force_tui=bool kwargs"
      pattern: "def make_renderer"
---

<objective>
Foundation wave: lock the library choice (Textual), add it as a versioned dependency, scaffold the `voss/harness/tui/` subpackage, add a `--plain` flag + non-TTY auto-fallback + `VOSS_PLAIN=1` env override on all four interactive CLI commands, lock the 80x24 minimum-size guard, and freeze a pre-M9 stdout byte baseline so every subsequent plan can verify it has not regressed `--plain` parity. Baseline capture uses a locked FakeProvider (the one already in `tests/harness/test_voss_loop_parity.py`) and is idempotent.

Purpose: TUI-10 (headless byte-parity + Windows fallback contract) and TUI-01 (library choice) are the only items every other plan in this phase depends on. They land first, in one plan, so Wave 2+ never has to re-litigate the library choice or re-baseline parity.

Output: pyproject dep, capability module, --plain plumbing, a captured stdout baseline, and an automated parity test.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md
@.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md
@voss/harness/render.py
@voss/harness/cli.py
@pyproject.toml
@tests/harness/test_voss_loop_parity.py

<interfaces>
<!-- Renderer protocol the TUI must implement (extracted from voss/harness/render.py). -->
<!-- Executor must NOT change this protocol shape — adding a method here would force editing every existing Renderer. -->

From voss/harness/render.py (lines 24-44):
```python
class Renderer(Protocol):
    def banner(self, *, model: str, cwd: Path, git_status: str) -> None: ...
    def show_user(self, task: str) -> None: ...
    def show_thinking(self, label: str) -> None: ...
    def show_plan(self, plan: Any, *, cost_usd: float) -> None: ...
    def show_tool_call(self, name: str, args: dict, summary: str, state: str) -> None: ...
    def show_clarify(self, question: str, confidence: float) -> None: ...
    def show_final(self, text: str, *, confidence: float, cost_usd: float) -> None: ...
    def status(self, *, model: str, tokens: int, cost_usd: float, ctx_pct: float) -> None: ...
    def show_cognition(self, *, architecture_tokens: int, constraints_count: int,
                       plans_loaded: int = 0, decisions_loaded: int = 0) -> None: ...
    def show_cognition_overflow(self, *, architecture_tokens: int, budget: int = 6000) -> None: ...
    def show_warning(self, msg: str) -> None: ...
```

Existing factory (voss/harness/render.py:47):
```python
def make_renderer(*, json_mode: bool) -> Renderer:
    if json_mode or not sys.stdout.isatty():
        return JsonRenderer() if json_mode else PlainRenderer()
    return TtyRenderer()
```

CLI commands that call make_renderer (voss/harness/cli.py): `do_cmd` (line 511), `chat_cmd` (599 via _run_repl), `edit_cmd` (647 via _run_repl), `resume_cmd` (955 via _run_repl), `_run_repl` (688). All FIVE call sites accept `--json` already; `--plain` is added in this plan symmetrically.

Locked stub provider for baseline determinism (from tests/harness/test_voss_loop_parity.py line 18):
```python
class FakeProvider:
    """Returns a canned sequence of agent steps. Already used by parity tests across the repo."""
    def __init__(self, plan): self.plan = plan; self._i = 0
    def __call__(self, *args, **kwargs): step = self.plan[self._i]; self._i += 1; return step
```
This plan's baseline test imports and reuses `FakeProvider` from `tests/harness/test_voss_loop_parity.py` — does NOT define a new fake. This guarantees the baseline byte-stream is reproducible from the same source class every other parity test in the repo uses.
</interfaces>
</context>

<tasks>

<task type="checkpoint:decision" gate="blocking">
  <name>Task 0: Library-choice decision gate (TUI-01)</name>
  <decision>Confirm Textual as the TUI library for M9, or choose prompt_toolkit.</decision>
  <context>
    UI-SPEC declares Textual the "strong default" and the locked design system (region grid, glyphs, color allow-list, modal overlays, slash palette popup, 256-color + truecolor target) is library-agnostic. CONTEXT.md gives the planner discretion only if Textual fails the Windows-console gate.
    Evidence already in hand from UI-SPEC + CONTEXT:
      - Textual supports asyncio streaming, modal overlays, ScrollView, ListView, Input, Static — all listed in the Registry Safety table.
      - Project is Python 3.11+ (pyproject.toml line 9). Textual requires Python 3.8+, supports Windows console via prompt_toolkit-style backend.
      - Vendored Python 3.12 from M6 is the production target — Textual is pure Python (no native ext.).
      - License: MIT (Textualize/textual). Cleared by UI-SPEC Registry Safety table (rejects GPL only).
    Failure mode that would force prompt_toolkit: Textual cannot render on the M6-vendored Windows console at all. UI-SPEC item 9 of Acceptance Visual Checks explicitly allows the "Windows console limitation hit" fallback path.
  </context>
  <options>
    <option id="textual">
      <name>Textual (UI-SPEC default)</name>
      <pros>Region grid, modal overlays, scrollable panes, 256/truecolor, css-ish styling all first-class. Asyncio-native — composes with `asyncio.run(run_turn(...))` in cli.py:563. Pure-Python.</pros>
      <cons>~5 MB install footprint. Windows console rendering of full-screen mode has historical edge cases (UI-SPEC pre-locks copy for this fallback).</cons>
    </option>
    <option id="prompt_toolkit">
      <name>prompt_toolkit (UI-SPEC fallback only)</name>
      <pros>Lighter, longer Windows track record.</pros>
      <cons>No native concept of modal overlays or scrollable history pane — every UI-SPEC widget would have to be hand-composed. UI-SPEC region grid + DiffModal + PermissionModal + SubAgentPanel would each be 3-5x more code. Loses 80% of UI-SPEC's "library-agnostic" claim.</cons>
    </option>
  </options>
  <resume-signal>Select: textual or prompt_toolkit. Default per UI-SPEC if no objection: textual.</resume-signal>
</task>

<task type="auto" tdd="true">
  <name>Task 1: Add Textual dep, scaffold voss/harness/tui/ subpackage, write capability module</name>
  <files>pyproject.toml, voss/harness/tui/__init__.py, voss/harness/tui/capability.py, tests/harness/tui/__init__.py, tests/harness/tui/test_capability_and_plain_fallback.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/pyproject.toml (lines 1-55, current dependencies list — add textual here, not in optional-deps; TUI is the default product surface per ROADMAP M9, not opt-in)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/render.py (lines 1-50, make_renderer factory signature + Renderer protocol; this plan does NOT change Renderer protocol — only adds a capability shim alongside it)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md ("Min terminal size" row + "--plain auto-fallback notice" + "Min-size guard" copy strings — verbatim required)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md ("Headless fallback" section — auto-detect non-TTY rule + VOSS_PLAIN env)
  </read_first>
  <behavior>
    - Test: tui_available() returns True when textual import succeeds (this run's environment).
    - Test: tui_should_activate(argv=["--plain"]) returns TUIDecision(activate=False, reason="--plain flag").
    - Test: tui_should_activate(env={"VOSS_PLAIN": "1"}) returns TUIDecision(activate=False, reason="VOSS_PLAIN env").
    - Test: tui_should_activate(stdout_isatty=False) returns TUIDecision(activate=False, reason="non-TTY stdout").
    - Test: tui_should_activate(json_mode=True) returns TUIDecision(activate=False, reason="--json mode").
    - Test: tui_should_activate(size=(79, 24)) returns TUIDecision(activate=False, reason="terminal below 80x24"), AND tui_should_activate(size=(80, 23)) likewise False.
    - Test: tui_should_activate(stdout_isatty=True, size=(80,24), argv=[], env={}, json_mode=False) returns TUIDecision(activate=True, reason="ok") when tui_available() True.
    - Test: min_size_guard((79,24)) returns the exact stderr string from UI-SPEC: `voss: terminal must be at least 80×24 (current: 79×24). Resize or use --plain.` (note the locked × glyph, not x).
    - Test: importing voss.harness.tui.capability does NOT import textual at module top level (deferred import inside tui_available); confirmed by patching sys.modules and asserting capability still imports.
  </behavior>
  <action>
    Per Task 0 D-decision (Textual default per UI-SPEC), add `textual>=0.58,<1.0` to pyproject.toml `[project] dependencies` (NOT optional-dependencies — TUI is the default product surface, not opt-in). Order it alphabetically after `rich`.

    Create `voss/harness/tui/__init__.py` (empty docstring only — actual app lands in M9-02; this plan ships the subpackage stub).

    Create `voss/harness/tui/capability.py`:
      - `@dataclass(frozen=True) class TUIDecision: activate: bool; reason: str`
      - `def tui_available() -> bool` — deferred `import textual` inside a try/except ImportError; returns True iff import succeeds. Cached in module-level `_AVAILABLE: Optional[bool] = None`.
      - `def tui_should_activate(*, argv: list[str] | None = None, env: dict[str, str] | None = None, stdout_isatty: bool | None = None, json_mode: bool = False, size: tuple[int, int] | None = None) -> TUIDecision`. Each kwarg defaults to live system values (`sys.argv[1:]`, `os.environ`, `sys.stdout.isatty()`, `shutil.get_terminal_size()`) when None — pure dependency injection so tests pass synthetic values.
      - Decision order (first match wins; reason string must exactly match the test expectations above): 1) `--plain` in argv → False, 2) `VOSS_PLAIN=1` in env → False, 3) `json_mode=True` → False, 4) stdout not a TTY → False, 5) size < (80,24) → False, 6) tui_available() False → False reason "textual not installed", 7) else activate=True reason "ok".
      - `def min_size_guard(size: tuple[int, int]) -> str` — return EXACTLY the UI-SPEC string. Use `×` (U+00D7), NOT `x`. Use locked format: `f"voss: terminal must be at least 80×24 (current: {size[0]}×{size[1]}). Resize or use --plain."`.

    Create `tests/harness/tui/__init__.py` (empty). Create `tests/harness/tui/test_capability_and_plain_fallback.py` with the 8 tests above. Use pytest-style; no fixtures needed beyond `monkeypatch` for env/argv.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pip install -e . --quiet 2>&1 | tail -5 && pytest tests/harness/tui/test_capability_and_plain_fallback.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "import textual; print(textual.__version__)"` exits 0 (dep installed).
    - `python -c "from voss.harness.tui.capability import tui_available, tui_should_activate, min_size_guard, TUIDecision; print('ok')"` prints `ok`.
    - All 8 behavior tests pass.
    - `grep -v '^#' voss/harness/tui/capability.py | grep -c "^import textual"` returns 0 (no top-level textual import; deferred inside function body).
    - `grep -c "textual>=0.58" pyproject.toml` returns >= 1 (dep in `[project] dependencies` list, properly formatted).
  </acceptance_criteria>
  <done>TUIDecision dataclass + 3 functions exported from `voss.harness.tui.capability`. textual is an installable dep. Capability module has zero textual import at top level so PlainRenderer path pays no Textual import cost.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire --plain flag + auto-fallback + min-size guard into CLI, capture pre-M9 stdout baseline with locked FakeProvider (idempotent), lock parity test</name>
  <files>voss/harness/render.py, voss/harness/cli.py, tests/harness/tui/baseline/plain_baseline.txt, tests/harness/tui/test_plain_parity.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/render.py (lines 47-51, make_renderer factory — extend its signature, do not replace it)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cli.py (lines 496-510 for do_cmd options, 582-598 for chat_cmd, 633-647 for edit_cmd, 947-960 for resume_cmd — add `--plain` flag option block to each, mirror the existing `--json` placement exactly)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cli.py (lines 538, 614, 678, 974 — call sites that pass json_mode to _run_repl or to make_renderer; add plain= alongside)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cli.py (lines 688-705, _run_repl signature — accept plain bool, call capability.tui_should_activate, route to PlainRenderer if False or to TtyRenderer if True for THIS plan; TextualRenderer lands in M9-02)
    - /Users/benjaminmarks/Projects/Voss/tests/harness/test_voss_loop_parity.py (lines 18-67 — the FakeProvider class this plan reuses verbatim for the baseline; do NOT define a new one)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md ("Headless / `--plain` Contract" table — Stdout shape row, Auto-detect rule row, Verification row)
  </read_first>
  <behavior>
    - Test: `CliRunner().invoke(do_cmd, ["--plain", "what is 2+2"])` with `_resolve_auth_or_die` monkeypatched to return `FakeProvider` (imported from tests/harness/test_voss_loop_parity.py) seeded with a fixed canned plan, fixed `cwd=tmp_path`, fixed env `{"VOSS_BASELINE":"1"}`, produces stdout byte-stream that matches `tests/harness/tui/baseline/plain_baseline.txt` exactly.
    - Test (idempotent capture): when `plain_baseline.txt` does NOT exist on disk AND env `VOSS_CAPTURE_BASELINE=1` is set, the test writes the file from the current run output then skips. When the file DOES exist, the env flag is IGNORED — the test always compares bytes. This prevents accidental baseline overwrites.
    - Test: `do_cmd` invoked without `--plain` but with `stdout_isatty=False` (CliRunner default) produces identical stdout to the `--plain` invocation (auto-fallback).
    - Test: `do_cmd --json` still produces NDJSON on stdout (json_mode short-circuits before plain logic — regression guard for existing JsonRenderer behavior).
    - Test: invoking any of `do_cmd`, `chat_cmd`, `edit_cmd`, `resume_cmd` with a 79-column terminal (monkeypatch `shutil.get_terminal_size` to (79,24)) AND `--plain` not set AND TTY True still proceeds (because TTY check + size check both block TUI activation → falls back to PlainRenderer, never reaches the min-size guard's exit-2 path).
    - Test: invoking with FORCE_TUI=1 + 79x24 size raises SystemExit(2) and stderr contains the min_size_guard string. (FORCE_TUI is the developer escape hatch used by M9-02 acceptance tests.)
  </behavior>
  <action>
    Extend `make_renderer` in `voss/harness/render.py`:
      - New signature: `def make_renderer(*, json_mode: bool, plain: bool = False, force_tui: bool = False) -> Renderer:`
      - Body: if `json_mode`: return `JsonRenderer()`. Else import `from .tui.capability import tui_should_activate` and call it with `argv=sys.argv[1:]`, `json_mode=False`, plain forwarded (when plain=True the decision is forced False regardless of env). If `force_tui` is True AND decision says False due to size: re-run min_size_guard, write to stderr, `sys.exit(2)`. Otherwise: if decision.activate AND force_tui-or-otherwise-ok: return a stub TextualRenderer (in THIS plan, raise NotImplementedError("TextualRenderer lands in M9-02"); behavior shipped means flag plumbing works without the renderer existing yet). Else return `TtyRenderer()` if `sys.stdout.isatty()` else `PlainRenderer()`. NOTE: keep current TtyRenderer path live for this wave — TUI swap-in happens in M9-07 wire-up. For M9-01 the only behavior change visible to users is: `--plain` forces PlainRenderer, `VOSS_PLAIN=1` forces PlainRenderer.

    Add `@click.option("--plain", "plain", is_flag=True, help="Use line-streamed renderer; bypass TUI.")` to `do_cmd` (after the existing `--json` option line ~496), `chat_cmd` (after line ~585), `edit_cmd` (after line ~633), `resume_cmd` (after line ~947). Thread `plain` through to `make_renderer(json_mode=json_mode, plain=plain)` and to `_run_repl(plain=plain, ...)`. Extend `_run_repl` signature with `plain: bool = False` and pass through.

    Idempotent baseline capture: `tests/harness/tui/test_plain_parity.py` contains a fixture/helper `_baseline_path() -> Path` and the parity test:
      ```python
      def test_plain_baseline_parity(tmp_path, monkeypatch):
          from tests.harness.test_voss_loop_parity import FakeProvider
          CANNED_PLAN = [...]  # locked literal in the test file; 3-5 steps producing one final answer
          monkeypatch.setattr("voss.harness.cli._resolve_auth_or_die",
                              lambda *_a, **_kw: FakeProvider(CANNED_PLAN))
          monkeypatch.chdir(tmp_path)
          monkeypatch.setenv("VOSS_BASELINE", "1")  # marker only; no behavior dep
          result = CliRunner().invoke(do_cmd, ["--plain", "echo plan-baseline"])
          baseline = _baseline_path()
          if not baseline.exists():
              if os.environ.get("VOSS_CAPTURE_BASELINE") == "1":
                  baseline.parent.mkdir(parents=True, exist_ok=True)
                  baseline.write_bytes(result.stdout_bytes)
                  pytest.skip(f"wrote baseline: {baseline}")
              pytest.fail(f"baseline missing at {baseline}; rerun with VOSS_CAPTURE_BASELINE=1")
          assert result.stdout_bytes == baseline.read_bytes(), "stdout drift vs locked baseline"
      ```
      Key properties: (a) FakeProvider is the existing class — single source of truth; (b) tmp_path eliminates cwd-dependent strings; (c) the env marker `VOSS_BASELINE=1` is a no-op flag the test can grep for in stdout to confirm the env path went through, NOT a behavior switch; (d) when the baseline exists, `VOSS_CAPTURE_BASELINE` is ignored — bytes are always compared; (e) the first developer to run the test with `VOSS_CAPTURE_BASELINE=1` writes the file and commits it; subsequent runs are pure comparisons.

    Add the other 4 tests (auto-fallback, --json regression, 79-col with no force_tui, FORCE_TUI exit-2) to the same file.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && VOSS_CAPTURE_BASELINE=1 pytest tests/harness/tui/test_plain_parity.py::test_plain_baseline_parity -q 2>/dev/null || true ; pytest tests/harness/tui/test_plain_parity.py tests/harness/tui/test_capability_and_plain_fallback.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -v '^#' voss/harness/cli.py | grep -c 'is_flag=True, help="Use line-streamed renderer'` returns >= 4 (one per interactive command).
    - `grep -v '^#' voss/harness/cli.py | grep -c "plain: bool = False"` returns >= 1 (_run_repl signature accepts plain).
    - `wc -c tests/harness/tui/baseline/plain_baseline.txt` returns > 0 (baseline captured, not empty).
    - `grep -c "from tests.harness.test_voss_loop_parity import FakeProvider" tests/harness/tui/test_plain_parity.py` returns 1 (locked stub source).
    - `grep -c "VOSS_CAPTURE_BASELINE" tests/harness/tui/test_plain_parity.py` returns >= 2 (idempotent capture logic present).
    - All 5 parity tests pass and all 8 capability tests still pass.
    - Existing test suite green: `pytest tests/harness/test_cli.py tests/harness/test_happy_path_integration.py -x -q` — no regression in `--json` mode or in default TTY path (since TtyRenderer is still the live default in this wave).
    - `grep -v '^#' voss/harness/render.py | grep -c "class TextualRenderer"` returns 0 (M9-02 ships the real one).
  </acceptance_criteria>
  <done>--plain + VOSS_PLAIN + auto-non-TTY all route to PlainRenderer. Pre-M9 baseline bytes are checked in. test_plain_parity.py guards stdout bytes against regression. Every subsequent plan in M9 must keep this test green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user terminal → voss process | argv + env (VOSS_PLAIN, COLUMNS, LINES) crosses here. Strings are untrusted but never executed. |
| voss process → stdout/stderr | renderer output is shown to user; not consumed by another program except via pipes (which use --plain). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M9-01-01 | Tampering | VOSS_PLAIN env spoofing | accept | Env vars are user-controlled by definition — VOSS_PLAIN forcing PlainRenderer is the user's stated preference, not an attack. |
| T-M9-01-02 | Denial-of-service | Tiny-terminal exit-2 loop | mitigate | min_size_guard exits 2 ONCE, does not loop or retry. Pytest verifies single SystemExit raised. |
| T-M9-01-03 | Info disclosure | Baseline file leaks user paths | mitigate | Baseline test uses CliRunner with monkeypatched cwd=tmp_path. Stub provider is the locked FakeProvider with a canned literal plan. No PII paths can appear. |
| T-M9-01-04 | Spoofing | Forged `--plain` byte output hiding errors | accept | PlainRenderer already exists pre-M9; this plan only re-routes to it. Stderr stays uncovered. |
| T-M9-01-05 | Tampering | Baseline silently overwritten by accidental capture flag | mitigate | When baseline file exists, VOSS_CAPTURE_BASELINE is IGNORED; bytes are always compared. Writing requires both env flag AND no existing file. |
</threat_model>

<verification>
- Capability module + flag plumbing covered by 13 tests across two files.
- Baseline bytes committed; subsequent plans must keep parity test green.
- Baseline capture is deterministic: FakeProvider is imported from a single locked source, cwd is tmp_path, plan is a literal in the test file.
- Baseline capture is idempotent: existing file is never silently overwritten.
- pyproject.toml shows textual as a regular (not optional) dep.
</verification>

<success_criteria>
1. `pip install -e .` pulls textual successfully.
2. `voss do --plain "x"` and `voss do "x" | cat` produce byte-identical stdout to the committed baseline.
3. `voss chat --plain`, `voss edit <p> --plain`, `voss resume <id> --plain` all use PlainRenderer without bootstrapping any TUI module.
4. 79×24 terminal + FORCE_TUI=1 + no --plain exits 2 with the locked stderr string.
5. tui_available(), tui_should_activate(), TUIDecision, min_size_guard exported from voss.harness.tui.capability.
6. No other plan in M9 can land without keeping `test_plain_parity.py` green.
7. Baseline cannot be silently overwritten by a stray env flag.
</success_criteria>

<output>
After completion, create `.planning/phases/M9-tui-shell-tui-01/M9-01-SUMMARY.md`.
</output>
