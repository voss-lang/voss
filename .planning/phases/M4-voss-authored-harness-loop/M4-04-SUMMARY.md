---
phase: M4
plan: 04
status: complete
date: 2026-05-12
requirements-completed:
  - DOG-07
---

# M4-04 Summary - compiled loop parity + DOG-07 smoke

M4-04 landed the wave-3 proof that the compiled `.voss` harness loop can run the same fixture as the Python parity oracle and can boot through the real `voss do` CLI path.

## What Changed

- Added a session-scoped `precompiled_harness` fixture in `tests/harness/conftest.py` that copies `voss/harness/agent/*.voss` into a temp project and compiles the harness cache once for the test session.
- Added `tests/harness/test_voss_loop_parity.py` with an inline `FakeProvider` and a fixture plan reading `fixture.md`.
- Added `tests/harness/test_dog07_smoke.py`, which runs `VOSS_HARNESS=compiled` and `VOSS_HERMETIC=1` through `python -m voss.cli do` as a subprocess.
- Fixed explicit-ctx probable ask codegen so `let x: probable<T> = ask(...)` inside `ctx {}` emits a wrapped `ProbableValue`.
- Added a deterministic `StubProvider` fallback for Plan-like pydantic schemas so hermetic compiled turns can produce a valid empty plan instead of crashing.

## Task Commits

1. `77a6c72` - added precompiled harness fixture, parity test, and DOG-07 smoke environment setup.
2. `d43adcf` - fixed codegen/runtime support for probable values inside explicit ctx blocks.
3. `cbe19ea` - added focused codegen and provider tests for the regression.
4. `feaec74` - aligned parity `FakeProvider` with `ContextScope.ask(return_type=...)`.

## Verification

```bash
python3 -m voss.cli check voss/harness/agent/
```

Result: `0 errors, 0 warnings across 5 files`.

```bash
pytest tests/harness/test_dog07_smoke.py tests/harness/test_voss_loop_parity.py -q
```

Result: `2 passed`.

```bash
pytest tests/codegen/test_runtime_constructs.py tests/providers/test_stub.py -q
```

Result: `13 passed`.

```bash
pytest tests/harness/ -q -m "not live"
```

Result: passed with the existing skipped tests.

```bash
git diff --check
```

Result: passed.

## Deviations

The planned tests exposed a real compiled-loop failure: generated code dereferenced `.confidence` on a plain string for explicit-ctx probable asks. I fixed the compiler/runtime support instead of weakening the DOG-07 test. This was required for the M4-04 smoke gate to exercise the actual compiled backend.

## Notes

- Parity uses `FakeProvider`, not `StubProvider`, to avoid prompt-fingerprint coupling between the Python and compiled backends.
- DOG-07 remains hermetic via `VOSS_HERMETIC=1`; no live provider credentials are needed.
- M4-05 remains pending for CI/docs/doctor cache-row work.
