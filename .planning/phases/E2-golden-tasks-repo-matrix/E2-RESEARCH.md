# Phase E2: Golden Tasks × Repo Matrix - Research

**Researched:** 2026-06-10
**Domain:** Eval matrix expansion — per-language fixture repos + toolchain-aware runner
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — Fixture repo nature:** Synthetic-minimal, in-repo, hermetic. `tests/eval/fixtures/{python,rust,ts}/` (or under `tests/eval/matrix/`). Each language: build/dependency manifest + ONE source module with known editable function + ONE test the toolchain runs. Target <= 5 files per fixture.

**D-02 — Matrix coverage (12 cells):** Shape-sensitive tasks × all 3 languages (9 cells): analyze · approved-edit · validation × {py, rust, ts}. Language-agnostic tasks proven once on Python (3 cells): plan-only · resume · fetch-summarize. `validation` per language = native build/test (pytest / cargo test / npm test), NOT `voss check`.

**D-03 — Toolchain strategy:** Require-present + explicit recorded skip (never silent). Missing toolchain → record `skipped: toolchain-absent` in JSONL, surface in summary.md. `--require-all-toolchains` strict flag fails the run if any of python/rust/node is absent. Preflight prints toolchain availability before first model call.

**D-04 — Gates:** Both behavioral AND cognition gates using E1's `checks` types (cmd-exits-0 / file-exists / file-contains). Behavioral = toolchain test exits 0 + edit-landed file-contains. Cognition = analyze asserts `architecture.md` contains the language-correct tooling token.

### Claude's Discretion (planner)

- Exact fixture file contents and the specific editable function/test per language.
- Cell IDs / task.toml naming convention (extend `golden/NN-name` with a language axis, e.g. `golden/rust/03-approved-edit/`).
- Whether the matrix is encoded as separate task.toml dirs vs a parametrized suite over a shared task body.

### Deferred Ideas (OUT OF SCOPE)

- Full 5×3=15 matrix (plan-only/resume/fetch-summarize on rust+ts).
- Realistic vendored small repos.
- Containerized toolchains.
- More languages (Go, Java).
- `tests/e2e/` relationship.
</user_constraints>

---

## Summary

E2 adds a 12-cell repo-shape matrix to the eval substrate: golden agentic tasks (analyze, approved-edit, validation for all 3 languages; plan-only, resume, fetch-summarize Python-only) running against synthetic-minimal fixture repos. It **consumes** E1's substrate without rebuilding it.

**Critical dependency update:** E1 is more complete than the additional context suggested. E1-01 (check schema), E1-02 (dev gate + config), and E1-03 (hybrid gate/judge + turn cap + judge split + summary) are ALL executed and merged. The runner already emits `gate_pass`, `capped`, `checks` fields per JSONL row; summary.py already aggregates gate-pass and judge-pass rates; the turn cap (`max_turns=15`) is wired. What remains unexecuted: E1-04 (golden task.toml `[[checks]]` retrofit) and E1-05 (live proof run, human checkpoint). E2's fixture-building work is **independent** of E1-04/E1-05. E2's runner extensions (toolchain preflight + skip row) depend on E1-03, which is already shipped.

The primary new engineering for E2 falls into two categories: (1) **content work** — building 12 fixture directories with task.toml + language-correct fixture files, and (2) **infrastructure work** — extending `run_suite` with toolchain-aware preflight, skip-row recording, and the `--require-all-toolchains` flag.

**Primary recommendation:** Use a dedicated `tests/eval/matrix/` suite directory (not nested under `golden/`). Name cells as `{lang}-{NN}-{task}` (e.g. `py-01-analyze`, `rust-03-approved-edit`). This requires zero changes to `load_suite` — it works flat with the new `--suite matrix` flag.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fixture repos (content) | tests/eval/matrix/ | — | Static assets consumed by runner; no Python package involvement |
| Toolchain preflight | voss/eval/runner.py | voss/harness/cli.py | run_suite drives the loop; CLI surfaces the flag |
| Skip-row recording | voss/eval/runner.py | voss/eval/summary.py | runner writes JSONL; summary aggregates |
| Per-language cmd checks | task.toml `[[checks]]` | runner._run_checks | Declarative in task; executed by existing runner function |
| Cognition check (analyze) | task.toml `[[checks]]` | — | file_contains on architecture.md; same executor |
| `--require-all-toolchains` | voss/harness/cli.py | voss/eval/runner.py | CLI flag; enforced in run_suite |

---

## E1 Contract: What Exists Today

The following E1 components are **shipped and green** (66 eval tests pass):

### Current TaskSpec Schema (`voss/eval/suite.py`)
[VERIFIED: codebase read]

```python
class CmdCheck(BaseModel):
    type: Literal["cmd"]
    run: str
    timeout: int = 60  # per-check override

class FileExistsCheck(BaseModel):
    type: Literal["file_exists"]
    path: str

class FileContainsCheck(BaseModel):
    type: Literal["file_contains"]
    path: str
    text: str

class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str
    mode: Literal["plan", "edit", "auto"]
    rubric: str
    judge_inputs: list[Literal["final", "file_diff"]] = ["final", "file_diff"]
    provider: str | None = None
    model: str | None = None
    auto_approve_edits: bool = False
    tools: list[str] = Field(default_factory=list)
    checks: list[AnyCheck] = Field(default_factory=list)  # [] = judge-only fallback
```

### Current `_run_checks` Executor (`voss/eval/runner.py`)
[VERIFIED: codebase read]

- Runs ALL checks (no short-circuit). Returns `(gate_pass: bool, results: list[dict])`.
- `cmd` checks: `shell=True`, `cwd=fixture_copy`, `timeout=check.timeout` (default 60s).
- `file_exists`: `(cwd / path).exists()`.
- `file_contains`: `(cwd / path).exists() and text in (cwd / path).read_text()`.
- `gate_pass = all(r["pass"] for r in results)`.

### Current JSONL Row Fields (post E1-03)
[VERIFIED: codebase read]

```
task_id, run_idx, success, cost_usd, confidence, duration_s,
judge_verdict, judge_confidence, judge_rationale,
provider, model, judge_model, live, seed, voss_version, started_at,
gate_pass (bool), capped (bool), checks (list[dict])
```

`success` = `False` if `crash_reason or capped or not gate_pass`; `None` if no checks and judge skipped; verdict.verdict otherwise.

### Current `run_suite` Signature
[VERIFIED: codebase read]

```python
def run_suite(*, suite="golden", stub=False, live=False, k=1, out=None,
              out_dir=None, judge_model=None, task=None, task_id=None,
              auth_pref="auto", model=None, max_turns=None) -> Path
```

`suite_root = project_root / "tests/eval" / suite` — so `--suite matrix` resolves to `tests/eval/matrix/`.

### Fixture Isolation (`_prepare_fixture`)
[VERIFIED: codebase read]

```python
def _prepare_fixture(task_dir: Path, tmp: Path) -> Path:
    cwd = tmp / "fixture"
    shutil.copytree(task_dir / "fixture", cwd)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=cwd, ...)
    subprocess.run(["git", "add", "-A"], cwd=cwd, ...)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=cwd, ...)
    return cwd
```

`task_dir = suite_root / task_id`. The fixture copy is a fresh git repo. Checks run in `cwd` (the copy).

### E1 Remaining Unexecuted Plans
[VERIFIED: codebase read]

- **E1-04** (Wave 3): Retrofit `[[checks]]` onto all 6 golden `task.toml` files. Independent of E2.
- **E1-05** (Wave 4, human checkpoint): Live codex-auth proof run. E2's live matrix proof run CANNOT run until E1-05 shows ≥5/6 gate_pass on the existing golden suite first.

### What E1 Does NOT Yet Provide for E2
[VERIFIED: codebase read]

1. **Skip-row recording** — `run_suite` has no `skipped: toolchain-absent` path. The current row shape has no `skipped` field.
2. **Toolchain preflight print** — the existing run header is `"N tasks · max M turns/task"`; no toolchain availability section.
3. **`--require-all-toolchains` flag** — not yet registered in CLI.
4. **summary.md skipped column** — template only shows gate-pass and judge-pass columns; no skipped count.

All four are new E2 work in `voss/eval/runner.py`, `voss/eval/summary.py`, the jinja template, and `voss/harness/cli.py`.

---

## Standard Stack

No new external dependencies. E2 uses stdlib subprocess only for toolchain checks, exactly as E1 uses it for `_run_checks`. [VERIFIED: E1 spec constraint + codebase read]

### Toolchain Detection
[VERIFIED: codebase read — `shutil.which` is the established pattern in `voss/harness/diagnostics.py`]

```python
import shutil
TOOLCHAINS = {
    "python": shutil.which("python3"),
    "rust":   shutil.which("cargo"),
    "ts":     shutil.which("node"),   # node covers both npm test and node --test
}
```

Detection key per language:
- **Python**: `shutil.which("python3")` — present on this machine: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3`
- **Rust**: `shutil.which("cargo")` — present: `/Users/benjaminmarks/.cargo/bin/cargo` (cargo 1.95.0-nightly)
- **TypeScript/Node**: `shutil.which("node")` — present: `/Users/benjaminmarks/.local/bin/node` (v22.22.3)

`tsc` is NOT globally installed (only in `apps/voss-app/node_modules/.bin/`). TypeScript fixtures must NOT require a global `tsc` — use `node --experimental-strip-types` for test execution.

---

## Architecture Patterns

### System Architecture: E2 Data Flow

```
VOSS_DEV=1 voss eval --suite matrix [--require-all-toolchains]
     |
     v
eval_cmd (voss/harness/cli.py)
     |  VOSS_DEV gate (E1-02)
     |
     v
run_suite(suite="matrix", ...)
     |
     |-- [E2 NEW] toolchain_preflight()
     |      shutil.which("python3" / "cargo" / "node")
     |      click.echo("toolchains: py✓ rust✓ ts✓")
     |      prints BEFORE first model call
     |
     |-- [E2 NEW] per-task toolchain guard
     |      if toolchain absent → _append_row(skipped row) + continue
     |
     |-- _prepare_fixture(suite_root / task_id, tmp)
     |      copytree(fixture/) + git init + git commit
     |
     |-- _drive_task(task_id, spec, cwd=fixture_copy, max_turns=15)
     |      run_turn loop (turns ≤ max_turns)
     |      returns (record, final, crash_reason, capped)
     |
     |-- _run_checks(spec.checks, cwd=fixture_copy)
     |      cmd / file_exists / file_contains
     |      returns (gate_pass, check_results)
     |
     |-- judge_run (if not capped, not crash, checks pass, judge_provider)
     |
     v
_append_row(.voss/eval/<run>/runs.jsonl, row)
     |
     v
write_summary(runs_path, summary_path)
     |  gate-pass rate, judge-pass rate, [E2 NEW] skipped count
     v
summary.md
```

### Recommended Project Structure

```
tests/eval/
├── golden/              # E1 suite (6 tasks, unchanged by E2)
│   ├── 01-analyze/
│   └── ...
└── matrix/              # E2 suite (12 cells, new)
    ├── py-01-analyze/
    │   ├── task.toml
    │   └── fixture/
    │       ├── pyproject.toml
    │       ├── calc.py
    │       └── test_calc.py
    ├── py-02-plan-only/
    ├── py-03-approved-edit/
    ├── py-04-validation/
    ├── py-05-resume/
    ├── py-06-fetch-summarize/
    ├── rust-01-analyze/
    │   ├── task.toml
    │   └── fixture/
    │       ├── Cargo.toml
    │       ├── src/lib.rs
    │       └── tests/test_add.rs
    ├── rust-03-approved-edit/
    ├── rust-04-validation/
    ├── ts-01-analyze/
    │   ├── task.toml
    │   └── fixture/
    │       ├── package.json
    │       ├── tsconfig.json (type-annotation aid for agent)
    │       ├── src/calc.ts
    │       └── src/calc.test.ts
    ├── ts-03-approved-edit/
    └── ts-04-validation/
```

### Pattern 1: Toolchain-Aware Skip Row
[DERIVED from E1 JSONL row schema + D-03 requirements]

The skip row is a new JSONL shape for toolchain-absent cells. It must NOT look like a FAIL (gate_pass=false) — it must be visually distinguishable in summary.md.

```python
# In run_suite, before _prepare_fixture:
lang = _task_lang(task_id)  # "py" | "rust" | "ts" | None
if lang and not toolchains_available.get(lang):
    _append_row(runs_path, {
        "task_id": task_id,
        "run_idx": run_idx,
        "success": None,
        "skipped": True,
        "skip_reason": "toolchain-absent",
        "gate_pass": None,
        "capped": False,
        "checks": [],
        # ... other required fields with None/defaults
    })
    continue
```

`_task_lang` extracts the language prefix from task_id: `"py-01-analyze".split("-")[0]` → `"py"`.

### Pattern 2: TOML `[[checks]]` for Per-Language Gates
[VERIFIED: E1-04 plan + existing TOML pattern in golden tasks]

```toml
# Behavioral gate: toolchain test exits 0
[[checks]]
type = "cmd"
run = "python3 -m pytest test_calc.py -q"
timeout = 60

# Behavioral gate: edit landed (new name present)
[[checks]]
type = "file_contains"
path = "calc.py"
text = "sum_two"

# Cognition gate: analyze mentions Python tooling
[[checks]]
type = "file_contains"
path = ".voss/architecture.md"
text = "pyproject"
```

### Pattern 3: Preflight Print Extension
[DERIVED from E1-03 run header pattern + D-03]

```python
# Extend existing run header: "N tasks · max M turns/task"
# with toolchain availability, before the task loop:
tc_line = " ".join(
    f"{lang}{'✓' if avail else '✗'}"
    for lang, avail in [("py", py_avail), ("rust", rust_avail), ("ts", ts_avail)]
)
click.echo(f"{len(tasks)} tasks · max {max_turns} turns/task · toolchains: {tc_line}")
```

### Anti-Patterns to Avoid

- **Silent toolchain skip:** a missing `cargo` that causes cmd-check failure would record FAIL, not `skipped: toolchain-absent`. The planner must add explicit toolchain detection before `_prepare_fixture` is called.
- **Installing npm packages in fixture:** `npm test` works without `npm install` for `node --experimental-strip-types --test` since `node:test` is built-in and no external modules are needed. Do not add a `scripts.pretest: "npm install"` step.
- **Using `tsc` for test execution:** `tsc` is not globally available. TypeScript fixtures use `node --experimental-strip-types --test` via npm test. The `tsconfig.json` is for agent-readability (analyze cognition), not for compilation gates.
- **Nested dirs in `tests/eval/golden/`:** `load_suite` iterates flat — subdirs without `task.toml` are silently skipped. Put the matrix in `tests/eval/matrix/` (a separate `--suite matrix`), not nested under `golden/`.
- **cargo workspace conflicts:** Rust fixtures must NOT have a `[workspace]` section. Running `cargo test` in an isolated temp dir that is not the Voss repo works fine as long as the fixture `Cargo.toml` is self-contained.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Toolchain detection | Custom `subprocess.run(["cargo", "--version"])` | `shutil.which("cargo")` | Already the established pattern in `diagnostics.py`; `which` is faster than spawning a subprocess |
| cmd check execution | Custom subprocess wrapper | `_run_checks` (E1 executor) | Already handles timeout, cwd, shell=True, no-short-circuit |
| Fixture isolation | Custom copytree logic | `_prepare_fixture` (M5 D-06) | Already does copytree + git init + commit |
| JSONL writing | Custom JSON writer | `_append_row` | Already handles path creation + append-open |
| TypeScript test runner | Jest/Mocha/vitest in fixture deps | `node --experimental-strip-types --test` | Built into Node v22; zero install; no node_modules needed |

---

## Fixture Specifications

### Python Fixture (flat layout)
[VERIFIED: tested locally — `python3 -m pytest test_calc.py -q` passes in isolated temp dir]

**Files (3 total, ≤ D-01 limit):**

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

**Editable function:** `add` → rename to `sum_two` for approved-edit.
**Test command:** `python3 -m pytest test_calc.py -q`
**Why flat (not src/):** `python3 -m pytest` finds `calc.py` at cwd root without `pip install -e .` needed in the isolated temp fixture.

### Rust Fixture
[VERIFIED: tested locally — `cargo test --quiet` passes in isolated temp dir]

**Files (3 total, ≤ D-01 limit):**

`Cargo.toml`:
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

**Editable function:** `add` → rename to `sum_two` for approved-edit.
**Test command:** `cargo test --quiet`
**Why integration test in `tests/`:** Keeps `src/lib.rs` clean as the only edit target; `cargo test` picks it up automatically. No `src/main.rs` needed.
**Note:** `cargo test` is slow first run due to compilation (~3–8s on a cold fixture). The per-task turn cap is 15; leave `timeout = 120` for cargo cmd checks.

### TypeScript Fixture
[VERIFIED: tested locally — `npm test` passes without npm install, using `node --experimental-strip-types --test`]

**Files (4 total, ≤ D-01 limit):**

`package.json`:
```json
{
  "name": "calc",
  "type": "module",
  "scripts": {
    "test": "node --experimental-strip-types --test src/*.test.ts"
  }
}
```

`tsconfig.json` (for agent-readable type annotation; not used by test runner):
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

**Editable function:** `add` → rename to `sumTwo` for approved-edit.
**Test command:** `npm test` (no npm install required — node:test is built-in)
**Why no `tsc --noEmit` gate:** `tsc` is not globally installed on this machine. The type-checking signal comes from the agent's own type-correct edit; behavioral correctness is confirmed by the test running.

---

## Per-Cell Check Specifications (D-04)

### Analyze Cells (py-01, rust-01, ts-01)

**Task:** "Analyze this repository and write architecture.md describing what it does."
**Mode:** edit, auto_approve_edits: true

**Checks:**

| Check type | Path/Command | Text | Purpose |
|------------|-------------|------|---------|
| file_exists | `.voss/architecture.md` | — | Behavioral: file was created |
| file_contains | `.voss/architecture.md` | `pyproject` / `Cargo.toml` / `package.json` | Cognition: language-correct tooling named |

Cognition token per language:
- Python: `pyproject` (pyproject.toml is the manifest)
- Rust: `Cargo.toml`
- TypeScript: `package.json`

The analyze task prompt (`bootstrap_prompt` path) leads the agent to mention the manifest in the architecture body. Even a minimal prompt like the E1 golden-01 prompt ("Analyze this repository and write architecture.md describing what it does.") reliably produces architecture docs that mention the manifest when the fixture has one.

### Approved-Edit Cells (py-03, rust-03, ts-03)

**Task:** "Rename the function `add()` to `sum_two()` (Python/Rust) or `sumTwo()` (TypeScript) and update its single call site in the test file."
**Mode:** edit, auto_approve_edits: true

**Checks:**

| Check type | Path/Command | Text | Purpose |
|------------|-------------|------|---------|
| file_contains | `calc.py` / `src/lib.rs` / `src/calc.ts` | `sum_two` / `sumTwo` | New name landed |
| cmd | `! grep -q 'def add(' calc.py` (py) / `! grep -q 'fn add(' src/lib.rs` (rust) / `! grep -q 'function add(' src/calc.ts` (ts) | — | Old name removed |
| cmd | `python3 -m pytest test_calc.py -q` / `cargo test --quiet` / `npm test` | — | Test suite green after edit |

### Validation Cells (py-04, rust-04, ts-04)

**Task:** "Run the project's test suite and report the exit code."
**Mode:** edit, auto_approve_edits: true

**Checks:**

| Check type | Path/Command | Text | Purpose |
|------------|-------------|------|---------|
| cmd | `python3 -m pytest test_calc.py -q` / `cargo test --quiet` / `npm test` | — | Native test suite exits 0 |

The validation cell proves the agent can correctly invoke the repo's native test toolchain — distinct from E1's `voss check sample.voss` pattern.

### Python-Only Cells

**py-02-plan-only:** Reuse E1 golden-02 fixture. Check: `cmd git diff --quiet HEAD` (no writes in plan mode).
**py-05-resume:** Reuse E1 golden-05 fixture. Check: `cmd test -f notes.txt` (cheap fixture-intrinsic gate).
**py-06-fetch-summarize:** Reuse E1 golden-06 fixture + tools pattern. Checks: `file_exists summary.txt` + `file_contains summary.txt "Example"`.

These three cells can SHARE the golden/0N-*/fixture directory contents — the fixture isolation copies the tree, so the task.toml in matrix/ can point at an identical fixture layout. This is the simplest approach: copy the fixture directory from golden/ into the matrix/ task dirs, so each matrix task is self-contained.

---

## E1/E2 Dependency Boundary

### E2 Work Independent of E1-04 and E1-05 (can build NOW)

- Build all 12 fixture directories (`tests/eval/matrix/*/fixture/`)
- Write all 12 `task.toml` files with `[[checks]]`
- Write unit tests loading the matrix suite under stub
- Write toolchain preflight function (no exec required for tests)

### E2 Work Depending on E1-03 (ALREADY SHIPPED)

- Toolchain skip row uses the same `_append_row` interface — E1-03 done.
- cmd-exit-0 checks for `cargo test` / `npm test` / `python3 -m pytest` use `_run_checks` — E1-01/E1-03 done.
- `gate_pass` and `checks` fields in JSONL row — E1-03 done.

### E2 Work Depending on E1-05 (NOT DONE)

- The E2 **live proof run** on codex auth should run only after E1's live proof run has established a working baseline (≥5/6 gate_pass on the golden suite). This is a sequencing convention, not a code dependency. The planner should gate the E2 live-run wave behind E1-05.

### Precise E1 State at Research Time
[VERIFIED: codebase read + 66 eval tests green]

| E1 Plan | Status | E2 Impact |
|---------|--------|-----------|
| E1-01: check schema + `_run_checks` | DONE | E2 uses `_run_checks` directly — no work needed |
| E1-02: dev gate + `[eval]` config | DONE | E2 works under `VOSS_DEV=1` — no work needed |
| E1-03: hybrid gate + cap + judge split + summary | DONE | E2 runner extensions build on this; skip-row is additive |
| E1-04: golden task.toml `[[checks]]` retrofit | NOT DONE | Independent of E2; E2 planner should note this as parallel work |
| E1-05: live proof run (human checkpoint) | NOT DONE | E2 live run should be gated after E1-05 |

---

## Toolchain Skip Implementation Details

The `run_suite` loop needs to know which language each task targets. Two approaches:

**Approach A (recommended): task_id prefix convention.** Cell IDs `py-*`, `rust-*`, `ts-*` encode the language. `_task_lang(task_id)` = `task_id.split("-")[0]` → one of `"py"`, `"rust"`, `"ts"`. Fails gracefully for `None` (lang-agnostic or unexpected prefix → no skip).

**Approach B: TaskSpec field.** Add `lang: str | None = None` to TaskSpec and put it in task.toml. More explicit but requires schema change.

Approach A works with zero schema changes and zero additions to TaskSpec. The planner should use Approach A.

**Skip row schema extension:**

```python
# New fields additive to existing row; existing analysis code uses .get() everywhere
row = {
    "task_id": task_id,
    "run_idx": run_idx,
    "success": None,
    "skipped": True,           # NEW
    "skip_reason": "toolchain-absent",  # NEW
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
}
```

---

## Common Pitfalls

### Pitfall 1: Cargo Test in Fixture Is Slow (First Compile)
**What goes wrong:** `cargo test` on a fresh fixture dir compiles from scratch — 8–20 seconds depending on machine. The default cmd check timeout is 60s. If build artifacts from a previous `cargo build` are NOT present (they aren't, since the fixture is copied to a fresh temp dir), the first compile can be slow.
**Why it happens:** Each `_prepare_fixture` call creates a fresh temp dir with no `.cargo/` target cache.
**How to avoid:** Set `timeout = 120` on Rust `cmd` checks. For the approved-edit test suite re-run, the `cargo test` re-compile is minimal (only the integration test crate changes). The initial compile is the bottleneck.
**Warning signs:** Rust validation/approved-edit cells recording FAIL with `detail: "timeout"`.

### Pitfall 2: Node Type Stripping Warning Noise
**What goes wrong:** Node v22.22 prints `ExperimentalWarning: Type Stripping is an experimental feature...` to stderr. Depending on how cmd check detail is captured, this might look like an error.
**Why it happens:** `--experimental-strip-types` is still marked experimental in v22.
**How to avoid:** The `_run_checks` cmd executor checks `returncode == 0` for pass/fail, not stderr content. The ExperimentalWarning does NOT cause a non-zero exit code. No special handling needed. [VERIFIED: local test `npm test` exits 0 with warning noise on stderr, TAP output on stdout]

### Pitfall 3: Python Import Path in Fixture
**What goes wrong:** A `src/` layout Python fixture (e.g. `src/calc.py` + `tests/test_calc.py`) causes `ModuleNotFoundError: No module named 'calc'` when running `python3 -m pytest` without `pip install -e .`.
**Why it happens:** `python3 -m pytest` does not add subdirectories to `sys.path` automatically. Without installing the package, imports fail.
**How to avoid:** Use flat layout only: `calc.py` and `test_calc.py` at fixture root. `python3 -m pytest test_calc.py` finds both at cwd. [VERIFIED: local test]

### Pitfall 4: `cargo test` Workspace Inheritance
**What goes wrong:** If the Voss repo has a workspace `Cargo.toml`, running `cargo test` in a subdir fixture might try to use the workspace. However, fixtures are copied to a temp dir outside the repo — workspace inheritance does NOT apply in the isolated temp dir.
**Why it happens:** `cargo` walks up to find `Cargo.toml`. In an isolated temp dir (e.g. `/tmp/voss-eval-rust-03-*/fixture/`), no parent `Cargo.toml` exists.
**How to avoid:** Already handled by `_prepare_fixture`'s temp dir isolation. No extra action needed.
**Warning signs:** If test IS running in-repo (not via fixture isolation), cargo workspace would be a problem. But `run_suite` always uses `tempfile.TemporaryDirectory`.

### Pitfall 5: `analyze` Task Writes to `.voss/architecture.md` vs `VOSS.md`
**What goes wrong:** The `/analyze` skill (M8+) stages to `.voss/.analyze.staging.md` and folds into `VOSS.md`'s `id=architecture` fence. But the E1 golden-01 prompt is a simple direct prompt ("Analyze this repository and write architecture.md...") that leads the agent to write `.voss/architecture.md` directly.
**Why it happens:** The eval task prompt is not the same as `voss analyze` skill invocation. The golden-01 task spec uses `mode=edit` + `auto_approve_edits=true` with a direct prompt.
**How to avoid:** E2 analyze cells should use the same simple prompt pattern as E1 golden-01: `"Analyze this repository and write architecture.md describing what it does."` The file_exists check targets `.voss/architecture.md`. The `cognition.py` fallback path explicitly reads `.voss/architecture.md` when `VOSS.md` is absent. [VERIFIED: cognition.py `_is_initialized` checks both paths]

### Pitfall 6: Missing `[[checks]]` Blocks vs Empty Checks
**What goes wrong:** If a task.toml has no `[[checks]]` blocks, `spec.checks = []` and `_run_checks` returns `(True, [])` — vacuous pass. The gate_pass is True even though nothing was checked. This defeats the anti-false-green mission.
**Why it happens:** Empty checks list is the judge-only fallback by design (back-compat). But it means a task with no checks and a judge that says "pass" will have both `gate_pass=True` and `success=True` without any deterministic gate.
**How to avoid:** Every matrix cell MUST have at least one deterministic check. The planner should add a test that asserts all matrix task specs have `len(spec.checks) >= 1`.

---

## Environment Availability

[VERIFIED: local environment probes]

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| python3 | Python fixture tests | Yes | 3.13.5 | — |
| pytest | Python cmd checks (`python3 -m pytest`) | Yes | 8.4.2 (via system + .venv) | — |
| cargo | Rust fixture tests | Yes | 1.95.0-nightly | `skipped: toolchain-absent` |
| node | TypeScript fixture tests | Yes | v22.22.3 | `skipped: toolchain-absent` |
| npm | TypeScript test cmd (`npm test`) | Yes | 10.9.8 | — |
| tsc (global) | TypeScript type-checking | **NO** | — | Not used — node --experimental-strip-types covers tests |
| git | `_prepare_fixture` (git init) | Yes | (in PATH) | — |

**All three toolchains are available on this machine.** The matrix can run all 12 cells live on this developer's machine. The `--require-all-toolchains` flag would NOT skip any cells here.

**Missing dependencies with no fallback:** None for the current environment.

**Note on tsc:** TypeScript fixtures use `node --experimental-strip-types --test` for tests. No separate tsc invocation is needed for the behavioral or cognition gates. [VERIFIED: `npm test` with `node --experimental-strip-types --test src/*.test.ts` runs and exits 0 without any npm install]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | `pyproject.toml` (`[tool.pytest]`) |
| Quick run command | `.venv/bin/python -m pytest tests/eval/ -q` |
| Full suite command | `.venv/bin/python -m pytest tests/eval/ -v` |
| Current green count | 66 tests (all passing as of 2026-06-10) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVGLD-01 | All 12 matrix task specs load via `load_suite(suite="matrix")` with non-empty `checks` | unit | `.venv/bin/python -m pytest tests/eval/test_matrix_suite.py -q` | Wave 0 gap |
| EVGLD-02 | Toolchain preflight prints availability before first model call | integration/stub | `.venv/bin/python -m pytest tests/eval/test_matrix_runner.py::test_preflight_print -q` | Wave 0 gap |
| EVGLD-03 | Missing toolchain → `skipped: toolchain-absent` row in JSONL, not FAIL | unit/stub | `.venv/bin/python -m pytest tests/eval/test_matrix_runner.py::test_toolchain_skip -q` | Wave 0 gap |
| EVGLD-04 | `--require-all-toolchains` flag fails run when a toolchain is absent | integration/stub | `.venv/bin/python -m pytest tests/eval/test_matrix_runner.py::test_require_all_toolchains -q` | Wave 0 gap |
| EVGLD-05 | py-03-approved-edit: `sum_two` lands in calc.py + test passes | stub (gate only) | `.venv/bin/python -m pytest tests/eval/test_matrix_stub.py::test_py_approved_edit_checks -q` | Wave 0 gap |
| EVGLD-06 | rust-01-analyze: architecture.md contains `Cargo.toml` | stub | `.venv/bin/python -m pytest tests/eval/test_matrix_stub.py::test_rust_analyze_checks -q` | Wave 0 gap |
| EVGLD-07 | ts-04-validation: `npm test` exits 0 in fixture | cmd-execution test | `.venv/bin/python -m pytest tests/eval/test_matrix_stub.py::test_ts_validation_checks -q` | Wave 0 gap |
| EVGLD-08 | Full 12-cell stub suite completes without errors | integration/stub | `.venv/bin/python -m pytest tests/eval/test_matrix_stub.py::test_full_matrix_stub_run -q` | Wave 0 gap |
| EVGLD-09 | summary.md shows `skipped` count per lang when toolchain absent | unit | `.venv/bin/python -m pytest tests/eval/test_matrix_summary.py -q` | Wave 0 gap |
| EVGLD-10 | Live matrix proof run (≥9/12 gate_pass, 0 capped) | LIVE (human checkpoint) | `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --suite matrix --auth codex` | manual |

### Hermetic vs Live Boundary

- **Hermetic (stub):** All fixture loading, toolchain preflight detection, skip-row recording, JSONL structure, summary.md aggregation. These do not require model calls.
- **Live (codex auth):** Agent driving the actual tasks. Requires `VOSS_DEV=1` + codex creds. Gated after E1-05.
- **Toolchain cmd tests (special case):** The `cargo test`, `npm test`, `python3 -m pytest` commands in checks DO run in the test suite (they execute in isolated temp dirs). These are real toolchain invocations but do not require model calls.

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/eval/ -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/eval/ -v`
- **Phase gate:** Full suite green before any live run attempt.

### Wave 0 Gaps

The following test files need to be created (Wave 0 scaffolding):

- [ ] `tests/eval/test_matrix_suite.py` — covers EVGLD-01 (matrix loads, all cells have checks)
- [ ] `tests/eval/test_matrix_runner.py` — covers EVGLD-02, EVGLD-03, EVGLD-04 (preflight + skip + require-all flag)
- [ ] `tests/eval/test_matrix_stub.py` — covers EVGLD-05..08 (per-cell check execution in stub mode + full stub run)
- [ ] `tests/eval/test_matrix_summary.py` — covers EVGLD-09 (summary shows skipped count)

---

## Security Domain

`security_enforcement` is not explicitly set to false in `.planning/config.json`. Applying standard review.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | E2 is internal-only; auth handled by E1 substrate |
| V3 Session Management | No | Eval sessions are ephemeral temp dirs |
| V4 Access Control | Partial | `VOSS_DEV=1` gate (E1-02) restricts `voss eval` to internal use |
| V5 Input Validation | Yes | `TaskSpec` pydantic with `extra="forbid"` validates task.toml |
| V6 Cryptography | No | No crypto in eval substrate |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via fixture files | Tampering | Fixtures are static + committed; no user-supplied content |
| `cmd` check shell injection | Tampering | Task.toml checks are developer-authored (committed); shell=True is intentional for fixture commands |
| Subscription burn via uncapped eval | Denial | `max_turns=15` cap + `VOSS_DEV=1` gate already in E1 |
| False-green from skipped toolchain cells | Spoofing | Skip rows must be visually distinct from PASS rows in summary.md (new E2 requirement) |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LLM-judge only (M5) | Hybrid gate_pass + judge | E1-03 (2026-06-10) | False-green now caught by deterministic gates |
| Single fixture shape (Python .voss) | Per-language fixture matrix | E2 (this phase) | Proves agent across project shapes |
| Single golden suite | golden + matrix suites via `--suite` flag | E2 | Separation of concerns; golden unchanged |
| No toolchain awareness | Preflight + skip recording | E2 (this phase) | No silent pass when toolchain absent |

---

## Open Questions

1. **Approved-edit test file update pattern (Rust)**
   - What we know: renaming `add` → `sum_two` in `src/lib.rs` breaks `tests/test_add.rs` which imports `calc::add`.
   - What's unclear: Should the approved-edit prompt ask the agent to update both the source AND the test? Or should the test call site be in `main.rs`?
   - Recommendation: Use `tests/test_add.rs` as the call site (parallel to Python's `main.py` call site). Prompt: "Rename `add` to `sum_two` in `src/lib.rs` and update its call site in `tests/test_add.rs`."

2. **TS approved-edit naming: `sumTwo` vs `sum_two`**
   - What we know: TypeScript/JavaScript convention for function names is camelCase (`sumTwo`). Python/Rust use snake_case (`sum_two`).
   - What's unclear: Does using different target function names per language make the file_contains checks cleaner or create confusion?
   - Recommendation: Use the idiomatic convention per language — `sumTwo` for TypeScript, `sum_two` for Python and Rust. The file_contains checks are per-file anyway.

3. **Python resume/fetch-summarize fixture reuse**
   - What we know: py-05-resume and py-06-fetch-summarize could share fixtures with E1 golden-05/06.
   - What's unclear: Should the matrix versions symlink to golden fixtures or duplicate them?
   - Recommendation: Duplicate (copy). Fixture isolation is per-task-dir; symlinks complicate `shutil.copytree`. The fixtures are small (1–2 files).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The analyze task's simple prompt reliably mentions the manifest file in architecture.md | Fixture Specs / Cognition gate | Cognition check may fail on live run — may need to strengthen the prompt or use a weaker token |
| A2 | `cargo test --quiet` exits 0 within 120s for a fresh single-crate fixture on this machine | Fixture Specs / Pitfall 1 | Rust validation cells record timeout FAIL; increase timeout or pre-warm |
| A3 | Node v22.22.3's `--experimental-strip-types` is stable enough for internal eval use | Fixture Specs | If Node upgrades to a breaking change, the flag or import syntax may need updating |

**Verified claims:** All package names, commands, and E1 code facts are VERIFIED via codebase read or local execution in this session.

---

## Sources

### Primary (HIGH confidence)
- `voss/eval/suite.py` — read directly: TaskSpec schema, AnyCheck union, checks field, load_suite mechanics
- `voss/eval/runner.py` — read directly: _prepare_fixture, _run_checks, run_suite signature, JSONL row shape (post E1-03)
- `voss/eval/judge.py`, `voss/eval/summary.py` — read directly: judge shape, summary aggregation (post E1-03)
- `voss/templates/eval/summary.md.jinja` — read directly: gate-pass + judge-pass columns present
- `tests/eval/golden/*/task.toml` — read directly: all 6 tasks, field set, fixture contents
- `.planning/phases/E1-eval-substrate/E1-01-SUMMARY.md` through `E1-03-PLAN.md` — read directly: E1 execution state
- Local execution: `python3 -m pytest test_calc.py`, `cargo test`, `npm test` with node --experimental-strip-types — all verified

### Secondary (MEDIUM confidence)
- E1-CONTEXT.md, E1-SPEC.md — read directly: E1 decisions and requirements
- E2-CONTEXT.md — read directly: locked decisions D-01..D-04

---

## Metadata

**Confidence breakdown:**
- E1 substrate state: HIGH — read code directly, ran tests (66 green)
- Fixture content: HIGH — verified all 3 toolchain patterns locally
- Toolchain availability: HIGH — verified via `shutil.which` and direct execution
- New runner extensions (skip row, preflight): MEDIUM — pattern is clear but implementation details are planner discretion
- Cognition check reliability (live): MEDIUM — based on E1 golden-01 behavior observed, but live model behavior varies

**Research date:** 2026-06-10
**Valid until:** 2026-07-10 (E1 substrate is stable; toolchain versions stable)
