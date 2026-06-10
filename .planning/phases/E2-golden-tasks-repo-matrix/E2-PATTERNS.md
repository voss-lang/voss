# Phase E2: Golden Tasks × Repo Matrix - Pattern Map

**Mapped:** 2026-06-10
**Files analyzed:** 19 (12 task.toml + 3 fixture sets + runner + summary + CLI + 4 test files)
**Analogs found:** 19 / 19

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `tests/eval/matrix/py-01-analyze/task.toml` | config | request-response | `tests/eval/golden/01-analyze/task.toml` | exact |
| `tests/eval/matrix/py-02-plan-only/task.toml` | config | request-response | `tests/eval/golden/02-plan-only/task.toml` | exact |
| `tests/eval/matrix/py-03-approved-edit/task.toml` | config | request-response | `tests/eval/golden/03-approved-edit/task.toml` | exact |
| `tests/eval/matrix/py-04-validation/task.toml` | config | request-response | `tests/eval/golden/04-validation/task.toml` | exact |
| `tests/eval/matrix/py-05-resume/task.toml` | config | request-response | `tests/eval/golden/05-resume/task.toml` | exact |
| `tests/eval/matrix/py-06-fetch-summarize/task.toml` | config | request-response | `tests/eval/golden/06-fetch-summarize/task.toml` | exact |
| `tests/eval/matrix/rust-01-analyze/task.toml` | config | request-response | `tests/eval/golden/01-analyze/task.toml` | role-match |
| `tests/eval/matrix/rust-03-approved-edit/task.toml` | config | request-response | `tests/eval/golden/03-approved-edit/task.toml` | role-match |
| `tests/eval/matrix/rust-04-validation/task.toml` | config | request-response | `tests/eval/golden/04-validation/task.toml` | role-match |
| `tests/eval/matrix/ts-01-analyze/task.toml` | config | request-response | `tests/eval/golden/01-analyze/task.toml` | role-match |
| `tests/eval/matrix/ts-03-approved-edit/task.toml` | config | request-response | `tests/eval/golden/03-approved-edit/task.toml` | role-match |
| `tests/eval/matrix/ts-04-validation/task.toml` | config | request-response | `tests/eval/golden/04-validation/task.toml` | role-match |
| `tests/eval/matrix/py-*/fixture/` | config | file-I/O | `tests/eval/golden/02-plan-only/fixture/calc.py` | exact |
| `tests/eval/matrix/rust-*/fixture/` | config | file-I/O | `tests/eval/golden/03-approved-edit/fixture/` | role-match |
| `tests/eval/matrix/ts-*/fixture/` | config | file-I/O | `tests/eval/golden/03-approved-edit/fixture/` | role-match |
| `voss/eval/runner.py` (extend) | service | event-driven | `voss/eval/runner.py` | exact (self) |
| `voss/eval/summary.py` (extend) | utility | transform | `voss/eval/summary.py` | exact (self) |
| `voss/harness/cli.py` (extend eval_cmd) | controller | request-response | `voss/harness/cli.py` lines 3492-3543 | exact (self) |
| `tests/eval/test_matrix_suite.py` | test | CRUD | `tests/eval/test_golden_checks.py` | exact |
| `tests/eval/test_matrix_runner.py` | test | request-response | `tests/eval/test_hybrid_gate.py` | exact |
| `tests/eval/test_matrix_stub.py` | test | request-response | `tests/eval/test_voss_eval_stub.py` | exact |
| `tests/eval/test_matrix_summary.py` | test | transform | `tests/eval/test_summary_md.py` | exact |

---

## Pattern Assignments

### `tests/eval/matrix/{lang}-{NN}-{task}/task.toml` (config, request-response)

**Primary analog:** `tests/eval/golden/01-analyze/task.toml`, `tests/eval/golden/03-approved-edit/task.toml`, `tests/eval/golden/04-validation/task.toml`

**Full field set — analyze cell template** (`tests/eval/golden/01-analyze/task.toml` lines 1-18):
```toml
# 01-analyze - analyze a tiny seed repo, expect .voss/architecture.md written.
prompt = "Analyze this repository and write architecture.md describing what it does."
mode = "edit"
rubric = """
PASS if:
- A file named .voss/architecture.md exists after the run.
- The file is non-empty and contains at least one paragraph describing the codebase.

FAIL if:
- .voss/architecture.md does not exist.
- The file is empty or contains only placeholder text.
"""
judge_inputs = ["final", "file_diff"]
auto_approve_edits = true

[[checks]]
type = "file_exists"
path = ".voss/architecture.md"
```

**Full field set — approved-edit cell template** (`tests/eval/golden/03-approved-edit/task.toml` lines 1-30):
```toml
# 03-approved-edit - apply an edit in edit mode with auto-approve; expect target file modified.
prompt = "Rename the function add() to sum_two() in calc.py and update its single call site in main.py."
mode = "edit"
rubric = """
PASS if:
- calc.py defines sum_two() (not add()).
- main.py imports and calls sum_two() (not add()).
- Both files were modified.

FAIL if:
- Either file is unchanged.
- The rename is incomplete (one file updated, the other not).
"""
judge_inputs = ["final", "file_diff"]
auto_approve_edits = true

[[checks]]
type = "file_contains"
path = "calc.py"
text = "sum_two"

[[checks]]
type = "file_contains"
path = "main.py"
text = "sum_two"

[[checks]]
type = "cmd"
run = "! grep -q 'def add(' calc.py"
```

**Full field set — validation cell template** (`tests/eval/golden/04-validation/task.toml` lines 1-19):
```toml
# 04-validation - invoke the repo's native test suite; expect exit 0.
prompt = "Run `voss check sample.voss` in this directory and report the exit code."
mode = "edit"
rubric = """
PASS if:
- The agent's final answer indicates the command exited 0.
- No errors or warnings reported.

FAIL if:
- The final answer indicates a non-zero exit code.
- The agent did not actually invoke the command.
"""
judge_inputs = ["final"]
auto_approve_edits = true

[[checks]]
type = "cmd"
run = "python3 -m voss.cli check sample.voss"
```

**Per-language task.toml substitutions** (from RESEARCH.md §Per-Cell Check Specifications):

For `rust-01-analyze`:
```toml
prompt = "Analyze this repository and write architecture.md describing what it does."
mode = "edit"
auto_approve_edits = true
judge_inputs = ["final", "file_diff"]

[[checks]]
type = "file_exists"
path = ".voss/architecture.md"

[[checks]]
type = "file_contains"
path = ".voss/architecture.md"
text = "Cargo.toml"
```

For `ts-01-analyze`:
```toml
[[checks]]
type = "file_contains"
path = ".voss/architecture.md"
text = "package.json"
```

For `py-03-approved-edit` (rename add → sum_two, update test file):
```toml
[[checks]]
type = "file_contains"
path = "calc.py"
text = "sum_two"

[[checks]]
type = "cmd"
run = "! grep -q 'def add(' calc.py"

[[checks]]
type = "cmd"
run = "python3 -m pytest test_calc.py -q"
timeout = 60
```

For `rust-03-approved-edit` (timeout 120 — cargo cold compile):
```toml
[[checks]]
type = "file_contains"
path = "src/lib.rs"
text = "sum_two"

[[checks]]
type = "cmd"
run = "! grep -q 'fn add(' src/lib.rs"

[[checks]]
type = "cmd"
run = "cargo test --quiet"
timeout = 120
```

For `ts-03-approved-edit` (camelCase convention):
```toml
[[checks]]
type = "file_contains"
path = "src/calc.ts"
text = "sumTwo"

[[checks]]
type = "cmd"
run = "! grep -q 'function add(' src/calc.ts"

[[checks]]
type = "cmd"
run = "npm test"
timeout = 60
```

For `py-04-validation`, `rust-04-validation`, `ts-04-validation`:
```toml
# py-04
[[checks]]
type = "cmd"
run = "python3 -m pytest test_calc.py -q"
timeout = 60

# rust-04
[[checks]]
type = "cmd"
run = "cargo test --quiet"
timeout = 120

# ts-04
[[checks]]
type = "cmd"
run = "npm test"
timeout = 60
```

For `py-02-plan-only` (reuse golden-02 pattern, `tests/eval/golden/02-plan-only/task.toml` line 15-17):
```toml
mode = "plan"
# no auto_approve_edits (defaults false)
[[checks]]
type = "cmd"
run = "git diff --quiet HEAD"
```

For `py-05-resume` (reuse golden-05 pattern, `tests/eval/golden/05-resume/task.toml` line 18-20):
```toml
[[checks]]
type = "cmd"
run = "test -f notes.txt"
```

For `py-06-fetch-summarize` (reuse golden-06 pattern, `tests/eval/golden/06-fetch-summarize/task.toml` lines 14-21):
```toml
tools = ["web_fetch", "fs_write"]

[[checks]]
type = "file_exists"
path = "summary.txt"

[[checks]]
type = "file_contains"
path = "summary.txt"
text = "Example"
```

---

### `tests/eval/matrix/py-*/fixture/` (Python fixtures)

**Analog:** `tests/eval/golden/02-plan-only/fixture/calc.py` (line 1-6) for source shape; `tests/eval/golden/05-resume/fixture/notes.txt` for plan-only/resume fixture shape; `tests/eval/golden/06-fetch-summarize/fixture/README.md` for fetch-summarize fixture.

**py-01-analyze / py-03-approved-edit / py-04-validation fixture** (3 files — flat layout required, see RESEARCH.md Pitfall 3):

`pyproject.toml`:
```toml
[project]
name = "calc"
version = "0.1.0"
```

`calc.py`:
```python
def add(a: int, b: int) -> int:
    return a + b
```

`test_calc.py`:
```python
from calc import add

def test_add() -> None:
    assert add(1, 2) == 3
```

**py-02-plan-only fixture** — copy `tests/eval/golden/02-plan-only/fixture/calc.py` verbatim (the add() function without type hints is the edit target).

**py-05-resume fixture** — copy `tests/eval/golden/05-resume/fixture/notes.txt` verbatim.

**py-06-fetch-summarize fixture** — copy `tests/eval/golden/06-fetch-summarize/fixture/README.md` verbatim.

---

### `tests/eval/matrix/rust-*/fixture/` (Rust fixtures)

**Analog:** `tests/eval/golden/03-approved-edit/fixture/` for multi-file shape; Cargo layout mirrors `crates/` conventions minimally.

**rust-01-analyze / rust-03-approved-edit / rust-04-validation fixture** (3 files):

`Cargo.toml` — NO `[workspace]` section (RESEARCH.md Pitfall 4):
```toml
[package]
name = "calc"
version = "0.1.0"
edition = "2021"
```

`src/lib.rs`:
```rust
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

`tests/test_add.rs`:
```rust
use calc::add;

#[test]
fn test_add() {
    assert_eq!(add(1, 2), 3);
}
```

---

### `tests/eval/matrix/ts-*/fixture/` (TypeScript fixtures)

**Analog:** `tests/eval/golden/03-approved-edit/fixture/` for source + test shape; `node --experimental-strip-types` replaces `tsc` (no global tsc, RESEARCH.md §Standard Stack).

**ts-01-analyze / ts-03-approved-edit / ts-04-validation fixture** (4 files):

`package.json` — `type: "module"` required for ESM imports; NO npm install needed:
```json
{
  "name": "calc",
  "type": "module",
  "scripts": {
    "test": "node --experimental-strip-types --test src/*.test.ts"
  }
}
```

`tsconfig.json` (agent-readable only, not used by test runner — RESEARCH.md §TypeScript Fixture):
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true
  },
  "include": ["src"]
}
```

`src/calc.ts`:
```typescript
export function add(a: number, b: number): number {
  return a + b;
}
```

`src/calc.test.ts`:
```typescript
import { test } from 'node:test';
import assert from 'node:assert';
import { add } from './calc.ts';

test('add(1, 2) === 3', () => {
  assert.strictEqual(add(1, 2), 3);
});
```

---

### `voss/eval/runner.py` (extend — toolchain preflight + skip row)

**Analog:** `voss/eval/runner.py` (self) — all new code is additive to the existing `run_suite` function.

**Existing run header** (`voss/eval/runner.py` line 381) — extend this line:
```python
click.echo(f"{len(tasks)} tasks · max {max_turns} turns/task")
```
becomes:
```python
# E2: detect toolchains once before the task loop
TOOLCHAINS = {
    "py":   shutil.which("python3"),
    "rust": shutil.which("cargo"),
    "ts":   shutil.which("node"),
}
tc_line = " ".join(
    f"{lang}{'OK' if path else 'MISSING'}"
    for lang, path in TOOLCHAINS.items()
)
click.echo(f"{len(tasks)} tasks · max {max_turns} turns/task · toolchains: {tc_line}")
```

**Existing task loop top** (`voss/eval/runner.py` lines 390-395) — add skip guard before `_prepare_fixture`:
```python
for task_id, spec in tasks:
    for run_idx in range(k):
        started_at = _now_iso()
        # E2: toolchain guard — must come before _prepare_fixture
        lang = task_id.split("-")[0] if "-" in task_id else None
        if lang in TOOLCHAINS and not TOOLCHAINS.get(lang):
            _append_row(runs_path, {
                "task_id": task_id,
                "run_idx": run_idx,
                "success": None,
                "skipped": True,
                "skip_reason": "toolchain-absent",
                "gate_pass": None,
                "capped": False,
                "checks": [],
                "cost_usd": None,
                "confidence": None,
                "duration_s": 0.0,
                "judge_verdict": "skipped",
                "judge_confidence": 0.0,
                "judge_rationale": f"skipped: toolchain-absent ({lang})",
                "provider": "n/a",
                "model": "n/a",
                "judge_model": "n/a",
                "live": live,
                "seed": run_idx,
                "voss_version": VOSS_VERSION,
                "started_at": started_at,
            })
            continue
        start = time.monotonic()
        with tempfile.TemporaryDirectory(...) as tmp:
            ...
```

**`_append_row` pattern** (`voss/eval/runner.py` lines 133-136) — skip row uses this function exactly as normal rows do:
```python
def _append_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
```

**`shutil.which` import** — already in `import shutil` at line 8; `shutil.which` mirrors the pattern in `voss/harness/diagnostics.py` lines 471-477:
```python
tools = {name: shutil.which(name) for name in ("node", "pnpm", "cargo")}
```

**`--require-all-toolchains` enforcement** — add after TOOLCHAINS detection, mirrors the `--live/--stub` mutex at lines 364-365:
```python
if require_all_toolchains and any(path is None for path in TOOLCHAINS.values()):
    missing = [lang for lang, path in TOOLCHAINS.items() if path is None]
    raise click.UsageError(f"--require-all-toolchains: missing toolchains: {missing}")
```

---

### `voss/eval/summary.py` (extend — skipped column)

**Analog:** `voss/eval/summary.py` lines 60-68 (gate/judge aggregation pattern):
```python
gate_rows = [r for r in rows if r.get("gate_pass") is not None]
gate_passes = sum(1 for r in gate_rows if r["gate_pass"])
gate_rate = gate_passes / len(gate_rows) if gate_rows else None

judge_rows = [
    r for r in rows if r.get("judge_verdict") not in (None, "skipped", "error")
]
judge_passes = sum(1 for r in judge_rows if r.get("judge_verdict") == "pass")
judge_rate = judge_passes / len(judge_rows) if judge_rows else None
```

Add skipped aggregation after the same pattern:
```python
# E2: skipped count (toolchain-absent rows have skipped=True)
skipped_rows = [r for r in rows if r.get("skipped") is True]
skipped_count = len(skipped_rows)
```

Pass `skipped_count` to the jinja template and add to the rendered output. Mirror the existing `gate_passes`/`gate_total` pair: `skipped_count` goes in the header block and a `skipped` column in the per-task table.

**Template extension pattern** — `voss/templates/eval/summary.md.jinja` lines 6-7 (add after `judge pass rate` line):
```
- skipped (toolchain-absent): {{ skipped_count }}
```

Per-task table — existing column set (`summary.md.jinja` line 13):
```
| task | runs | gate pass | pass rate | mean cost |
```
Add `skipped` column:
```
| task | runs | gate pass | skipped | pass rate | mean cost |
```

For per-task skipped count in `summary.py` lines 81-96, add inside the task loop:
```python
task_skipped = sum(1 for row in task_rows if row.get("skipped") is True)
tasks.append({
    "id": task_id,
    "runs": len(task_rows),
    "gate_pass_rate": gate_pass_rate,
    "skipped": str(task_skipped),   # NEW
    "pass_rate": rate,
    "mean_cost": cost_s,
})
```

---

### `voss/harness/cli.py` (extend eval_cmd — `--require-all-toolchains` flag)

**Analog:** `voss/harness/cli.py` lines 3492-3543 (the existing `eval_cmd` registration).

**Existing flag pattern** (lines 3514-3514 — `--max-turns` is the most recently added flag):
```python
@click.option("--max-turns", "max_turns", default=None, type=int, help="Turn cap per task (overrides config default).")
```

Add immediately after, same decorator style:
```python
@click.option(
    "--require-all-toolchains",
    "require_all_toolchains",
    is_flag=True,
    default=False,
    help="Fail run if python3/cargo/node is absent (strict mode).",
)
```

Add to function signature and `run_suite` call:
```python
def eval_cmd(
    suite: str,
    stub: bool,
    live: bool,
    k: int,
    out_path: Path,
    judge_model: str | None,
    task: str | None,
    auth_pref: str,
    max_turns: int | None,
    require_all_toolchains: bool,   # NEW
) -> None:
    ...
    run_suite(
        ...
        require_all_toolchains=require_all_toolchains,  # NEW
    )
```

**`run_suite` signature** (`voss/eval/runner.py` lines 347-361) — add `require_all_toolchains: bool = False`:
```python
def run_suite(
    *,
    suite: str = "golden",
    stub: bool = False,
    live: bool = False,
    k: int = 1,
    out: Path | None = None,
    out_dir: Path | None = None,
    judge_model: str | None = None,
    task: str | None = None,
    task_id: str | None = None,
    auth_pref: str = "auto",
    model: str | None = None,
    max_turns: int | None = None,
    require_all_toolchains: bool = False,   # NEW
) -> Path:
```

---

### `tests/eval/test_matrix_suite.py` (test, CRUD)

**Primary analog:** `tests/eval/test_golden_checks.py` lines 1-70

**Import pattern** (`tests/eval/test_golden_checks.py` lines 1-10):
```python
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from voss.eval.suite import CmdCheck, FileExistsCheck, load_suite
```

**Suite loader test pattern** (`tests/eval/test_golden_checks.py` lines 33-52):
```python
def test_all_golden_tasks_have_checks() -> None:
    repo = _repo_root()
    tasks = load_suite(Path("tests/eval/golden"), suite="golden")
    assert len(tasks) == 6
    assert all(len(spec.checks) >= 1 for _, spec in tasks)

    by_id = dict(tasks)
    analyze_checks = by_id["01-analyze"].checks
    assert any(
        isinstance(c, FileExistsCheck) and c.path == ".voss/architecture.md"
        for c in analyze_checks
    )
```

**For matrix test, copy this pattern with suite="matrix":**
```python
def test_all_matrix_tasks_have_checks() -> None:
    tasks = load_suite(Path("tests/eval/matrix"), suite="matrix")
    assert len(tasks) == 12
    assert all(len(spec.checks) >= 1 for _, spec in tasks), \
        "every matrix task must have at least one deterministic check"
```

**`_repo_root` helper** (`tests/eval/test_golden_checks.py` lines 12-13) — copy verbatim:
```python
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
```

---

### `tests/eval/test_matrix_runner.py` (test, request-response)

**Primary analog:** `tests/eval/test_hybrid_gate.py` lines 1-187

**Monkeypatch + run_suite call pattern** (`tests/eval/test_hybrid_gate.py` lines 56-72):
```python
def test_gate_overrides_judge(golden_repo_root: Path, tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "out"
    monkeypatch.chdir(golden_repo_root)
    monkeypatch.setattr(runner, "_judge_provider_for_eval", lambda *, auth_pref: StubProvider())
    monkeypatch.setattr(
        runner,
        "judge_run",
        AsyncMock(return_value=(Verdict(verdict="pass", confidence=0.9, rationale="ok"), "pass")),
    )
    runner.run_suite(stub=True, auth_pref="none", task="gate-task", out=out)
    row = _read_rows(out / "runs.jsonl")[0]
    assert row["gate_pass"] is False
```

**Run header capture pattern** (`tests/eval/test_hybrid_gate.py` lines 137-157):
```python
def test_run_header_prints(tmp_path: Path, monkeypatch, capsys) -> None:
    ...
    runner.run_suite(stub=True, auth_pref="none", task="header-task", out=out, max_turns=3)
    captured = capsys.readouterr()
    assert "tasks · max" in captured.out
    assert "turns/task" in captured.out
```

Copy and extend for preflight test:
```python
def test_preflight_prints_toolchain_availability(tmp_path: Path, monkeypatch, capsys) -> None:
    # monkeypatch shutil.which to return None for "cargo"
    ...
    runner.run_suite(stub=True, ..., suite="matrix", ...)
    captured = capsys.readouterr()
    assert "toolchains:" in captured.out
    assert "py" in captured.out
    assert "rust" in captured.out
    assert "ts" in captured.out
```

**`_write_task` helper** (`tests/eval/test_hybrid_gate.py` lines 23-28) — copy for matrix task creation in tests:
```python
def _write_task(root: Path, task_id: str, task_toml: str) -> None:
    task_dir = root / "tests" / "eval" / "matrix" / task_id   # "matrix" not "golden"
    fixture = task_dir / "fixture"
    fixture.mkdir(parents=True)
    (fixture / "README.md").write_text("# Fixture\n")
    (task_dir / "task.toml").write_text(task_toml)
```

---

### `tests/eval/test_matrix_stub.py` (test, request-response)

**Primary analog:** `tests/eval/test_voss_eval_stub.py` lines 1-227

**`_run_eval` subprocess helper** (`tests/eval/test_voss_eval_stub.py` lines 38-49) — copy verbatim, add `--suite matrix`:
```python
def _run_eval(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    repo = str(_repo_root())
    env["PYTHONPATH"] = repo + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "voss.cli", "eval", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
```

**Per-task golden stub pattern** (`tests/eval/test_voss_eval_stub.py` lines 207-227):
```python
@pytest.mark.parametrize(
    "task_id",
    ["01-analyze", "02-plan-only", "03-approved-edit", ...],
)
def test_existing_golden_tasks_stub(task_id: str, tmp_path: Path) -> None:
    repo = _repo_root()
    if not (repo / "tests" / "eval" / "golden" / task_id / "task.toml").exists():
        pytest.skip(f"golden task not present: {task_id}")
    out = tmp_path / task_id
    result = _run_eval(
        ["--stub", "--auth", "none", "--task", task_id, "-k", "1", "--out", str(out)],
        cwd=repo,
    )
    assert result.returncode == 0, result.stderr
    rows = _read_rows(out / "runs.jsonl")
    assert len(rows) == 1
    assert set(rows[0]) == REQUIRED_FIELDS
```

Adapt for matrix: parametrize over the 12 matrix cell IDs, switch path to `tests/eval/matrix/`, pass `--suite matrix`.

**REQUIRED_FIELDS sentinel** (`tests/eval/test_voss_eval_stub.py` lines 11-31) — extend for skip row fields:
```python
REQUIRED_FIELDS = {
    "task_id", "run_idx", "success", "cost_usd", "confidence",
    "duration_s", "judge_verdict", "judge_confidence", "judge_rationale",
    "provider", "model", "judge_model", "live", "seed", "voss_version",
    "started_at", "gate_pass", "capped", "checks",
}
# Skip rows add: "skipped", "skip_reason" — test separately
```

---

### `tests/eval/test_matrix_summary.py` (test, transform)

**Primary analog:** `tests/eval/test_summary_md.py` lines 1-145

**`_write_rows` helper** (`tests/eval/test_summary_md.py` lines 9-11) — copy verbatim:
```python
def _write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
```

**Exact-bytes test pattern** (`tests/eval/test_summary_md.py` lines 47-90) — copy structure, update expected string to include `skipped` column:
```python
def test_summary_renders_skipped_column(tmp_path: Path) -> None:
    jsonl = tmp_path / "runs.jsonl"
    rows = [
        {"task_id": "py-01-analyze", "success": True, "skipped": False, ...},
        {"task_id": "rust-01-analyze", "success": None, "skipped": True,
         "skip_reason": "toolchain-absent", ...},
    ]
    _write_rows(jsonl, rows)
    text = write_summary(jsonl, tmp_path / "summary.md").read_text()
    assert "skipped" in text
    assert "| py-01-analyze |" in text
    assert "| rust-01-analyze |" in text
```

**Section assertion pattern** (`tests/eval/test_summary_md.py` lines 33-44):
```python
def test_summary_has_required_sections(tmp_path: Path) -> None:
    ...
    text = summary_path.read_text()
    assert "overall success rate" in text
    assert "gate pass rate" in text
    assert "| task | runs | gate pass | pass rate | mean cost |" in text
```
New assertion to add for matrix:
```python
assert "skipped" in text
assert "| task | runs | gate pass | skipped | pass rate | mean cost |" in text
```

---

## Shared Patterns

### VOSS_DEV=1 Gate (applies to all test files)

**Source:** `tests/eval/conftest.py` lines 1-9
```python
from __future__ import annotations

import pytest

@pytest.fixture(autouse=True)
def _set_voss_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """All eval tests run with VOSS_DEV=1 so the gated verb is accessible."""
    monkeypatch.setenv("VOSS_DEV", "1")
```

**Apply to:** All 4 new test files. The conftest.py is already in `tests/eval/` and is auto-used — no per-file addition needed. New test files only need to live in `tests/eval/` to inherit it.

### `_read_rows` Helper (applies to all runner/stub test files)

**Source:** `tests/eval/test_voss_eval_stub.py` lines 70-72 (also duplicated in `test_golden_checks.py` lines 29-31, `test_hybrid_gate.py` lines 31-33):
```python
def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]
```

**Apply to:** `test_matrix_runner.py`, `test_matrix_stub.py`, `test_matrix_summary.py`. Copy verbatim — it is the established pattern across all eval test files.

### `_repo_root` Helper (applies to suite + stub test files)

**Source:** `tests/eval/test_golden_checks.py` lines 12-13:
```python
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
```

**Apply to:** `test_matrix_suite.py`, `test_matrix_stub.py`.

### Monkeypatch Provider Pattern (applies to runner test file)

**Source:** `tests/eval/test_runner_options.py` lines 44-47 (also `test_hybrid_gate.py` lines 59-62):
```python
monkeypatch.setattr(
    runner,
    "_provider_for_eval",
    lambda *, stub, auth_pref: (StubProvider(), None),
)
monkeypatch.setattr(runner, "_judge_provider_for_eval", lambda *, auth_pref: None)
```

**Apply to:** `test_matrix_runner.py` preflight and skip tests — use these patches to avoid creds requirement while testing the toolchain logic.

### TaskSpec `extra="forbid"` (applies to all task.toml files)

**Source:** `voss/eval/suite.py` lines 41-54
```python
class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str
    mode: Literal["plan", "edit", "auto"]
    rubric: str
    judge_inputs: list[Literal["final", "file_diff"]] = ["final", "file_diff"]
    ...
    checks: list[AnyCheck] = Field(default_factory=list)
```

**Apply to:** All 12 matrix task.toml files. Only these fields are valid: `prompt`, `mode`, `rubric`, `judge_inputs`, `provider`, `model`, `auto_approve_edits`, `tools`, `checks`. No `lang` field (D-03 Approach A: lang encoded in task_id prefix).

---

## No Analog Found

All files have analogs. No matrix cell requires a pattern that doesn't exist in the codebase.

| File | Role | Data Flow | Note |
|------|------|-----------|------|
| (none) | — | — | All E2 patterns map to existing golden task + runner + test analogs |

---

## Metadata

**Analog search scope:** `tests/eval/`, `voss/eval/`, `voss/harness/cli.py`, `voss/harness/diagnostics.py`
**Files scanned:** 14 source files + 6 golden task.toml + 1 jinja template
**Key constraint confirmed:** `shutil.which` for toolchain detection is the established pattern in `voss/harness/diagnostics.py` line 471; `load_suite` works flat with any suite name via `--suite` flag; `_append_row` handles missing parent dir.
**Pattern extraction date:** 2026-06-10
