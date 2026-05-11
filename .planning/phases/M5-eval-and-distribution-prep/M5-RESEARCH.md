# Phase M5: Eval and Distribution Prep - Research

**Researched:** 2026-05-11
**Domain:** Eval harness, LLM-as-judge scoring, Python wheel packaging
**Confidence:** HIGH

## Summary

M5 wires a measurement-only eval over the existing v0.1 Python harness. Every primitive it needs already exists: `voss.cli.main` Click group accepts new subcommands trivially; `RunRecord.cost_usd` (voss/harness/session.py:77) and `Plan.confidence` (voss/harness/agent.py:46) are persisted per-turn; `LiteLLMProvider.complete` (voss_runtime/providers/litellm_provider.py:32–50) already supports `response_format=<Pydantic>` JSON-mode parsing identical to the `Plan` path; `PermissionGate(auto_yes=True)` (voss/harness/permissions.py:104) is the auto-approve hook for task 03; `python -m build` is installed; `tomllib` is stdlib (python>=3.11 per pyproject); `statistics.correlation` (3.10+) gives Pearson r in one call. M2's `.voss/.gitignore` content (voss/harness/cognition.py:581) ignores only `sessions/`, so `.voss/eval/` is git-tracked by default — D-03 holds without modification.

**Primary recommendation:** Land seven tasks — (1) `voss eval` subcommand skeleton + JSONL/Markdown writer in new `voss/harness/eval.py`, (2) five golden task fixtures, (3) `Verdict` pydantic model + judge call (reuses `response_format` machinery), (4) `EVAL_AUTO_APPROVE=1` env hook on `PermissionGate`, (5) resume-task driver (in-process `asyncio.Task.cancel()`), (6) `auth.resolve(role=...)` minimal extension, (7) wheel-in-tempvenv smoke `tests/packaging/test_wheel_install.py`. Pearson r from `statistics.correlation`; no scipy.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Eval CLI orchestration | CLI / Click | — | mirrors `voss check`/`voss compile` registration |
| Golden task fixture management | Test fixtures | filesystem (tempdir) | per-run hermetic git init |
| Agent run dispatch | harness/agent.run_turn | provider | already provides cost+confidence |
| LLM-as-judge scoring | harness/eval (new) | LiteLLMProvider JSON-mode | reuses `response_format=Verdict` |
| Auto-approve simulation | harness/permissions | env var bridge | gate already has `auto_yes` |
| Resume (kill mid-turn) | asyncio task control | session_store.save/load | in-process cancel + reload |
| Packaging smoke | tests/packaging | `python -m build` + venv | extends existing pattern |
| Report artifacts | filesystem (.voss/eval) | — | durable, git-tracked |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| click | >=8.1.0 | `voss eval` subcommand | already the CLI framework [VERIFIED: pyproject.toml:19] |
| pydantic | >=2.6,<3.0 | `Verdict` model + `task.toml` schema | matches `Plan` pattern [VERIFIED: pyproject.toml:13] |
| tomllib | stdlib (3.11+) | parse `task.toml` | stdlib; project pins `requires-python>=3.11` [VERIFIED: pyproject.toml:9] |
| statistics.correlation | stdlib (3.10+) | Pearson r for EVAL-04 | one-call API; no scipy [VERIFIED: `python3 -c "from statistics import correlation"`] |
| build | dev/CI only | wheel build in smoke test | invoked via `python -m build`; installed in dev env [VERIFIED: `python3 -c "import build"` -> 1.5.0] |
| litellm | >=1.50.0 | judge provider call | reuses existing provider machinery [VERIFIED: pyproject.toml:12] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| venv (stdlib) | — | tempvenv for smoke test | `venv.create(dir, with_pip=True)` or `python -m venv` subprocess |
| asyncio (stdlib) | — | task 05 cancel/resume | `asyncio.Task.cancel()` |
| difflib (stdlib) | — | unified diff for judge_inputs `file_diff` | already used by permissions:_render_diff_preview |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `statistics.correlation` | numpy/scipy | extra dep, not justified for 15-point r |
| `tomllib` | `tomli` | unnecessary; stdlib already available |
| Subprocess kill mid-turn | in-process `asyncio.Task.cancel()` | cancel is deterministic across CI; subprocess kill races provider HTTP teardown |
| pytest parametrize per task | one driver loop in `voss eval` | the eval IS the test; pytest wrapping adds nothing |

**Installation:** No new top-level deps required. `build` is a dev/CI requirement; add to `[project.optional-dependencies] dev` if not already pulled transitively:

```bash
# pyproject.toml dev extras — add `build>=1.0` if wheel smoke needs it explicitly
pip install -e ".[dev]" build
```

**Version verification:** `build 1.5.0` confirmed present; `pyproject.toml` already declares `requires-python>=3.11` [VERIFIED: pyproject.toml:9].

## Architecture Patterns

### System Architecture Diagram

```
voss eval <flags>
    │
    ├─► auth.resolve(preference="auto"[, role="judge"])
    │       └─► provider (LiteLLM | StubProvider) — D-10, D-11
    │
    ├─► load_suite("golden")
    │       └─► tests/eval/golden/<NN>-<slug>/task.toml (tomllib)
    │
    └─► for task in suite:
        for run_idx in range(k):
            ├─► prepare_tempdir(task.fixture/)
            │       └─► shutil.copytree + git init + commit
            ├─► drive_task(task, tempdir, provider)
            │       ├─► [task 03] os.environ["EVAL_AUTO_APPROVE"]="1"
            │       ├─► [task 05] spawn run_turn → cancel mid-turn → resume
            │       └─► run_turn(...) → TurnResult{plan,cost_usd,run:RunRecord}
            ├─► extract_signals(session)
            │       ├─► cost = sum(r.cost_usd for r in session.runs)
            │       └─► confidence = session.runs[0].plan["confidence"]
            ├─► judge(task.rubric, turn.final, file_diff, judge_provider)
            │       └─► provider.complete(response_format=Verdict)
            └─► append_jsonl_row(.voss/eval/<ts>/runs.jsonl)
    │
    └─► summarize(jsonl) → .voss/eval/<ts>/summary.md
            └─► statistics.correlation(confidence[], success_01[])
```

### Recommended Project Structure
```
voss/harness/
├── eval.py                 # NEW: suite loader, judge call, writer, scorer
voss/cli.py                 # MODIFIED: register eval via harness.cli or direct
tests/eval/
├── __init__.py             # NEW
└── golden/
    ├── 01-analyze/
    │   ├── task.toml
    │   └── fixture/        # tiny seed repo files
    ├── 02-plan-only/
    ├── 03-approved-edit/
    ├── 04-validation/
    └── 05-resume/
tests/packaging/
└── test_wheel_install.py   # NEW: built-wheel-in-tempvenv smoke
```

### Pattern 1: Click subcommand registration (mirror `voss compile`)
Two equivalent paths; pick #2 to keep the agent surface co-located:

1. Add `@main.command("eval")` directly in `voss/cli.py` (next to `compile`/`check`).
2. **(Recommended)** Define `eval_cmd` in `voss/harness/cli.py` alongside `do_cmd`/`chat_cmd`, append to `AGENT_COMMANDS` tuple (voss/harness/cli.py:795), and the existing `register(main)` (voss/harness/cli.py:807, called from voss/cli.py:290) picks it up automatically.

```python
# voss/harness/cli.py — append to AGENT_COMMANDS
@click.command("eval")
@click.option("--suite", default="golden")
@click.option("--stub", is_flag=True)
@click.option("--live", is_flag=True)  # no-op; future-proof
@click.option("-k", "k", type=int, default=3)
@click.option("--out", "out_dir", type=click.Path(path_type=Path), default=None)
@click.option("--judge-model", default=None)
@click.option("--task", "task_id", default=None)
@click.option("--auth", "auth_pref", type=click.Choice(AUTH_CHOICES), default="auto")
def eval_cmd(suite, stub, live, k, out_dir, judge_model, task_id, auth_pref):
    """Run the golden eval suite and write JSONL + Markdown report."""
    from .eval import run_suite
    run_suite(suite=suite, stub=stub, k=k, out_dir=out_dir,
              judge_model=judge_model, task_id=task_id, auth_pref=auth_pref)
```

### Pattern 2: `Verdict` JSON-mode (same machinery as `Plan`)

```python
# voss/harness/eval.py
from pydantic import BaseModel, Field
class Verdict(BaseModel):
    verdict: Literal["pass", "fail"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str

resp = await provider.complete(
    messages=[{"role":"system","content":JUDGE_SYSTEM},
              {"role":"user","content":judge_prompt}],
    model=judge_model, response_format=Verdict, temperature=0.0,
)
verdict = resp.parsed  # already pydantic-validated by litellm_provider.py:48
```

`LiteLLMProvider.complete` already handles `response_format=<Pydantic>` end-to-end (parses with `model_validate_json`; raises `ParseError` on failure). Fallback for non-JSON-mode models: catch `ParseError`, re-prompt once with the validation error appended ("retry shape"), then give up and mark row `judge_verdict: "skipped"`.

### Pattern 3: Auto-approve via env var (smallest extension to `PermissionGate`)

The gate already has `auto_yes: bool` (voss/harness/permissions.py:98) which makes `needs_prompt` return False. Two options:

- **Option A (recommended):** Eval driver constructs `PermissionGate(auto_yes=True)` directly when spawning task 03 — no harness change needed.
- **Option B (env bridge, if eval drives the CLI in a subprocess):** Add a one-liner in `PermissionGate.__post_init__` or `needs_prompt`: `if os.environ.get("EVAL_AUTO_APPROVE") == "1": return False`. Keeps the contract honest for any code path that constructs a gate.

CONTEXT D-17 / Claude's discretion suggests Option B; in-process drive uses Option A. **Recommendation:** Option A (in-process). Task 03 calls `run_turn` directly with `permissions=PermissionGate(auto_yes=True)`. No code change to `permissions.py`.

### Pattern 4: Resume (task 05) — in-process cancel
```python
async def drive_resume(cwd, provider, ...):
    # Phase 1: spawn a session, run first turn, KILL mid-turn
    record = SessionRecord.new(cwd=cwd, model=model)
    task = asyncio.create_task(run_turn(prompt_1, ..., session_id=record.id))
    await asyncio.sleep(KILL_DELAY)   # or wait for first tool dispatch event
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    session_store.save(record, history)  # persist partial state
    # Phase 2: load + resume
    record, history = session_store.load(record.id, cwd=cwd)
    result = await run_turn(prompt_2, history=history, session_id=record.id, ...)
    return result
```
`SessionRecord` + `session_store.save/load` are already shaped for this (voss/harness/session.py:133–192).

### Pattern 5: Pearson r via stdlib
```python
from statistics import correlation
r = correlation([row["confidence"] for row in rows if row["confidence"] is not None],
                [1.0 if row["success"] else 0.0 for row in rows if row["confidence"] is not None])
```
~5 lines including guard for n<2.

### Pattern 6: Wheel-in-tempvenv smoke (extends tests/packaging/test_entrypoint.py:65 pattern)
```python
@pytest.mark.slow
def test_wheel_installs_and_provides_cli(tmp_path):
    # 1. Build wheel via python -m build (NO --no-deps; pull real deps so smoke is end-to-end)
    dist_dir = tmp_path / "dist"
    subprocess.run([sys.executable, "-m", "build", "--wheel", "--outdir", str(dist_dir),
                    str(_repo_root())], check=True, timeout=600)
    wheel = next(dist_dir.glob("voss-*.whl"))
    # 2. Create tempvenv
    venv_dir = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    py = venv_dir / "bin" / "python"  # or Scripts/python.exe on Windows
    voss_bin = venv_dir / "bin" / "voss"
    # 3. pip install <wheel>
    subprocess.run([str(py), "-m", "pip", "install", "-q", str(wheel)], check=True, timeout=600)
    # 4. Asserts
    for argv in [[str(voss_bin), "--help"],
                 [str(voss_bin), "compile", "samples/classify.voss"],
                 [str(voss_bin), "check", "samples/classify.voss"],
                 [str(voss_bin), "doctor"],
                 [str(py), "-c", "import voss_runtime"]]:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=60, cwd=_repo_root())
        assert r.returncode == 0, (argv, r.stderr)
    assert voss_bin.exists()
```
Existing `tests/packaging/test_entrypoint.py::test_editable_install_exposes_voss_help` (line 65) gives the venv pattern; M5 swaps `-e .` for `<wheel>` and adds assertions per D-16.

### Anti-Patterns to Avoid
- **Hand-rolled JSONL writer with custom escaping** — `json.dumps(row) + "\n"` is correct; never reach for csv-style escape.
- **Subprocess-based eval drive** — flaky on CI; in-process drive (call `run_turn` from `eval.py`) is deterministic.
- **`scipy.stats.pearsonr`** — pulls a ~80MB dep for a 5-line function; use `statistics.correlation`.
- **Reusing task 04's tempdir for task 05** — CONTEXT D-06 forbids it; each task gets a fresh fixture.
- **Stub-cost token estimation** — CONTEXT (deferred) explicitly rejects. Stub cost = `None`.
- **`--no-deps` on wheel install in smoke** — the smoke proves the wheel installs **with** its deps; `test_entrypoint.py:65` uses `--no-deps` only because it's testing editable-install of the dev tree.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TOML parsing | hand parser | `tomllib` stdlib | already in stdlib at >=3.11 |
| Pearson r | manual covariance | `statistics.correlation` | one stdlib call |
| Wheel build | shell out to `setup.py bdist_wheel` | `python -m build` | PEP 517 standard; already installed |

## Runtime State Inventory

N/A — M5 introduces new modules and files only. No renames, no migrations, no string replacements.

## Common Pitfalls

- **`task.toml` schema drift** — validate with pydantic on read; reject unknown top-level keys with a clear error.
- **`asyncio.Task.cancel()` swallowed by `except Exception` in `run_turn`** — `agent.py:235` catches `Exception` per-tool but not the outer turn; `CancelledError` is `BaseException` in 3.8+, so it propagates. Verify by inspection during plan (the catch is inside the per-step loop, not around the whole turn).
- **Judge JSON-mode unavailable for the resolved model** — `LiteLLMProvider` raises `ParseError` if `model_validate_json` fails; eval catches and marks row `judge_verdict: "skipped"`, `success: null`.
- **`.voss/eval/` shadowed by `.voss/.gitignore`** — confirmed only ignores `sessions/` (voss/harness/cognition.py:581). Safe.
- **Tempdir `git init` in CI without user.email** — pass `-c user.email=eval@voss.local -c user.name=eval` on `git commit`, or set via `git config` calls.
- **Cost = 0.0 for non-LiteLLM providers** — `AnthropicOAuthProvider` may not populate `cost_usd`. Treat 0.0 as `null` only if provider source is OAuth; or sum honestly and document zero rows.
- **`voss doctor` exit code under wheel smoke** — D-14 says exit 0 on OK or WARN-only; non-zero only on FAIL. In a clean tempvenv, `check_provider_auth` will likely FAIL (no creds). The smoke must either provide creds (live mode) or assert exit code 1 with that specific row, OR allow exit codes {0,1} and only fail on crash/missing-binary. **Recommendation:** smoke runs `voss doctor` and checks it terminates (exit ∈ {0,1}) and produces output mentioning "python" + "provider auth" — not a hard exit-0 assertion. Aligns with the loud-failure posture without blocking the smoke on missing creds.
- **`auth.resolve(role=...)` does not exist today** — the function takes only `preference` (voss/harness/auth.py:332). Smallest extension: add `role: str = ""` parameter; today it's a no-op pass-through (single judge = same provider); future versions can branch on role. Documented as a 5-line change.
- **`samples/classify.voss` compile in tempvenv** — runs from `cwd=_repo_root()` so the source file is reachable; the wheel install gives us the `voss` binary in venv but not the repo samples, so `cwd=` is required.
- **`python -m build` slow + network for build deps** — first run downloads `setuptools`/`wheel`; `@pytest.mark.slow` (D-17) is correct.

## Code Examples

### task.toml load + validate
```python
import tomllib
from pydantic import BaseModel, Field
from typing import Literal

class TaskSpec(BaseModel):
    prompt: str
    mode: Literal["plan", "edit", "auto"]
    rubric: str
    judge_inputs: list[Literal["final", "file_diff"]] = ["final", "file_diff"]
    provider: str | None = None
    model: str | None = None
    auto_approve_edits: bool = False

def load_task(task_dir: Path) -> TaskSpec:
    data = tomllib.loads((task_dir / "task.toml").read_text())
    return TaskSpec.model_validate(data)
```

### Per-task fixture isolation (D-06)
```python
import shutil, subprocess
def prepare_fixture(task_dir: Path, tmp: Path) -> Path:
    cwd = tmp / "fixture"
    shutil.copytree(task_dir / "fixture", cwd)
    subprocess.run(["git", "-C", str(cwd), "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(cwd), "-c", "user.email=eval@voss",
                    "-c", "user.name=eval", "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(cwd), "-c", "user.email=eval@voss",
                    "-c", "user.name=eval", "commit", "-q", "-m", "init"], check=True)
    return cwd
```

### Cost + confidence extraction (D-13, D-14)
```python
def extract_signals(record: SessionRecord) -> tuple[float | None, float | None]:
    if not record.runs:
        return None, None
    total_cost = sum(float(r.get("cost_usd") or 0.0) for r in record.runs)
    first_plan = record.runs[0].get("plan") or {}
    confidence = first_plan.get("confidence")
    return total_cost, (float(confidence) if confidence is not None else None)
```

### JSONL writer
```python
def append_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
```

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVAL-01 | Golden repo tasks exist for canonical demo workflow | Five fixtures under `tests/eval/golden/<NN>-<slug>/`; `task.toml` schema validated via pydantic+tomllib; per-task tempdir+git init pattern documented |
| EVAL-02 | Evaluation tracks success rate | LLM-as-judge returns `Verdict.verdict`; aggregate per task and overall in `summary.md` |
| EVAL-03 | Evaluation tracks mean cost | `RunRecord.cost_usd` (session.py:77) summed per run; mean across runs in `summary.md` |
| EVAL-04 | Evaluation tracks confidence correlation against successful and failed runs | `Plan.confidence` (agent.py:46) per first turn; Pearson r via `statistics.correlation` over (confidence, 1/0 success) pairs |
| EVAL-05 | Package install polish is verified after Python harness loop works | Wheel-in-tempvenv smoke at `tests/packaging/test_wheel_install.py`; README install section polish per D-18 |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python | runtime | ✓ | 3.11+ enforced by pyproject | — |
| tomllib | task.toml parsing | ✓ | stdlib (3.11+) | — |
| statistics.correlation | EVAL-04 r | ✓ | stdlib (3.10+) | — |
| build | wheel smoke | ✓ | 1.5.0 | `python -m pip wheel --no-deps .` (less standard) |
| git | per-task fixture init | ✓ (doctor checks) | — | — (doctor FAILs if absent; eval inherits) |
| litellm | judge JSON-mode | ✓ | >=1.50.0 pinned | — |
| Anthropic/OpenAI creds | live eval | env-dependent | — | `--stub` for CI smoke (D-11) |

**Missing dependencies with no fallback:** None at infrastructure level. At runtime, missing creds is a planned loud failure (D-10) with `--stub` opt-out.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest -q -m "not slow and not live" tests/eval tests/packaging` |
| Full suite command | `pytest -q` (includes slow + live where creds available) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVAL-01 | Five golden task fixtures present and parseable | unit | `pytest tests/eval/test_suite_loads.py -x` | ❌ Wave 0 |
| EVAL-01 | Each `task.toml` validates against `TaskSpec` | unit | `pytest tests/eval/test_task_spec.py -x` | ❌ Wave 0 |
| EVAL-02 | `voss eval --stub --task 02-plan-only -k 1` produces a JSONL row with `success` field | integration | `pytest tests/eval/test_voss_eval_stub.py -x` | ❌ Wave 0 |
| EVAL-03 | JSONL row has `cost_usd` (null under stub, float under live) | integration | `pytest tests/eval/test_voss_eval_stub.py::test_cost_field -x` | ❌ Wave 0 |
| EVAL-04 | `summary.md` includes `conf_corr_r` line; Pearson computation matches `statistics.correlation` on a fixture row set | unit | `pytest tests/eval/test_pearson.py -x` | ❌ Wave 0 |
| EVAL-04 | Live eval (creds present) populates `confidence` from `Plan.confidence` | live | `pytest -m live tests/eval/test_live_signals.py -x` | ❌ Wave 0 |
| EVAL-05 | Wheel-in-tempvenv smoke passes; `voss` binary on PATH | slow | `pytest -m slow tests/packaging/test_wheel_install.py -x` | ❌ Wave 0 |
| EVAL-05 | `import voss_runtime` from tempvenv succeeds | slow | covered by above test | ❌ Wave 0 |
| EVAL-05 | README install section contains required content (D-18) | unit | `pytest tests/packaging/test_readme.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest -q -m "not slow and not live" tests/eval tests/packaging` (~seconds; covers loaders, stub eval, Pearson)
- **Per wave merge:** `pytest -q -m "not live"` (includes wheel smoke; ~1–2 min)
- **Phase gate:** Full suite green; live tests run if creds present (skipped otherwise via `@pytest.mark.live`)

### Wave 0 Gaps
- [ ] `tests/eval/__init__.py` — package marker
- [ ] `tests/eval/test_suite_loads.py` — directory walk + count assertion (5 fixtures)
- [ ] `tests/eval/test_task_spec.py` — pydantic validation of every `task.toml`
- [ ] `tests/eval/test_pearson.py` — fixture rows → correlation matches `statistics.correlation`
- [ ] `tests/eval/test_voss_eval_stub.py` — invokes `voss eval --stub -k 1 --task 02-plan-only`, asserts JSONL row shape
- [ ] `tests/eval/test_live_signals.py` — `@pytest.mark.live` smoke for cost+confidence pull-through
- [ ] `tests/packaging/test_wheel_install.py` — wheel-in-tempvenv (slow)
- [ ] `tests/packaging/test_readme.py` — README install section content asserts

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (transitive) | reuses existing `auth.resolve` — no new credential paths in M5 |
| V3 Session Management | no | eval doesn't introduce session state beyond existing `SessionRecord` |
| V4 Access Control | yes | `PermissionGate` already enforces tier-based gating; eval drives it, does NOT bypass it (D-17 explicit) |
| V5 Input Validation | yes | `task.toml` parsed via `tomllib` and validated by pydantic `TaskSpec`; rejects unknown fields |
| V6 Cryptography | no | none introduced |
| V12 Files / Resources | yes | tempdir + path-confined fixture copy; never writes outside `.voss/eval/<ts>/` or the per-run tempdir |

### Known Threat Patterns for {Python CLI + LLM eval}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious `task.toml` triggering tool calls outside tempdir | Tampering | Tasks run with `cwd=<tempdir>`; `PermissionGate` mode and `EditScope` already path-jail writes |
| Judge prompt injection from agent output | Tampering | Judge sees structured prompt (rubric + final + diff) — diff comes from `git diff`, not raw model output; rubric authored in fixture, not by model |
| Wheel build pulls untrusted indexes | Supply chain | `python -m build` uses default index; CI environment controls; document `--no-build-isolation` only if needed |
| `.voss/eval/` accidentally committing secrets | Information disclosure | JSONL row schema is fixed-field allowlist (mirrors `SessionRecord` redaction guarantee, session.py:13–35); no creds reach the row |
| Auto-approve env leaking outside eval (task 03 Option B) | Tampering | Recommendation is Option A (in-process `auto_yes=True`); env never set |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `auth.resolve(role="judge")` extension is trivial (add `role: str = ""` param) | Pattern 2 / Q3 | If a separate-role contract needs to differ in resolution order, plan grows by one small task |
| A2 | `asyncio.Task.cancel()` propagates cleanly past `run_turn`'s per-step `except Exception` | Pitfall, Pattern 4 | If CancelledError is swallowed somewhere unexpected (e.g., a contextlib suppress), task 05 needs alternative mid-turn kill (e.g., raise from a tool wrapper) — falls back to subprocess kill |
| A3 | `python -m build` works in CI without network restrictions during smoke | EVAL-05 | If CI is offline-only for the smoke, `python -m pip wheel --no-deps .` is the fallback |
| A4 | All five demo workflow steps map cleanly to single-turn `run_turn` calls (except task 05 which is two turns) | Architecture diagram | Task 01 analyze may need the `/analyze` skill path (handle_analyze in voss/harness/cli.py:49) instead of plain `run_turn` |
| A5 | `LiteLLMProvider`'s `response_format=<Pydantic>` works against the judge model regardless of which provider serves it | Pattern 2 | Some models lack JSON-mode; `ParseError` path + skip is the documented fallback |
| A6 | Stub provider returns a stable `Plan.confidence` value so eval doesn't crash on stub | D-11 | If stub returns None or omits confidence, eval marks row `confidence: null` and Pearson computation drops it |

## Open Questions

1. **Should `voss eval` register under the agent group (`voss/harness/cli.py:AGENT_COMMANDS`) or directly on `main` in `voss/cli.py`?**
   - What we know: both work; existing agent verbs live in `harness/cli.py` and register via the `register()` helper.
   - What's unclear: whether `eval` is conceptually agent or compiler — it drives agent runs over a fixed suite.
   - Recommendation: register in `voss/harness/cli.py` for cohesion (eval imports agent, recorder, session). The plan can flip this with a one-line move.

2. **Task 01 (analyze): use `run_turn` directly with an "analyze this repo" prompt, or invoke the existing `_handle_analyze` skill path (voss/harness/cli.py:49)?**
   - What we know: M1 ships a deterministic `/analyze` skill that writes `.voss/architecture.md`.
   - What's unclear: whether the eval should measure the skill (deterministic, less informative) or the LLM agent doing the same task via planning.
   - Recommendation: measure the LLM agent path — that's what EVAL-01 actually tests. Skill is a separate code path.

3. **`docs/release.md` runbook — land in M5 or defer?**
   - What we know: CONTEXT marks it Claude's discretion / lightweight.
   - What's unclear: whether the team has appetite for a runbook page now.
   - Recommendation: defer. M5 is measurement; release-prep is its own micro-phase post-greenlight.

## Sources

### Primary (HIGH confidence)
- `voss/cli.py:121–290` — Click group + register pattern
- `voss/harness/cli.py:248–844` — agent command shape, `AGENT_COMMANDS` tuple, REPL drive
- `voss/harness/agent.py:43–283` — `Plan.confidence`, `TurnResult`, `run_turn` signature
- `voss/harness/session.py:60–254` — `RunRecord.cost_usd`, `SessionRecord.runs`, `save`/`load`
- `voss/harness/permissions.py:94–219` — `PermissionGate.auto_yes`, `mode_allows`
- `voss/harness/recorder.py:80–119` — `absorb(plan)` → `RunRecord.plan` dict round-trip
- `voss/harness/diagnostics.py:181–198` — `run_all_checks`, `aggregate_exit_code` (FAIL→1 else 0)
- `voss_runtime/providers/litellm_provider.py:32–50` — `response_format=Pydantic` JSON-mode contract
- `tests/packaging/test_entrypoint.py:65–105` — existing venv test pattern to extend
- `pyproject.toml:1–53` — deps, `requires-python>=3.11`, `voss = voss.cli:main`, `slow`/`live` markers
- `voss/harness/cognition.py:575–582` — `.voss/.gitignore` content (ignores `sessions/` only)
- Local verification: `build 1.5.0` installed; `statistics.correlation` importable; `tomllib` stdlib at 3.11+

### Secondary (MEDIUM confidence)
- CONTEXT M2 D-09 (`.voss/.gitignore` policy) — referenced via cognition.py:581
- CONTEXT M1 D-13/14 (`voss doctor` exit codes) — confirmed in diagnostics.py:194–198 and cli.py:628–640

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified present, versions confirmed
- Architecture: HIGH — every primitive eval needs already exists in the codebase
- Pitfalls: HIGH — derived from reading the actual call sites, not training data

**Research date:** 2026-05-11
**Valid until:** 2026-06-10 (stable Python tooling; ~30 days)

## RESEARCH COMPLETE

**Phase:** M5 - Eval and Distribution Prep
**Confidence:** HIGH

### Key Findings
- Every primitive eval needs already exists: `Plan.confidence`, `RunRecord.cost_usd`, `LiteLLMProvider` JSON-mode, `PermissionGate.auto_yes`, `SessionRecord.save/load`, Click `register()` helper.
- No new top-level dependencies. `tomllib` + `statistics.correlation` + `venv` + `build` cover everything; pyproject already pins python>=3.11.
- `.voss/.gitignore` (voss/harness/cognition.py:581) ignores only `sessions/` — `.voss/eval/` is git-tracked by default; CONTEXT D-03 holds.
- Auto-approve for task 03 needs no permissions.py change — driver constructs `PermissionGate(auto_yes=True)` in-process.
- Resume task uses `asyncio.Task.cancel()` after first tool dispatch; `SessionRecord.save/load` round-trips state cleanly.
- Wheel smoke extends the existing `tests/packaging/test_entrypoint.py:65` venv pattern; swap `-e .` for `<built wheel>` + add doctor/import/samples asserts.

### File Created
`.planning/phases/M5-eval-and-distribution-prep/M5-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | All deps verified present at the exact versions claimed |
| Architecture | HIGH | Read every integration point in the actual code, not just docs |
| Pitfalls | HIGH | Surfaced from concrete call-site inspection (e.g., CancelledError vs per-step except) |
| Validation Architecture | HIGH | Maps each EVAL-* to a concrete pytest command + fixture file |

### Compiler/Runtime Gaps Flagged as Sub-Plans
- **`auth.resolve(role=...)` extension** — 5-line addition (`def resolve(preference="auto", role: str = "")`). Scope as one task in plan; today's behavior is a no-op pass-through (judge = same provider). CONTEXT marks this Claude's discretion.
- **README install section polish (D-18)** — current README header (lines 1–10) says "Not on PyPI yet" and uses `pip install -e ".[dev]"`. M5 must update to `pip install voss` framing plus `voss doctor` first-run + samples + harness links + "v0.1 is a Python harness" line. Scope as a single edit task.

### Open Questions
1. `voss eval` registration site — recommend `voss/harness/cli.py` agent group.
2. Task 01 measures LLM agent path, not the deterministic `/analyze` skill — recommend LLM path.
3. `docs/release.md` runbook — recommend defer.

### Ready for Planning
Research complete. Planner can produce task-level PLAN.md across seven tasks (eval module, five fixtures, wheel smoke + README polish, plus the `auth.resolve` micro-extension).
