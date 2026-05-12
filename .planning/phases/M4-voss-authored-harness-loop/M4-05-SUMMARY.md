---
phase: M4
plan: 05
status: complete
date: 2026-05-12
requirements-completed:
  - DOG-06
---

# M4-05 Summary - CI gate, install one-liner, doctor cache row

M4-05 closed the operational polish for the Voss-authored harness loop: CI now checks the dogfood `.voss` sources, install docs show the eager-compile path, and `voss doctor` reports compiled-harness cache freshness without blocking.

## What Changed

- `.github/workflows/ci.yml` now runs `python -m voss.cli check voss/harness/agent/` in the `stub` job at lines 26-27, after `pip install -e ".[dev]"` and before the existing demo check and pytest step.
- `README.md` install section now documents `voss compile voss/harness/agent/` at lines 28-32 as the optional eager-compile step for `VOSS_HARNESS=compiled`.
- `voss/harness/diagnostics.py` now has `check_harness_cache(cwd)` at lines 187-203 and includes it in `run_all_checks` at line 216.
- `tests/harness/test_doctor.py` adds a row-existence sentinel for the `"harness cache"` doctor row.

## Doctor Behavior

`check_harness_cache(cwd)` has three branches:

- No `voss/harness/agent/` sources in `cwd`: returns OK with `no harness sources`.
- Sources exist but `harness_cache.assert_fresh(cwd)` raises `StaleHarnessCacheError`: returns WARN with fix `voss compile voss/harness/agent/`.
- Cache is fresh: returns OK with `.voss-cache/harness/ fresh`.

WARN remains informational because `aggregate_exit_code` only returns non-zero for `CheckResult.FAIL`.

## DOG Coverage

- DOG-01..05: five authored files under `voss/harness/agent/` check clean.
- DOG-06: `voss check voss/harness/agent/` is now a CI gate.
- DOG-07: compiled backend dispatch and subprocess smoke passed in M4-03/M4-04.
- DOG-08: `.voss-cache/harness/` artifacts and manifest are produced by directory compile.

## D-Decision Trace

- D-01..D-04: shipped in M4-03 via the five thin `.voss` control-flow files and Python-owned tools/permissions.
- D-05..D-07: shipped in M4-02 via directory `check`/`compile` and diagnostic aggregation.
- D-08..D-12: shipped in M4-03/M4-04 via backend dispatch, Python parity oracle, loud stale cache, parity test, and compiled smoke.
- D-13..D-15: shipped in M4-02/M4-03 via per-file cache artifacts, sha/version manifest, and sandboxed cache writes.
- D-16: completed here with README eager compile plus informational doctor row.

## Verification

```bash
pytest tests/harness/test_doctor.py tests/harness/test_cache_freshness.py -q
```

Result: `9 passed`.

```bash
pytest tests/harness/ -q -m "not live"
```

Result: passed with existing skips.

```bash
pytest tests/harness/ tests/codegen/test_imports.py tests/codegen/test_await_use_import.py tests/parser/test_use_alias.py -q -m "not live"
```

Result: passed with existing skips.

```bash
grep -F "voss.cli check voss/harness/agent/" .github/workflows/ci.yml
grep -F "voss compile voss/harness/agent/" README.md
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
git diff --check
```

Result: all passed.

## Notes

- The validation plan referenced `tests/codegen/test_use_alias.py`, which does not exist in this repo. The equivalent final M4 run used the real codegen alias coverage file, `tests/codegen/test_imports.py`, alongside `tests/codegen/test_await_use_import.py` and `tests/parser/test_use_alias.py`.
- `.planning/STATE.md` now marks M4 complete and records the 2026-05-12 completion activity.
