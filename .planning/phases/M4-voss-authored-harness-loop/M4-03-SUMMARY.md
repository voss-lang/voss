---
phase: M4
plan: 03
status: complete
date: 2026-05-12
---

# M4-03 Summary - dogfood files + boot dispatch

## Layout

M4-03 uses the planned cross-file split under `voss/harness/agent/`:

- `loop.voss` — orchestration entry with `ctx(budget: 60000 tokens)`, routing, planning, execution, review, and clarification branches.
- `router.voss` — `probable<string>` intent routing.
- `planner.voss` — `probable<Plan>` planning with confidence gate and fallback `Plan` construction for low confidence.
- `executor.voss` — thin forwarder to Python `_run_step_loop`.
- `reviewer.voss` — final synthesis with `try/catch`, `_substitute_placeholders`, and `_make_turn_result`.

Comment-stripped line counts:

- `loop.voss`: 35
- `router.voss`: 13
- `planner.voss`: 23
- `executor.voss`: 13
- `reviewer.voss`: 23

All files clear the D-01 floor checks.

## Python Changes

### `voss/harness/agent.py`

- Extracted `_run_step_loop(...)`.
- Added `_substitute_placeholders(...)`.
- Added `_make_turn_result(...)`.
- `run_turn` now delegates tool execution and placeholder substitution to those helpers while preserving recorder behavior.

### `voss/harness/tools.py`

- Added `ToolEntry.invoke_dict(args)`.

### `voss/harness/cli.py`

- Removed module-top direct `run_turn` dependency.
- Added `_resolve_run_turn(cwd)` with backend resolution:
  1. `VOSS_HARNESS`
  2. `[harness] backend` from config
  3. `"python"`
- Invalid backends raise `click.ClickException`.
- Compiled backend calls `harness_cache.assert_fresh(cwd)` before importing `.voss-cache/harness/loop.py`.
- `do_cmd` resolves the backend per invocation.
- `_run_repl` also resolves the backend per turn, so chat/edit REPL turns can exercise the compiled path after the cache is proven fresh.

## Manifest Sample

The compiled manifest contains all five sources:

```json
{
  "version": 1,
  "voss_version": "0.1.0",
  "sources": {
    "executor.voss": {"sha256": "...", "lines": 16},
    "loop.voss": {"sha256": "...", "lines": 38},
    "planner.voss": {"sha256": "...", "lines": 26},
    "reviewer.voss": {"sha256": "...", "lines": 26},
    "router.voss": {"sha256": "...", "lines": 16}
  }
}
```

## Verification

```bash
python3 -m voss.cli check voss/harness/agent/
```

Result: `0 errors, 0 warnings across 5 files`.

```bash
python3 -m voss.cli compile voss/harness/agent/ --project-root .
grep -n 'await _run_step_loop' .voss-cache/harness/executor.py
python3 -c "import json; m=json.load(open('.voss-cache/harness/_manifest.json')); assert m['version']==1; assert len(m['sources'])==5"
```

Result: all passed; `executor.py` contains `await _run_step_loop(...)`.

```bash
pytest tests/harness/test_agent_integration.py tests/harness/test_boot_dispatch.py -q
```

Result: 20 passed.

```bash
pytest tests/harness/ -q -m "not live"
```

Result: passed with existing skips.

## Notes

- Worker subagents landed the helper extraction, boot dispatch, and initial cross-file `.voss` split. The final local integration adjusted `planner.voss` so the directory check is warning-free.
- `planner.voss` constructs a fallback `Plan` on the low-confidence path instead of returning `plan.value` outside the confidence gate.
- M4-04 can now add the parity and DOG-07 smoke tests.
