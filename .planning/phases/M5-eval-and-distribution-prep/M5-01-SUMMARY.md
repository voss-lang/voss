---
phase: M5
plan: 01
status: complete
date: 2026-05-12
requirements-completed:
  - EVAL-01
---

# M5-01 Summary - eval package skeleton and suite loader

M5-01 stood up the `voss.eval` package and the Wave 0 schema/loader boundary for later eval runner, judge, summary, and golden fixture work.

## What Changed

- Added `voss/eval/__init__.py` as the package marker with the deferred Wave 2 `run_suite` re-export comment.
- Added `voss/eval/suite.py` with `TaskSpec`, `load_task`, and `load_suite`.
- Added `tests/eval/` package marker and Wave 0 unit tests for task spec validation, suite loading, and fixture isolation.

## TaskSpec

`TaskSpec` uses `ConfigDict(extra="forbid")` and accepts only:

- `prompt: str`
- `mode: Literal["plan", "edit", "auto"]`
- `rubric: str`
- `judge_inputs: list[Literal["final", "file_diff"]]`, defaulting to `["final", "file_diff"]`
- `provider: str | None`
- `model: str | None`
- `auto_approve_edits: bool`, defaulting to `False`

The tests pin minimal defaults, invalid-mode rejection, unknown-key rejection, and `auto_approve_edits=True` round-trip behavior.

## Loader Contract

`load_task(task_dir)` reads `task_dir / "task.toml"` through stdlib `tomllib` and validates it as `TaskSpec`.

`load_suite(suite_root, suite="golden")` walks the suite directory and returns `list[tuple[str, TaskSpec]]`, sorted by directory basename. Passing `suite=""` treats `suite_root` itself as the suite directory; this is the Wave 0 convention used by the inline tests before Wave 4 golden fixtures exist. Non-directories and directories without `task.toml` are skipped.

## Fixture Isolation

`tests/eval/test_fixture_isolation.py` includes the temporary inline `_prepare_fixture` helper. It copies `fixture/` into a destination cwd, runs `git init -q -b main`, stages, and commits the initial tree. The file contains the required TODO:

```python
# TODO Wave 2: replace inline helper with `from voss.eval.runner import _prepare_fixture`.
```

The tests assert the helper creates a git repo and that two fixture preparations do not share state.

## Verification

```bash
python3 -c "from voss.eval.suite import TaskSpec, load_task, load_suite; s = TaskSpec(prompt='x', mode='plan', rubric='PASS if ok'); assert s.judge_inputs == ['final','file_diff']; assert s.auto_approve_edits is False; print('OK')"
```

Result: `OK`.

```bash
pytest -q -m "not slow and not live" tests/eval/test_task_spec.py tests/eval/test_suite_loads.py tests/eval/test_fixture_isolation.py
```

Result: `8 passed`.

```bash
pytest -q -m "not slow and not live" tests/eval/
```

Result: `8 passed`.

No `voss.eval.runner`, `voss.eval.judge`, or `voss.eval.summary` imports were introduced.

## Notes

- Wave 0 tests intentionally build inline suite fixtures instead of depending on `tests/eval/golden/`, which lands in Wave 4.
- Subagent commits also added M6 roadmap/requirements material outside this M5-01 scope. I left those commits intact and did not rewrite history.
