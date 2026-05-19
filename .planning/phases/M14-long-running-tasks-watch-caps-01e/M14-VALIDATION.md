---
phase: M14
slug: long-running-tasks-watch-caps-01e
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-18
---

# Phase M14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `M14-RESEARCH.md` § Validation Architecture (HIGH confidence).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (`asyncio_mode=auto`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — already configured |
| **Quick run command** | `pytest tests/harness/test_m14_watch.py -q -x` |
| **Full suite command** | `pytest -q -m "not live"` |
| **Estimated runtime** | ~15 seconds (watch tests are poll-with-retry bounded ≤ 2s each) |

---

## Sampling Rate

- **After every task commit:** `pytest tests/harness/test_m14_watch.py -q -x`
- **After every plan wave:** `pytest tests/harness/ -q -m "not live" -x`
- **Before `/gsd:verify-work`:** Full suite green (`pytest -q -m "not live"`)
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

> Task IDs assigned by gsd-planner. Each WATCH requirement's automated test below is the binding Nyquist contract; planner maps tasks onto these and fills Task ID / Wave columns. All tests are `❌ W0` until the Wave 0 scaffold (`tests/harness/test_m14_watch.py`) lands.

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| WATCH-01 | Edit matching file → exactly one coalesced event within 200ms window | Integration | `pytest tests/harness/test_m14_watch.py::test_debounce_coalesces_rapid_writes -x` | ❌ W0 | ⬜ pending |
| WATCH-01 | Edit non-matching file → zero events | Integration | `pytest tests/harness/test_m14_watch.py::test_non_matching_glob_no_event -x` | ❌ W0 | ⬜ pending |
| WATCH-01 | `_WATCHERS` registry populated; `reap_watchers()` stops Observer | Unit | `pytest tests/harness/test_m14_watch.py::test_watcher_registry_and_reap -x` | ❌ W0 | ⬜ pending |
| WATCH-02 | `fs_watch` registers; `fs_watch_poll` reads JSONL in later turn | Integration | `pytest tests/harness/test_m14_watch.py::test_fs_watch_tool_cursor_read -x` | ❌ W0 | ⬜ pending |
| WATCH-02 | Shared `_read_log_cursor` output format identical to `shell_monitor` | Unit | `pytest tests/harness/test_m14_watch.py::test_shared_cursor_reader_format -x` | ❌ W0 | ⬜ pending |
| WATCH-03 | `voss watch 'pytest -q'` re-executes command on watched-file change | Integration | `pytest tests/harness/test_m14_watch.py::test_voss_watch_reruns_on_change -x` | ❌ W0 | ⬜ pending |
| WATCH-03 | Shell allowlist enforced for `voss watch <command>` | Unit | `pytest tests/harness/test_m14_watch.py::test_watch_command_allowlist -x` | ❌ W0 | ⬜ pending |
| WATCH-04 | Non-daemon `voss watch` reaped on session exit (TERM ≤2s / KILL ≤5s) | Integration | `pytest tests/harness/test_m14_watch.py::test_nondaemon_watch_reaped_on_exit -x` | ❌ W0 | ⬜ pending |
| WATCH-04 | Daemon `voss watch --daemon` still running after session exit | Integration | `pytest tests/harness/test_m14_watch.py::test_daemon_watch_survives_exit -x` | ❌ W0 | ⬜ pending |
| WATCH-05 | WATCH-01/02 event tests pass on macOS + Linux | CI matrix | GitHub Actions `matrix: [ubuntu-latest, macos-latest]` | ❌ W0 (CI cfg) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/harness/test_m14_watch.py` — all WATCH-01..05 tests (10 tests, red stubs)
- [ ] `_reset_watchers` autouse fixture — mirrors `_reset_registries` in `test_lifecycle.py`; calls `lifecycle.reset_for_tests()` extended with `_WATCHERS.clear()`
- [ ] Daemon PID cleanup fixture — teardown `os.kill(daemon_pid, signal.SIGTERM)` (swallow `ProcessLookupError`)
- [ ] CI workflow update — add `macos-latest` to the `stub` job matrix OR a separate `watch-cross-platform` job
- [ ] `watchdog>=4.0,<7` added to `pyproject.toml` `[project] dependencies` + `[project.optional-dependencies] dev`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Windows file-watch behavior | WATCH-05 | Best-effort / non-gating per SPEC; ReadDirectoryChangesW timing differs | Optional: run `test_debounce_coalesces_rapid_writes` on a Windows box; failure is documented, not blocking |

*All gating phase behaviors have automated verification (macOS + Linux CI). Windows is the only manual/best-effort item, by SPEC design.*

---

## Flakiness Mitigations (binding)

- Poll-with-retry (50ms interval, 2s max) to observe events — NEVER `time.sleep(debounce_ms/1000 + ε)`.
- `observer.daemon = True` before `observer.start()`; `threading.Timer.daemon = True` in the Debouncer (prevents pytest/interpreter hang).
- Probe `observer.is_alive()` with retry before the first test file write.
- Each test writes the watched file **once**; assert exactly 1 event after the window.
- Tests explicitly `from watchdog.observers import Observer` (not `PollingObserver`) unless testing fallback.
- `test_daemon_watch_survives_exit` records the spawned PID and kills it in fixture teardown.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags in test commands
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter (after Wave 0 lands)

**Approval:** pending
