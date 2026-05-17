---
phase: T5
slug: shell-ergonomics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-16
---

# Phase T5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8 + pytest-asyncio 0.23 (`asyncio_mode = "auto"`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/harness/test_t5_shell.py tests/harness/test_lifecycle.py -x -q` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~20s quick; full suite ~2 min |

---

## Sampling Rate

- **After every task commit:** `pytest tests/harness/test_t5_shell.py tests/harness/test_lifecycle.py -x -q`
- **After every plan wave:** `pytest -q -m "not live"`
- **Before `/gsd:verify-work`:** full suite green (`pytest -q`) + manual smoke (`voss jobs` from a separate shell while a `voss chat` bg job runs)
- **Max feedback latency:** 20 seconds

> Coverage gate `fail_under=90` is scoped to `voss_runtime` only; T5 code lives in `voss.harness` so the gate is unaffected — but every new harness path MUST have behavioral test coverage regardless.

---

## Per-Task Verification Map

> Populated by planner. Each task gets an `<automated>` block whose command appears here with requirement ID + threat ref.

| Task ID | Plan | Wave | Requirement | Threat Ref | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------|-------------------|-------------|--------|
| _populated by planner_ | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Requirement → Test Map (from RESEARCH.md §Validation Architecture)

| Req | Behavior | Test Type | Command |
|-----|----------|-----------|---------|
| SHELL-01 | cap constant is 30720 | unit source-inspection | `pytest tests/harness/test_shell_timeout.py -k cap -q` |
| SHELL-01 | >30KB truncates with `<truncated, total N bytes>` | unit | `test_t5_shell.py::test_shell_run_30kb_truncation` |
| SHELL-02 | bg spawns, returns `bg-001`, no PID in result | unit (fast fake cmd) | `::test_background_returns_handle` |
| SHELL-02 | counter monotonic + zero-padded per session | unit | `::test_handle_counter` |
| SHELL-03 | `[cursor N][running]` → `[exit M]`, cursor round-trips | integration (det. emitter) | `::test_monitor_cursor_progression` |
| SHELL-03 / SC#1 | 20s job observable from a 2nd turn (short emitter, NOT real 20s) | integration | `::test_monitor_across_turns` |
| SHELL-04 | INT/TERM ok; KILL/unknown → `<denied: unsupported signal>` | unit | `::test_signal_surface` |
| SHELL-04 | SIGTERM delivered, job exits | integration (POSIX skipif) | `::test_signal_terminates` |
| SHELL-05 | `voss jobs` reads sidecar from separate invocation; table + `--json` | integration (CliRunner, pre-seed `.meta.json`) | `::test_voss_jobs_reads_sidecar` |
| SC #2 | reap SIGTERM→SIGKILL escalation timing | integration (SIG_IGN child, monotonic bounds) | `::test_reap_jobs_escalation` |
| SC #3 | 30s-no-output watchdog kills + `reason=watchdog_no_output` | integration (inject small deadline) | `::test_no_output_watchdog` |
| SC #3 | 100MB RSS watchdog kills + `reason=watchdog_mem` | integration (monkeypatch RSS probe >100MB) | `::test_rss_watchdog` |

---

## Deterministic Test Primitives (MANDATORY — subprocess+asyncio+cross-turn is the hard part)

- **No real production-constant sleeps.** Mirror `test_shell_timeout.py:25` — inject a 0.2–0.3s deadline, never the real 30s. Parametrize `no_output_deadline_s` (default 30.0).
- **Deterministic emitter:** `tests/harness/fixtures/emit.py` — prints N lines with small (0.05s) sleeps, line-counted, bounded. Used by all pump/monitor tests.
- **RSS watchdog:** monkeypatch the `_tree_rss_bytes` probe to return a synthetic >100MB int. NEVER allocate real memory (slow, flaky, OOM-risk).
- **Reap escalation:** SIG_IGN-SIGTERM child (`test_lifecycle.py:38-44` pattern) + `time.monotonic()` bounds.
- **`voss jobs` cross-process realism:** do NOT spawn a real session. Pre-write `.voss-cache/jobs/<sid>/bg-001.meta.json` to `tmp_path`, point `.active-session` at it, `CliRunner().invoke(jobs_cmd, ...)`. This is the honest test of the cross-process contract (D-11) without process orchestration.
- **`lifecycle.reset_for_tests()` MUST be extended** to clear `_JOBS` (autouse fixture, `test_lifecycle.py:14` pattern) — else cross-test job leakage.

---

## Wave 0 Requirements

- [ ] `tests/harness/test_t5_shell.py` — SHELL-01..05 + SC#1/#2/#3 (does not exist)
- [ ] `tests/harness/fixtures/emit.py` — deterministic bounded line emitter
- [ ] Extend `lifecycle.reset_for_tests()` to clear `_JOBS`
- [ ] Extend `tests/harness/test_shell_timeout.py` (or sibling) with `assert "30720" in src` guard mirroring the existing `timeout=30.0` source-inspection guard at :128
- [ ] Reap-escalation timing test (SIG_IGN pattern)
- [ ] Add `psutil>=5.9,<8` to `[project] dependencies` BEFORE `test_rss_watchdog` (production module imports psutil even though probe is monkeypatched) — **D-10 human-verify checkpoint precedes this**

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `voss jobs` shows a live bg job from a genuinely separate terminal | SHELL-05 / D-11 | True cross-process visibility needs two real OS processes | Terminal A: `voss chat`, start a 60s bg job. Terminal B: `voss jobs` — confirm the handle, PID, RUNNING status appear. |
| Orphan grandchild reaped on session exit (POSIX killpg) | SC #2 | Process-tree teardown is environment-sensitive | Start a bg job that forks a child; kill `voss chat`; confirm both PIDs gone within 5s (`ps`). |
| psutil dependency legitimacy | D-10 | Supply-chain human-verify (slopcheck unavailable at research time) | Confirm `psutil` PyPI page: maintainer giampaolo, source github.com/giampaolo/psutil, recent release. **BLOCKING checkpoint before Wave 0 dep add.** |

---

## Security Gates (from RESEARCH.md §Security Domain)

| Threat | STRIDE | Mitigation | Verified By |
|--------|--------|------------|-------------|
| Command injection via metachars | Tampering/EoP | `shell_allowed()` reused verbatim (D-05) | `::test_signal_surface` + sandbox reuse |
| Runaway/forkbomb bg process | DoS | 30s+100MB watchdog; `start_new_session`+`killpg` tree-kill | `::test_no_output_watchdog`, `::test_rss_watchdog`, `::test_reap_jobs_escalation` |
| PID leak to model | Info disclosure | D-01: only `bg-NNN` crosses tool boundary | `::test_background_returns_handle` (assert no PID in result string) |
| `shell_signal`/`shell_run_background` edit-mode bypass | EoP | **D-12**: extend `permissions.py mode_allows` edit-mode deny to new mutating shell tools | new permissions test asserting edit mode denies `shell_run_background` + `shell_signal` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (incl. psutil dep + `_JOBS` reset)
- [ ] No real 30s/100MB sleeps or allocations in unit tests
- [ ] D-12 edit-mode security test exists
- [ ] D-10 psutil human-verify checkpoint precedes the dep add
- [ ] `nyquist_compliant: true` set once per-task map populated

**Approval:** pending
