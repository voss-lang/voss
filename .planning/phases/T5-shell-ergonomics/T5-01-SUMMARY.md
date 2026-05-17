# T5-01 Test Scaffold and psutil Dependency Summary

**Completed:** 2026-05-17T17:43:48Z
**Plan:** `T5-01-test-scaffold-and-psutil-dep-PLAN.md`
**Wave:** 1

## Outcome

Completed the Wave 0 T5 scaffold:

- Approved the `psutil>=5.9,<8` dependency gate after checking current PyPI/GitHub legitimacy signals.
- Added `psutil>=5.9,<8` as a runtime dependency.
- Added the separate lifecycle `_JOBS` registry and extended `reset_for_tests()` to clear it.
- Added `tests/harness/fixtures/emit.py`, a deterministic line emitter with explicit `sys.stdout.flush()`.
- Added `tests/harness/test_t5_shell.py` with 13 collecting red tests covering SHELL-01..05, SC#1/#2/#3, D-12 edit-mode denial, and the real-session sidecar path contract.
- Added `test_shell_run_30kb_cap_documented`, the required `30720` source-inspection guard with `cap` in the name.

## Files Changed

- `pyproject.toml`
- `voss/harness/lifecycle.py`
- `tests/harness/fixtures/emit.py`
- `tests/harness/test_t5_shell.py`
- `tests/harness/test_shell_timeout.py`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/phases/T5-shell-ergonomics/T5-01-SUMMARY.md`

## Verification

- `python3 -m pip install 'psutil>=5.9,<8'` installed `psutil 7.2.2`.
- `python3 -c "import psutil; print(psutil.__version__)"` printed `7.2.2`.
- `python3 -c "from voss.harness import lifecycle; lifecycle._JOBS['bg-001'] = object(); lifecycle.reset_for_tests(); assert lifecycle._JOBS == {}, lifecycle._JOBS; print('jobs-registry-ok')"` passed.
- `python3 -m py_compile tests/harness/fixtures/emit.py tests/harness/test_t5_shell.py tests/harness/test_shell_timeout.py voss/harness/lifecycle.py` passed.
- `python3 -m pytest tests/harness/test_t5_shell.py --co -q` collected 13 tests.
- `python3 -m pytest tests/harness/test_shell_timeout.py::test_shell_run_30kb_cap_documented --co -q` collected 1 test.
- `python3 -m pytest tests/harness/test_t5_shell.py -q --no-header` failed with 13 failures, as intended for the Nyquist red scaffold.
- `python3 -m pytest tests/harness/test_shell_timeout.py -k cap -q --no-header` failed on `test_shell_run_30kb_cap_documented`, as intended until T5-02 raises the cap.
- `python3 tests/harness/fixtures/emit.py 3` printed `line 0`, `line 1`, `line 2`.
- `git diff --check` passed.

## Deviations from Plan

- The environment has no `python` executable on `PATH`, so all verification used equivalent `python3` commands.
- The dependency was installed with `python3 -m pip install 'psutil>=5.9,<8'` instead of `pip install -e '.[dev]'` to avoid pulling the heavier dev/search dependency set.
- The operator delegated the human-verify decision. I checked current public package metadata and approved the gate before adding the dependency.

## Residuals

- T5-02 is expected to turn the SHELL-01 cap tests green.
- T5-03..T5-05 are expected to turn the remaining background/job/monitor/signal/jobs CLI tests green.

## Self-Check: PASSED
