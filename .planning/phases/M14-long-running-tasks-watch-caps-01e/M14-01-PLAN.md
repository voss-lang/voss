---
phase: M14-long-running-tasks-watch-caps-01e
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - tests/harness/test_m14_watch.py
  - .github/workflows/ci.yml
autonomous: false
requirements: [WATCH-01, WATCH-02, WATCH-03, WATCH-04, WATCH-05]
user_setup: []

must_haves:
  truths:
    - "watchdog>=4.0,<7 is importable in the dev environment after pip install -e .[dev]"
    - "All 10 WATCH tests in tests/harness/test_m14_watch.py collect and fail (RED) — none error on collection"
    - "reset_for_tests-based autouse fixture resets watcher state between tests"
    - "A daemon-PID cleanup fixture kills any spawned detached worker on teardown"
    - "CI runs the WATCH event tests on macos-latest in addition to ubuntu-latest"
  artifacts:
    - path: "tests/harness/test_m14_watch.py"
      provides: "10 RED WATCH-01..05 tests + _reset_registries autouse fixture + daemon-PID cleanup fixture"
      contains: "def test_debounce_coalesces_rapid_writes"
      min_lines: 120
    - path: "pyproject.toml"
      provides: "watchdog runtime + dev dependency pin"
      contains: "watchdog>=4.0,<7"
    - path: ".github/workflows/ci.yml"
      provides: "macos-latest in the WATCH test CI matrix"
      contains: "macos-latest"
  key_links:
    - from: "tests/harness/test_m14_watch.py"
      to: "voss.harness.lifecycle.reset_for_tests"
      via: "autouse fixture call"
      pattern: "lifecycle\\.reset_for_tests"
    - from: "pyproject.toml"
      to: "watchdog package"
      via: "pip install -e .[dev]"
      pattern: "watchdog>=4\\.0,<7"
---

<objective>
Wave 0 scaffold for phase M14: pin the `watchdog` dependency, stand up the 10 RED WATCH tests (the binding Nyquist validation contract from M14-VALIDATION.md), the watcher-reset autouse fixture, the daemon-PID cleanup fixture, and add `macos-latest` to the CI matrix for WATCH event tests (WATCH-05).

Purpose: Every subsequent M14 wave turns these RED tests GREEN. No production watch code is written here — this plan only proves the test/dep/CI infrastructure exists and fails for the right reason.
Output: `pyproject.toml` (watchdog pinned runtime + dev), `tests/harness/test_m14_watch.py` (10 collecting RED tests + fixtures), `.github/workflows/ci.yml` (macos-latest WATCH matrix).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M14-long-running-tasks-watch-caps-01e/M14-SPEC.md
@.planning/phases/M14-long-running-tasks-watch-caps-01e/M14-VALIDATION.md
@.planning/phases/M14-long-running-tasks-watch-caps-01e/M14-RESEARCH.md
@.planning/phases/M14-long-running-tasks-watch-caps-01e/M14-PATTERNS.md

<interfaces>
<!-- Contracts the RED tests must assert against. These are the locked names downstream
     plans (M14-02..04) will implement. Tests reference them so collection succeeds
     (import-time names) while assertions fail (behavior not yet implemented). -->

Locked decisions resolving the 3 RESEARCH Open Questions (bind in tests as documented expectations):
- OQ-1: lifecycle._next_handle gets `prefix: str = "bg"`; new lifecycle._next_watch_handle(session_id) -> "watch-NNN"
  using a separate lifecycle._WATCH_HANDLE_COUNTERS dict.
- OQ-2: fs_watch tool is_mutating=False; fs_watch_poll tool is_mutating=False (parity with shell_monitor;
  Observer thread + .voss-cache JSONL is not a workspace mutation — matches code_refresh/shell_monitor precedent).
- OQ-3: daemon re-exec argv = [sys.executable, "-m", "voss.harness.cli", "watch", "--_is-worker", ...];
  re-entry guard flag is "--_is-worker".

Symbols the tests import (defined by later plans; tests xfail/fail until then):
- voss.harness.lifecycle: _WATCHERS (dict), WatcherRecord, _next_watch_handle, _find_watcher,
  _read_log_cursor, reap_watchers, register_watcher
- voss.harness.tools.make_toolset(cwd, *, session_id=...) result keys: "fs_watch", "fs_watch_poll"
- voss.harness.cli: watch_cmd (click command), and the top-level `voss watch` invocation via CliRunner

From voss/harness/lifecycle.py (existing, the reset analog test_lifecycle.py uses):
```
def reset_for_tests() -> None: ...   # M14-02 extends to clear _WATCHERS + _WATCH_HANDLE_COUNTERS
def monitor_job(handle, since_ms=0, *, session_id=None) -> str: ...  # cursor-format oracle for WATCH-02
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Pin watchdog dependency (runtime + dev)</name>
  <read_first>
    - pyproject.toml (lines 10-55 — `dependencies` list ending `psutil>=5.9,<8`, and `[project.optional-dependencies] dev`)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-RESEARCH.md (§ Standard Stack — watchdog>=4.0,<7, latest 6.0.0, Python 3.9+; § Package Legitimacy Audit — watchdog APPROVED)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-PATTERNS.md (pyproject.toml section — copy the `psutil>=5.9,<8` pin style exactly)
  </read_first>
  <action>
    Add `"watchdog>=4.0,<7",` to the `[project] dependencies` list in pyproject.toml immediately
    after the `"psutil>=5.9,<8",` line (mirror the existing pin style — no inline comment needed).
    Add `"watchdog>=4.0,<7",` to the `[project.optional-dependencies] dev` list as well so the test
    suite can import it. Then run `pip install -e ".[dev]"` so the new dependency is resolved into the
    active environment. Do NOT touch the `search`/`code` extras or any other dependency line (surgical change).
  </action>
  <verify>
    <automated>python -c "import watchdog; from watchdog.observers import Observer; from watchdog.events import PatternMatchingEventHandler; print(watchdog.version.VERSION_STRING)"</automated>
  </verify>
  <acceptance_criteria>
    - Source assertion: `grep -c 'watchdog>=4.0,<7' pyproject.toml` returns 2 (runtime + dev).
    - Behavior assertion: `python -c "import watchdog"` exits 0 and prints a version in the range [4.0, 7.0).
    - Surgical: `git diff --stat pyproject.toml` shows only additions, no other dependency lines changed.
  </acceptance_criteria>
  <done>watchdog>=4.0,<7 appears exactly twice in pyproject.toml (runtime + dev) and imports cleanly in the active venv.</done>
</task>

<task type="auto">
  <name>Task 2: Author the 10 RED WATCH tests + autouse/daemon fixtures</name>
  <read_first>
    - tests/harness/test_lifecycle.py (the `_reset_registries` autouse fixture ~lines 14-18, async test structure, `@pytest.mark.skipif(_SLEEP_BIN is None ...)` pattern, `shutil.which` binary probes)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-VALIDATION.md (§ Per-Task Verification Map — the EXACT 10 test names; § Wave 0 Requirements; § Flakiness Mitigations — poll-with-retry not time.sleep, observer.daemon=True, write file once)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-RESEARCH.md (§ Validation Architecture → Test Map; § Common Pitfalls 2/3/4/6/7; Flakiness Landmines table)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-PATTERNS.md (tests/harness/test_m14_watch.py section — fixture shape; daemon PID cleanup fixture; platform skip)
    - voss/harness/lifecycle.py (lines 524-537 `reset_for_tests` — the function the autouse fixture calls; lines 454-482 `monitor_job` — the cursor-format oracle for test_shared_cursor_reader_format)
  </read_first>
  <action>
    Create tests/harness/test_m14_watch.py with EXACTLY these 10 test functions (names are the binding
    Nyquist contract — do not rename): test_debounce_coalesces_rapid_writes, test_non_matching_glob_no_event,
    test_watcher_registry_and_reap, test_fs_watch_tool_cursor_read, test_shared_cursor_reader_format,
    test_voss_watch_reruns_on_change, test_watch_command_allowlist, test_nondaemon_watch_reaped_on_exit,
    test_daemon_watch_survives_exit, plus a 10th `test_watchdog_dependency_importable` covering WATCH-05's
    importability acceptance criterion. Add an autouse fixture `_reset_registries` that calls
    `voss.harness.lifecycle.reset_for_tests()` before and after each test (same shape as test_lifecycle.py;
    relies on M14-02 extending reset_for_tests to clear _WATCHERS). Add a `daemon_pid_cleanup` fixture
    that yields a list, and in teardown iterates it calling `os.kill(pid, signal.SIGTERM)` swallowing
    ProcessLookupError. Tests MUST collect cleanly: import the target symbols guarded so collection never
    errors — use `pytest.importorskip`-free direct imports where the module exists today (lifecycle, tools,
    cli) and assert on not-yet-existing attributes/behavior so each test FAILS (RED) rather than ERRORS at
    collection. Tests touching events use a poll-with-retry helper (50ms interval, 2s max) — never
    `time.sleep(debounce_ms/1000 + ε)`. Each event test writes the watched file ONCE. Use pytest `tmp_path`.
    Add `@pytest.mark.skipif(sys.platform == "win32", reason="WATCH-05 Windows non-gating")` on the two
    event-timing tests. The cursor-format test asserts the future `lifecycle._read_log_cursor` output
    matches the `[cursor N][status]\n...` shape produced by the existing `monitor_job` (use monitor_job's
    format as the oracle). Tests reference the OQ-locked names from <interfaces> (watch-NNN handle prefix,
    fs_watch/fs_watch_poll is_mutating=False, --_is-worker re-entry flag) as documented expectations.
  </action>
  <verify>
    <automated>python -m pytest tests/harness/test_m14_watch.py -q --co && python -m pytest tests/harness/test_m14_watch.py -q -p no:cacheprovider 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - Behavior assertion: `python -m pytest tests/harness/test_m14_watch.py -q --co` lists exactly 10 collected items and exits 0 (collection succeeds — no ImportError/CollectError).
    - Test command (RED gate): `python -m pytest tests/harness/test_m14_watch.py -q` exits non-zero with failures (NOT errors) — the suite is RED because production code does not exist yet.
    - Source assertion: `grep -v '^#' tests/harness/test_m14_watch.py | grep -c 'def test_'` returns 10.
    - Source assertion: `grep -c 'reset_for_tests' tests/harness/test_m14_watch.py` >= 1 (autouse fixture wired).
    - Source assertion: `grep -c 'SIGTERM' tests/harness/test_m14_watch.py` >= 1 (daemon PID cleanup fixture present).
    - No `time.sleep(` used as the sole event-wait mechanism: `grep -c 'def _poll_for\|while.*time.*<\|for _ in range' tests/harness/test_m14_watch.py` >= 1 (poll-with-retry helper present).
  </acceptance_criteria>
  <done>10 named tests collect cleanly and fail RED (no collection errors); autouse reset fixture + daemon-PID cleanup fixture present; poll-with-retry used for event waits; Windows event tests skip-marked.</done>
</task>

<task type="auto">
  <name>Task 3: Add macos-latest to the WATCH-test CI matrix (WATCH-05)</name>
  <read_first>
    - .github/workflows/ci.yml (lines 32-75 — the `stub` job: `runs-on: ubuntu-latest`, `strategy.matrix.python-version: ["3.11","3.12"]`, the `pip install -e ".[dev]"` step, the final `pytest -q -m "not live"` step)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-RESEARCH.md (§ Common Pitfall 7 Windows CI gating; § Cross-Platform Notes — macOS FSEvents acceptance; § Validation Architecture — `matrix: [ubuntu-latest, macos-latest]` for WATCH event tests)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-PATTERNS.md (.github/workflows/ci.yml section — add macos-latest with the documenting comment)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-SPEC.md (WATCH-05 acceptance — macOS+Linux gating, Windows non-gating documented)
  </read_first>
  <action>
    Add a new CI job `watch-cross-platform` to .github/workflows/ci.yml (do NOT widen the existing `stub`
    job's OS matrix — keep stub on ubuntu-latest to avoid ballooning the full suite onto macOS runners).
    The new job uses `strategy.matrix.os: [ubuntu-latest, macos-latest]`, `runs-on: ${{ matrix.os }}`,
    python "3.12", `pip install -e ".[dev]"`, and runs ONLY the WATCH event tests:
    `python -m pytest tests/harness/test_m14_watch.py -q -m "not live"`. Add a YAML comment block above the
    job documenting: "WATCH-05: macOS + Linux are the gating runners for FSEvents/inotify event delivery.
    Windows is explicitly non-gating per SPEC WATCH-05 and is intentionally excluded from this matrix."
    Mirror the existing `stub` job's checkout/setup-python/cache-pip step structure exactly.
  </action>
  <verify>
    <automated>python -c "import yaml,sys; d=yaml.safe_load(open('.github/workflows/ci.yml')); j=d['jobs']['watch-cross-platform']; m=j['strategy']['matrix']['os']; assert 'macos-latest' in m and 'ubuntu-latest' in m and 'windows' not in str(m).lower(), m; print('ok', m)"</automated>
  </verify>
  <acceptance_criteria>
    - Source assertion: `python -c "import yaml; d=yaml.safe_load(open('.github/workflows/ci.yml')); print('watch-cross-platform' in d['jobs'])"` prints True.
    - Behavior assertion: the new job matrix contains `macos-latest` and `ubuntu-latest` and NOT any windows entry (verify command asserts this).
    - Source assertion: `grep -c 'WATCH-05' .github/workflows/ci.yml` >= 1 (documenting comment present).
    - The `stub` job's `runs-on` remains `ubuntu-latest` (unchanged): `python -c "import yaml; d=yaml.safe_load(open('.github/workflows/ci.yml')); print(d['jobs']['stub']['runs-on'])"` prints `ubuntu-latest`.
  </acceptance_criteria>
  <done>ci.yml has a `watch-cross-platform` job on [ubuntu-latest, macos-latest] running only the WATCH tests, with a WATCH-05 documenting comment; the `stub` job is untouched.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking-human">
  <what-built>
    Wave 0 scaffold: `watchdog>=4.0,<7` pinned (runtime + dev) and imported in the venv;
    `tests/harness/test_m14_watch.py` with 10 collecting RED tests + reset/daemon-PID fixtures;
    a `watch-cross-platform` CI job on macOS+Linux. The watchdog package legitimacy was flagged
    [ASSUMED] in M14-RESEARCH.md § Package Legitimacy Audit (slopcheck unavailable).
  </what-built>
  <how-to-verify>
    1. Confirm watchdog legitimacy: open https://pypi.org/project/watchdog/ and verify the project is
       the canonical `gorakhargosh/watchdog` filesystem-events library (14-year history, used by Django/
       pytest-watch/Jupyter), and the resolved version is in [4.0, 7.0).
    2. Run `python -m pytest tests/harness/test_m14_watch.py -q --co` and confirm exactly 10 tests collect.
    3. Run `python -m pytest tests/harness/test_m14_watch.py -q` and confirm it is RED (failures, not
       collection errors) — this is the expected pre-implementation state.
    4. Confirm the new CI job exists and excludes Windows.
  </how-to-verify>
  <resume-signal>Type "approved" to proceed to M14-02 (lifecycle + watch backend), or describe issues.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| PyPI → dev/CI environment | The new `watchdog` package is fetched from PyPI and installed; untrusted-supply-chain surface |
| Test fixture → OS process table | The daemon-PID cleanup fixture sends signals to PIDs it recorded |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M14-01 | Tampering | `watchdog` package install (supply chain) | mitigate | Pin `watchdog>=4.0,<7` (no floating latest); blocking human checkpoint verifies legitimacy via pypi.org/project/watchdog before any GREEN wave (M14-RESEARCH § Package Legitimacy Audit flagged [ASSUMED]) |
| T-M14-02 | Denial of Service | daemon-PID cleanup fixture | mitigate | Fixture swallows ProcessLookupError and only signals PIDs it itself recorded in the yielded list — never scans/kills arbitrary processes |
| T-M14-03 | Tampering | CI matrix scope creep | accept | Windows excluded by design (SPEC WATCH-05 non-gating); documented in ci.yml comment — accepted risk that Windows file-watch is unverified |
| T-M14-SC | Tampering | pip install watchdog | mitigate | slopcheck + blocking human checkpoint for the [ASSUMED] watchdog package per M14-RESEARCH § Package Legitimacy Audit |
</threat_model>

<verification>
- `grep -c 'watchdog>=4.0,<7' pyproject.toml` == 2
- `python -c "import watchdog"` exits 0
- `python -m pytest tests/harness/test_m14_watch.py -q --co` collects exactly 10 tests, exit 0
- `python -m pytest tests/harness/test_m14_watch.py -q` is RED (failures, not collection errors)
- `watch-cross-platform` CI job exists on [ubuntu-latest, macos-latest], excludes Windows
- Blocking human checkpoint approved (watchdog legitimacy confirmed)
</verification>

<success_criteria>
- watchdog pinned runtime + dev and importable in the active venv
- All 10 binding WATCH tests collect cleanly and fail RED (no collection errors)
- Watcher-reset autouse fixture + daemon-PID cleanup fixture present
- CI runs WATCH event tests on macOS + Linux; Windows excluded + documented (WATCH-05)
- Package-legitimacy human checkpoint approved
</success_criteria>

<output>
Create `.planning/phases/M14-long-running-tasks-watch-caps-01e/M14-01-SUMMARY.md` when done
</output>
