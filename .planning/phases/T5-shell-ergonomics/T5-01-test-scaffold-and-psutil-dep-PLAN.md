---
phase: T5-shell-ergonomics
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/harness/test_t5_shell.py
  - tests/harness/fixtures/emit.py
  - tests/harness/test_shell_timeout.py
  - voss/harness/lifecycle.py
  - pyproject.toml
autonomous: false
requirements: [SHELL-01, SHELL-02, SHELL-03, SHELL-04, SHELL-05]
user_setup: []

must_haves:
  truths:
    - "The full T5 test surface exists as failing stubs before any production code is written (Nyquist)"
    - "psutil is a declared runtime dependency, eyeballed by a human before it lands"
    - "lifecycle.reset_for_tests() clears _JOBS so background-job state never leaks across tests"
    - "A source-inspection guard fails the moment the SHELL-01 cap regresses below 30720"
  artifacts:
    - path: "tests/harness/test_t5_shell.py"
      provides: "Failing test stubs for SHELL-01..05 + SC#1/#2/#3"
      contains: "def test_background_returns_handle"
    - path: "tests/harness/fixtures/emit.py"
      provides: "Deterministic bounded line emitter for pump/monitor tests"
      contains: "sys.stdout.flush"
    - path: "pyproject.toml"
      provides: "psutil runtime dependency declaration"
      contains: "psutil>=5.9,<8"
  key_links:
    - from: "tests/harness/test_t5_shell.py"
      to: "voss.harness.lifecycle.reset_for_tests"
      via: "autouse fixture"
      pattern: "reset_for_tests"
    - from: "voss/harness/lifecycle.py"
      to: "_JOBS"
      via: "reset_for_tests clears the registry"
      pattern: "_JOBS"
---

<objective>
Lay the Wave-0 foundation for T5: create the full failing test surface, the deterministic emitter fixture, the `_JOBS` registry declaration plus its `reset_for_tests` extension, the SHELL-01 source-inspection regression guard, and add `psutil` as a runtime dependency behind a blocking human-verify checkpoint (D-10; slopcheck unavailable at research time).

Purpose: Every downstream T5 task asserts against tests authored here. Nyquist compliance requires the tests exist (red) before production code. The `psutil` dependency must be eyeballed by a human before it lands (legitimacy audit tagged it `[ASSUMED]`).
Output: `tests/harness/test_t5_shell.py` (new, all-red), `tests/harness/fixtures/emit.py` (new), extended `tests/harness/test_shell_timeout.py`, `_JOBS` declaration + `reset_for_tests` extension in `lifecycle.py`, `psutil>=5.9,<8` in `pyproject.toml`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T5-shell-ergonomics/T5-CONTEXT.md
@.planning/phases/T5-shell-ergonomics/T5-VALIDATION.md
@.planning/phases/T5-shell-ergonomics/T5-PATTERNS.md

<interfaces>
<!-- Contracts the test stubs assert against. Authored here, implemented in T5-02..05. -->

JobRecord schema (D-01/D-11, sidecar IS the JobRecord serialized) — implemented in T5-03:
  fields: handle: str, pid: int, started_at: str, cmd: str, log_path: str,
          status: str ("running"|"done"|"killed"), exit_code: int | None,
          runtime_ms: int
  handle format: "bg-NNN" (monotonic per session, zero-padded to 3, e.g. "bg-001")

Tool envelopes (string returns):
  shell_run_background(cmd) -> "bg-NNN"  (PID NEVER in the string — D-01)
  shell_monitor(handle, since_ms=0) -> "[cursor N][running|exit M]\n<chunk>"
                truncation suffix: "<truncated, N more bytes — re-monitor with cursor M>"
  shell_signal(handle, signal) -> ack string OR "<denied: unsupported signal>"

lifecycle (implemented T5-03/T5-04):
  _JOBS: dict[str, JobRecord]                      # declared in THIS plan
  register_job(...) -> str                         # mints bg-NNN, T5-03
  reap_jobs() -> None                              # SIGTERM@0 → SIGKILL@5s, T5-03
  signal_job(handle, sig) -> bool                  # T5-04

cli (implemented T5-05):
  jobs_cmd  (click command "jobs", --json flag)    # reads *.meta.json sidecars
</interfaces>

<existing_patterns>
Autouse reset fixture — tests/harness/test_lifecycle.py:14-18:
```python
@pytest.fixture(autouse=True)
def _reset_registries():
    lifecycle.reset_for_tests()
    yield
    lifecycle.reset_for_tests()
```

Deterministic subprocess test precedents — tests/harness/test_lifecycle.py:21-25, 36-58:
  `_PYTHON_BIN = shutil.which("python3") or shutil.which("python")`
  `@pytest.mark.skipif(_PYTHON_BIN is None, reason="...")`
  SIG_IGN-SIGTERM child + `time.monotonic()` elapsed bounds `assert 4.5 <= elapsed <= 6.5`.

Short-timeout shim — tests/harness/test_shell_timeout.py:25 (`timeout: float = 0.3`, never the real 30s).

Source-inspection guard — tests/harness/test_shell_timeout.py:116-128:
```python
@pytest.mark.slow
def test_real_shell_run_timeout_contract_documented(tmp_path):
    src = inspect.getsource(tools_mod.make_toolset)
    assert "timeout=30.0" in src, "..."
```

lifecycle registry decl + reset — voss/harness/lifecycle.py:24-27, 75-77:
```python
_SUBPROCESSES: list[asyncio.subprocess.Process] = []
_SESSIONS: list[object] = []
_TERM_DEADLINE_S = 5.0
...
def reset_for_tests() -> None:
    _SUBPROCESSES.clear()
    _SESSIONS.clear()
```

pyproject deps list — pyproject.toml:10-23 `[project] dependencies` (ends `"keyring>=24.0",`).
pytest markers available — pyproject.toml:67-71 (`slow`, `live`, `acceptance`; NO `t5` marker — use `slow` for the source-inspection guard).
</existing_patterns>
</context>

<tasks>

<task type="checkpoint:human-verify" gate="blocking-human">
  <name>Task 1: psutil dependency legitimacy verification (D-10, BLOCKING)</name>
  <action>STOP. Do not run any command. This is a blocking human-verify legitimacy gate (not auto-approvable — workflow.auto_advance is ignored for package-legitimacy gates). Present the verification steps below to the user and wait for an explicit "approved" before Task 2 adds the psutil pin. No code is written in this task.</action>
  <what-built>Nothing yet — this checkpoint gates the psutil dependency addition in Task 2. RESEARCH §Package Legitimacy Audit tagged psutil `[ASSUMED]` because slopcheck was unavailable at research time. Per the package-legitimacy protocol a human must eyeball the dependency before it lands. This checkpoint is NOT auto-approvable (workflow.auto_advance is ignored for legitimacy gates).</what-built>
  <how-to-verify>
    1. Open https://pypi.org/project/psutil/ in a browser.
    2. Confirm: maintainer is `giampaolo` (Giampaolo Rodola); source repo is `github.com/giampaolo/psutil`; a recent release exists (latest at research time was 7.2.2); ~352M downloads/month; ~16-year history.
    3. Confirm there are no postinstall scripts (psutil is a pure C-extension build).
    4. The pin to be added is exactly: `"psutil>=5.9,<8",` (wide compatible band; `memory_info().rss` API stable since 1.x).
    This is a single-line eyeball confirmation — RESEARCH explicitly states no extended investigation is warranted for this top-100 PyPI package.
  </how-to-verify>
  <resume-signal>Type "approved" to allow Task 2 to add the psutil pin, or describe blocking concerns.</resume-signal>
</task>

<task type="auto">
  <name>Task 2: Add psutil runtime dependency + extend lifecycle _JOBS registry + reset</name>
  <files>pyproject.toml, voss/harness/lifecycle.py</files>
  <action>
    In pyproject.toml `[project] dependencies` (the list ending `"keyring>=24.0",` around pyproject.toml:10-23), append one line: `"psutil>=5.9,<8",`. Per RESEARCH §Installation this goes in `[project] dependencies`, NOT `optional-dependencies.search` or `dev` — it is required for SC#3 on all platforms. Do not touch any other dependency.

    In voss/harness/lifecycle.py: (a) beside the existing module-level registry declarations at lifecycle.py:24-27 (`_SUBPROCESSES`, `_SESSIONS`, `_TERM_DEADLINE_S`), add `_JOBS: dict[str, "JobRecord"] = {}` as a forward-referenced declaration (the `JobRecord` dataclass itself lands in T5-03 — use a string annotation so this plan does not require it). Add a module-level comment noting `_JOBS` is a deliberately SEPARATE registry from `_SUBPROCESSES` (distinct reap semantics: watchdog timers, mid-life signals, may exceed the 5s deadline — CONTEXT anti-pattern + RESEARCH Alternatives). Do NOT add JobRecord, register_job, reap_jobs, or the supervisor task here — only the empty registry dict + comment. (b) Extend `reset_for_tests()` (lifecycle.py:75-77) to also `_JOBS.clear()`. Add an inline note that T5-03 will additionally cancel any live supervisor tasks here. Do NOT modify `reap_all`, `_atexit_hook`, `register_subprocess`, or `register_session` in this plan (those are extended in T5-03).

    Run `pip install -e '.[dev]'` (or `pip install 'psutil>=5.9,<8'`) so `import psutil` resolves for the test module authored in Task 3.
  </action>
  <verify>
    <automated>python -c "import psutil; print(psutil.__version__)" && python -c "from voss.harness import lifecycle; lifecycle.reset_for_tests(); assert lifecycle._JOBS == {}, lifecycle._JOBS; print('jobs-registry-ok')"</automated>
    <requirement>SHELL-02 (registry foundation), SC#3 (psutil availability)</requirement>
    <expected>psutil imports and reports a version in [5.9, 8); lifecycle._JOBS exists and is cleared to {} by reset_for_tests.</expected>
  </verify>
  <done>`psutil>=5.9,<8` is in `[project] dependencies`; `import psutil` succeeds; `lifecycle._JOBS` is a module-level dict cleared by `reset_for_tests()`; no other lifecycle function changed.</done>
</task>

<task type="auto">
  <name>Task 3: Author failing T5 test surface + deterministic emitter + SHELL-01 source guard</name>
  <files>tests/harness/test_t5_shell.py, tests/harness/fixtures/emit.py, tests/harness/test_shell_timeout.py</files>
  <action>
    Create `tests/harness/fixtures/emit.py`: a tiny standalone script invoked as `sys.executable, str(fixtures_dir/"emit.py"), "<N>"`. It prints N lines (`line {i}`) each followed by `sys.stdout.flush()` and `time.sleep(0.05)`, then exits 0. Bounded, line-counted, deterministic. Mirror the inline `-c` precedent at test_lifecycle.py:38-44 (write + flush + sleep). Keep it allowlist-clean (`python3` is in sandbox.py DEFAULT_SHELL_ALLOWLIST) though tests typically bypass the gate.

    Create `tests/harness/test_t5_shell.py` with an autouse `_reset_registries` fixture copied from test_lifecycle.py:14-18 (calls the now-`_JOBS`-clearing `lifecycle.reset_for_tests()`). Add `_PYTHON_BIN = shutil.which("python3") or shutil.which("python")` and `@pytest.mark.skipif(_PYTHON_BIN is None, ...)` on integration tests. Write ALL of the following as FAILING stubs (each body `raise NotImplementedError` or an assertion that cannot pass until the implementation exists — they MUST be red now and turn green in later waves, never xfail/skip-by-default):
      - `test_shell_run_30kb_truncation` (SHELL-01) — output >30KB truncates with `<truncated, total N bytes>`.
      - `test_background_returns_handle` (SHELL-02) — returns `bg-001`; assert NO PID digits leak in the result string.
      - `test_handle_counter` (SHELL-02) — counter monotonic + zero-padded across spawns in one session.
      - `test_monitor_cursor_progression` (SHELL-03) — `[cursor N][running]\n<chunk>` then `[exit M]` after EOF; cursor round-trips (pass returned N back as `since_ms`); uses the emit.py fixture.
      - `test_monitor_across_turns` (SHELL-03 / SC#1) — a job observable from a second `shell_monitor` call (short emitter, NEVER a real 20s sleep).
      - `test_signal_surface` (SHELL-04) — `INT`/`TERM` accepted; `KILL` and unknown → `<denied: unsupported signal>`.
      - `test_signal_terminates` (SHELL-04) — POSIX-only `@pytest.mark.skipif(os.name != "posix", ...)`; SIGTERM delivered, job exits.
      - `test_voss_jobs_reads_sidecar` (SHELL-05) — pre-seed `tmp_path/.voss-cache/jobs/<sid>/bg-001.meta.json` + `.active-session` pointer; `click.testing.CliRunner().invoke(jobs_cmd, [...])` renders the table and `--json`. (Import `jobs_cmd` lazily inside the test so this module imports cleanly before T5-05 lands — use `pytest.importorskip`-style guard or a local import wrapped so the stub is RED, not a collection error.)
      - `test_reap_jobs_escalation` (SC#2) — SIG_IGN-SIGTERM child (test_lifecycle.py:38-44 pattern) + `time.monotonic()` bounds asserting SIGTERM≈t0 and SIGKILL by ~5s.
      - `test_no_output_watchdog` (SC#3) — inject a SMALL `no_output_deadline_s` (e.g. 0.3), never 30s; assert kill + `shell.background.reap` with `reason="watchdog_no_output"`.
      - `test_rss_watchdog` (SC#3) — monkeypatch the tree-RSS probe to return a synthetic >100MB int; NEVER allocate real memory; assert kill + `reason="watchdog_mem"`.
      - `test_edit_mode_denies_background_and_signal` (D-12) — `mode_allows("edit", "shell_run_background", True)` and `mode_allows("edit", "shell_signal", True)` both deny; `mode_allows("edit", "shell_monitor", False)` stays allowed.
    Where a stub references an as-yet-unimplemented symbol, guard the import so the FUNCTION fails (red) rather than the MODULE failing to collect — collection must succeed so `pytest --co` lists every test.

    Extend `tests/harness/test_shell_timeout.py`: add a sibling `@pytest.mark.slow` source-inspection test (mirror `test_real_shell_run_timeout_contract_documented` at :116-128) asserting `"30720" in inspect.getsource(tools_mod.make_toolset)` — guards SHELL-01 against silent regression exactly like the existing `timeout=30.0` guard. Do not modify the existing test.
  </action>
  <verify>
    <automated>python -m pytest tests/harness/test_t5_shell.py --co -q && python -m pytest tests/harness/test_t5_shell.py -q --no-header 2>&1 | tail -3</automated>
    <requirement>SHELL-01..05, SC#1/#2/#3 (test surface exists, all red)</requirement>
    <expected>`pytest --co` collects all ~12 T5 stubs with zero collection errors; running them shows all failing (red) — none pass, none are skip-by-default. emit.py exists and is executable as a script.</expected>
  </verify>
  <done>`tests/harness/test_t5_shell.py` collects cleanly and every stub is RED; `tests/harness/fixtures/emit.py` prints N lines with flush+sleep; `test_shell_timeout.py` has a new failing `30720` source guard (red until T5-02); the `30720`-not-yet-present source guard fails for the right reason.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| PyPI → build env | New third-party dependency (`psutil`) enters the supply chain |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T5-SC | Tampering | `psutil` pip install (supply chain) | mitigate | Blocking `checkpoint:human-verify` (Task 1) before the pin lands; pinned band `>=5.9,<8`; top-100 PyPI, 16-yr history, no postinstall scripts (RESEARCH legitimacy audit). Never auto-approvable. |
| T-T5-01 | Tampering | SHELL-01 cap constant | mitigate | Source-inspection regression guard (`assert "30720" in src`) added in Task 3 so the cap cannot silently regress. |
</threat_model>

<verification>
- `pytest tests/harness/test_t5_shell.py --co -q` collects every stub, zero errors.
- All T5 stubs RED (no implementation yet) — Nyquist precondition satisfied.
- `import psutil` resolves; `lifecycle._JOBS` exists + cleared by `reset_for_tests()`.
- `pytest tests/harness/test_shell_timeout.py -k cap -q` runs (the new `30720` guard is RED until T5-02 raises the cap).
</verification>

<success_criteria>
- psutil legitimacy human-verify checkpoint approved before the pin landed.
- `psutil>=5.9,<8` in `[project] dependencies`; importable.
- Full T5 failing test surface exists and collects.
- `lifecycle._JOBS` declared + cleared by `reset_for_tests`; no other lifecycle function touched.
- SHELL-01 `30720` source guard exists (RED until T5-02).
</success_criteria>

<output>
Create `.planning/phases/T5-shell-ergonomics/T5-01-SUMMARY.md` when done.
</output>
