---
phase: M5
plan: 03
type: execute
wave: 2
depends_on:
  - M5-01
  - M5-02
files_modified:
  - voss/eval/runner.py
  - voss/eval/__init__.py
  - voss/harness/cli.py
  - tests/eval/test_cli_options.py
  - tests/eval/test_voss_eval_stub.py
  - tests/eval/test_live_signals.py
autonomous: true
requirements:
  - EVAL-01
  - EVAL-02
  - EVAL-03
  - EVAL-04
must_haves:
  truths:
    - "`voss eval --help` lists --suite, --stub, --live, -k, --out, --judge-model, --task, --auth flags."
    - "`voss eval --stub --task <id> -k 1 --out <tmp>` writes `<tmp>/runs.jsonl` containing one row with the D-04 15-field schema."
    - "Under `--stub`, the JSONL row has `cost_usd: null` — never a token estimate, never 0.0."
    - "Under live providers (creds present), the JSONL row has `cost_usd` from `RunRecord.cost_usd` and `confidence` from `Plan.confidence`."
    - "When no provider creds resolve and `--stub` is not passed, eval exits with the exact loud-failure string `voss eval: no provider creds — pass --stub for hermetic smoke or run /login` (stderr) and exit code 2."
    - "When the agent run raises, the JSONL row records `success: false`, `judge_verdict: \"skipped\"`, judge is never invoked."
  artifacts:
    - path: "voss/eval/runner.py"
      provides: "Orchestrator: suite × k loops, _prepare_fixture, _drive_task, _drive_resume, _extract_signals, _append_row, run_suite"
      exports: ["run_suite", "_prepare_fixture", "_drive_task", "_drive_resume", "_extract_signals", "_append_row"]
      min_lines: 180
    - path: "voss/eval/__init__.py"
      provides: "Re-export run_suite for `from voss.eval import run_suite`"
      contains: "from .runner import run_suite"
    - path: "voss/harness/cli.py"
      provides: "New eval_cmd Click command appended to AGENT_COMMANDS tuple"
      contains: "@click.command(\"eval\")"
    - path: "tests/eval/test_cli_options.py"
      provides: "CliRunner-based help-text assertions for all eval flags"
    - path: "tests/eval/test_voss_eval_stub.py"
      provides: "Subprocess-driven stub smoke + D-04 field allowlist + cost-null pin + per-task parametrize"
    - path: "tests/eval/test_live_signals.py"
      provides: "@pytest.mark.live cost + confidence pull-through smoke (skipped without creds)"
  key_links:
    - from: "voss/eval/runner.py"
      to: "voss/harness/session.py:RunRecord.cost_usd (line 77)"
      via: "_extract_signals sums RunRecord.cost_usd across record.runs"
      pattern: "cost_usd"
    - from: "voss/eval/runner.py"
      to: "voss/harness/agent.py:Plan.confidence (line 46)"
      via: "_extract_signals reads record.runs[0]['plan']['confidence']"
      pattern: "confidence"
    - from: "voss/eval/runner.py"
      to: "voss/harness/permissions.py:PermissionGate (line 98-104)"
      via: "PermissionGate(mode=spec.mode, auto_yes=spec.auto_approve_edits)"
      pattern: "PermissionGate\\(mode="
    - from: "voss/harness/cli.py:AGENT_COMMANDS"
      to: "voss/eval/runner.py:run_suite"
      via: "eval_cmd imports run_suite lazily and dispatches"
      pattern: "from voss.eval import run_suite"
---

<objective>
Wire the eval orchestrator end-to-end: a new `voss eval` Click command, a `voss/eval/runner.py` that loops over the suite × k runs against fresh hermetic tempdirs, extracts cost + confidence from RunRecord/Plan, dispatches the judge from Plan 02, writes a JSONL row per run with the D-04 fixed-field allowlist, and short-circuits to "skipped" rows on agent crash or missing-judge-creds-under-stub. This is the central plumbing wave; everything before it built reusable contracts (suite/judge/auth), everything after consumes the JSONL it writes (summary, fixtures, packaging).

Purpose: EVAL-02/03/04 are all expressed in the JSONL emitted by this command. EVAL-01 fixtures (Plan 05) cannot exercise their rubric without the runner; the wheel smoke (Plan 06) does not depend on this plan but the README polish references `voss eval` as a v0.1 command. The plan also pins the loud-failure no-creds path (CONTEXT D-10) and the auto-approve hook used by task 03 (CONTEXT D-07 + RESEARCH Pattern 3 Option A).

Output: `voss/eval/runner.py` (~200 LOC), `voss/eval/__init__.py` re-export update, `eval_cmd` appended to AGENT_COMMANDS, three test files (CLI surface, stub smoke + D-04 schema, live signals).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md
@.planning/phases/M5-eval-and-distribution-prep/M5-RESEARCH.md
@.planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md
@.planning/phases/M5-eval-and-distribution-prep/M5-01-PLAN.md
@.planning/phases/M5-eval-and-distribution-prep/M5-02-PLAN.md
@voss/harness/cli.py
@voss/harness/agent.py
@voss/harness/session.py
@voss/harness/permissions.py
@voss/harness/auth.py
@voss/harness/tools.py
@voss/harness/render.py

<interfaces>
<!-- RunRecord shape — voss/harness/session.py:60-77 -->
# @dataclass
# class RunRecord:
#     id: str
#     started_at: str
#     ended_at: str
#     goal: str = ""
#     plan: Optional[dict] = None
#     ...
#     cost_usd: float = 0.0

<!-- PermissionGate — voss/harness/permissions.py:94-104 -->
# @dataclass
# class PermissionGate:
#     mode: Mode = "edit"
#     store: PermissionStore | None = None
#     auto_yes: bool = False  # for tests + non-interactive runs
#     def needs_prompt(self, tool_name: str) -> bool:
#         if self.auto_yes:
#             return False

<!-- AGENT_COMMANDS tuple — voss/harness/cli.py:795-810 -->
# AGENT_COMMANDS = (
#     do_cmd, chat_cmd, edit_cmd, doctor_cmd,
#     sessions_cmd, resume_cmd, tools_cmd, config_cmd,
# )
# def register(group: click.Group) -> None:
#     for cmd in AGENT_COMMANDS:
#         group.add_command(cmd)

<!-- AUTH_CHOICES already exists in voss/harness/cli.py (used by do_cmd / chat_cmd) -->

<!-- voss_runtime.providers public surface — VERIFIED voss_runtime/providers/__init__.py:1-32 -->
# from .base import ModelProvider, ProviderResponse
# from .litellm_provider import LiteLLMProvider
# from .stub import StubProvider
# def get(name: str | None = None) -> ModelProvider:  # exported as `get`
#     key = name or get_config().default_model
#     if key in _registry: return _registry[key]
#     return _registry.get("__default__", LiteLLMProvider())
# register("__default__", LiteLLMProvider())
# register("__stub__", StubProvider())
# __all__ = ["LiteLLMProvider", "ModelProvider", "ProviderResponse", "StubProvider", "get", "register"]

<!-- Existing import idioms — VERIFIED -->
# voss/harness/agent.py:23: from voss_runtime.providers import get as get_provider
# voss/harness/cli.py:19:   from voss_runtime.providers import LiteLLMProvider

<!-- run_turn signature — VERIFIED voss/harness/agent.py:128-142 -->
# async def run_turn(
#     task: str,
#     *,
#     tools: dict[str, ToolEntry],
#     cwd: Path,
#     renderer: Renderer,
#     confidence_threshold: float = 0.60,
#     token_budget: int = 60_000,
#     model: str | None = None,
#     provider: ModelProvider | None = None,
#     history: EpisodicMemory | None = None,
#     permissions: PermissionGate | None = None,
#     session_id: str | None = None,
#     cognition=None,
# ) -> TurnResult
# NOTE: `history=` IS a real kwarg; type is EpisodicMemory | None (NOT a raw dict / list).

<!-- Resume primitive — VERIFIED voss/harness/cli.py:692-712 (resume_cmd) -->
# record, history = session_store.load(session_id_or_name, cwd=Path.cwd())
# (session_store.load returns (SessionRecord, EpisodicMemory) — same shape we pass as history=)

<!-- D-04 JSONL row schema — 15 fields, exact -->
# task_id, run_idx, success, cost_usd, confidence, duration_s,
# judge_verdict, judge_confidence, judge_rationale,
# provider, model, judge_model, seed, voss_version, started_at

<!-- D-10 loud-failure exact string -->
# voss eval: no provider creds — pass --stub for hermetic smoke or run /login
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: voss/eval/runner.py orchestrator + __init__ re-export</name>
  <files>voss/eval/runner.py, voss/eval/__init__.py</files>
  <read_first>
    - voss/harness/agent.py:128-142 — run_turn signature (VERIFIED above); `history: EpisodicMemory | None` is the resume kwarg
    - voss/harness/session.py:60-192 — RunRecord dataclass, SessionRecord, save(), load() round-trip
    - voss/harness/permissions.py:94-119 — PermissionGate(mode=..., auto_yes=...), Mode literal
    - voss/harness/tools.py — make_toolset(cwd) factory
    - voss/harness/render.py — PlainRenderer (non-TTY renderer used in non-interactive runs)
    - voss/harness/auth.py:resolve — returns Resolution(source, detail); source=="none" triggers loud failure
    - voss_runtime/providers/__init__.py — `get` factory + StubProvider (VERIFIED public surface above)
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"voss/eval/runner.py" (lines 323-574) — full target shape
    - .planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md §D-04, D-06, D-10, D-11, D-12, D-13, D-14 — JSONL schema, hermetic fixture, loud failure, stub null cost, k=3 sequential, cost source, confidence source
    - .planning/phases/M5-eval-and-distribution-prep/M5-RESEARCH.md §"Pattern 4: Resume" (lines 167-184) — asyncio.Task.cancel pattern + SessionRecord.save/load round-trip
  </read_first>
  <behavior>
    - `from voss.eval import run_suite` works; `run_suite` is the public entrypoint.
    - `run_suite(suite="golden", stub=True, k=1, out_dir=<tmp>, judge_model=None, task_id=<one>, auth_pref="auto")` writes exactly one JSONL row to `<tmp>/runs.jsonl` and returns `<tmp>` as a Path.
    - Under stub mode with no judge creds: row has `cost_usd: None`, `judge_verdict: "skipped"`, `success: None`, judge is NEVER invoked.
    - Under stub mode + crash in agent: row has `success: False`, `judge_verdict: "skipped"`, `judge_rationale: "agent crashed"`, judge is NEVER invoked.
    - Under live mode (creds present): row has `cost_usd: float ≥ 0.0` summed across `record.runs`, `confidence: float ∈ [0,1]` from `record.runs[0]['plan']['confidence']`, judge_verdict ∈ {"pass","fail"} or "skipped" on ParseError.
    - Under live mode with no creds AND no --stub: raises `click.exceptions.Exit(code=2)` after echoing the exact D-10 string to stderr.
    - Task id starting with `"05-resume"` routes through `_drive_resume` (asyncio.Task.cancel pattern); other tasks route through plain `run_turn`.
    - `PermissionGate(mode=spec.mode, auto_yes=spec.auto_approve_edits)` is constructed per-task (Option A from RESEARCH Pattern 3 — no env-var bridge).
    - Output directory defaults to `Path.cwd() / ".voss" / "eval" / <ISO-Z timestamp>` per D-02 + D-03.
    - JSONL row keys are exactly the D-04 15-field allowlist; serialized with `sort_keys=True` for diff stability.
    - Resume rubric is outcome-based (asserts resume succeeded), NOT cancel-timing-based (per T-M5-03-resume-flake mitigation).
  </behavior>
  <action>
    Create `voss/eval/runner.py` per M5-PATTERNS.md lines 355-574. Required structure:

    Module docstring `"""Eval runner: suite × k loops, JSONL writer, signal extraction (M5 D-04, D-13, D-14)."""`.

    Imports (top-of-file):
    - stdlib: `from __future__ import annotations`, `asyncio`, `difflib`, `json`, `os`, `shutil`, `subprocess`, `tempfile`, `time`; `from datetime import datetime, timezone`; `from pathlib import Path`.
    - `click`.
    - `from voss import __version__ as VOSS_VERSION` (read VOSS_VERSION lazily if voss/__init__.py does not export __version__; fall back to `importlib.metadata.version("voss")`).
    - `from voss.harness import auth as auth_mod`.
    - `from voss.harness.agent import run_turn`.
    - `from voss.harness.permissions import PermissionGate`.
    - `from voss.harness.session import SessionRecord, save, load`.
    - `from voss.harness.tools import make_toolset`.
    - `from voss.harness.render import PlainRenderer`.
    - **Provider import (PINNED, verified at voss/harness/agent.py:23 + voss_runtime/providers/__init__.py:1-3,12,24-31):** `from voss_runtime.providers import StubProvider, get as get_provider`. Both names are part of `__all__`; this matches the import idiom already used by `voss/harness/agent.py`. Do NOT introduce a new import path.
    - `from .suite import TaskSpec, load_suite`.
    - `from .judge import judge_run, Verdict`.

    Module constants:
    - `SUITE_ROOT = Path("tests/eval")` — repo-relative; resolved against `Path.cwd()` inside `run_suite` (test invocations set cwd to repo root).
    - `RESUME_CANCEL_DELAY_S = float(os.environ.get("EVAL_RESUME_CANCEL_DELAY_S", "0.05"))` — overridable for slow CI (T-M5-03-resume-flake mitigation; see Async helpers section).

    Helper functions (private, prefixed `_`):
    - `_now_iso() -> str`: returns `datetime.now(timezone.utc).isoformat(timespec="seconds")`.
    - `_prepare_fixture(task_dir: Path, tmp: Path) -> Path`: copies `task_dir/"fixture"` to `tmp/"fixture"` via `shutil.copytree`. Then runs `git init -q -b main` in cwd. Then `git add -A` + `git commit -q -m init` with env containing `GIT_AUTHOR_NAME=eval`, `GIT_AUTHOR_EMAIL=eval@voss`, `GIT_COMMITTER_NAME=eval`, `GIT_COMMITTER_EMAIL=eval@voss` per M5-PATTERNS.md lines 390-399. Subprocess calls use `check=True`. Returns the cwd path.
    - `_file_diff(cwd: Path) -> str`: runs `git diff HEAD` (capture stdout) in cwd; returns stdout text. Used as the judge `file_diff` input.
    - `_extract_signals(record: SessionRecord) -> tuple[float | None, float | None]`: if `not record.runs`, returns (None, None). Otherwise: `total_cost = sum(float(r.get("cost_usd") or 0.0) for r in record.runs) or None` (the `or None` collapses 0.0 to None so OAuth providers that do not populate cost are honestly reported as null — see RESEARCH §Common Pitfalls "Cost = 0.0 for non-LiteLLM providers"). `first_plan = record.runs[0].get("plan") or {}`; `conf = first_plan.get("confidence")`; return `(total_cost, float(conf) if conf is not None else None)`.
    - `_append_row(path: Path, row: dict) -> None`: mkdir parents=True, exist_ok=True; open append; write `json.dumps(row, sort_keys=True) + "\n"`.

    Async helpers:
    - `async def _drive_task(task_id: str, spec: TaskSpec, cwd: Path, *, provider, model: str | None, permissions: PermissionGate) -> tuple[SessionRecord, str, bool]`: creates `SessionRecord.new(cwd=cwd, model=model)`. If `task_id.startswith("05-resume")`, delegates to `_drive_resume(...)`. Otherwise calls `await run_turn(spec.prompt, tools=make_toolset(cwd), cwd=cwd, renderer=PlainRenderer(), provider=provider, permissions=permissions, model=model, session_id=record.id)`. Wraps the run_turn call in `try/except Exception` (NOT BaseException — CancelledError must propagate; cancel is only invoked in _drive_resume and is caught there). On exception, returns `(record, "", True)`. On success returns `(record, result.final, False)`.
    - `async def _drive_resume(record, spec, cwd, provider, model, permissions)`: per M5-PATTERNS.md lines 446-466 + RESEARCH §Pattern 4. Approach (sleep-based cancel with env-var-tunable delay + outcome-based rubric — chosen over introducing an Event hook into `run_turn` because that would change the public signature of a function with 8+ call sites, out of M5 scope):
      1. `task = asyncio.create_task(run_turn(spec.prompt, tools=make_toolset(cwd), cwd=cwd, renderer=PlainRenderer(), provider=provider, permissions=permissions, model=model, session_id=record.id))`.
      2. `await asyncio.sleep(RESUME_CANCEL_DELAY_S)` — uses the module-level constant pulled from `EVAL_RESUME_CANCEL_DELAY_S` env var (default 0.05). Slow CI tunes via env, not by editing source. The cancel timing is NOT the rubric — the rubric (Plan 05 task.toml) asserts outcome ("resume succeeded; final summarizes notes.txt"), so a too-late cancel that lets the first turn finish still allows the resume to demonstrate prior-context surfacing on the second turn.
      3. `task.cancel()`. `try: await task except asyncio.CancelledError: pass`.
      4. Reload via `record2, history2 = load(record.id, cwd=cwd)`. **VERIFIED at voss/harness/cli.py:700:** `session_store.load` returns `(SessionRecord, EpisodicMemory)` and `history2` is passed directly to `run_turn(history=...)`.
      5. Second call: `result = await run_turn(spec.prompt, tools=make_toolset(cwd), cwd=cwd, renderer=PlainRenderer(), provider=provider, permissions=permissions, model=model, history=history2, session_id=record2.id)`. The `history=` kwarg shape is verified (agent.py:138, `EpisodicMemory | None`).
      6. Return `(record2, result.final, False)`.

    Public entrypoint:
    - `def run_suite(*, suite: str = "golden", stub: bool = False, k: int = 3, out_dir: Path | None = None, judge_model: str | None = None, task_id: str | None = None, auth_pref: str = "auto") -> Path`:
      - `project_root = Path.cwd()`; `suite_root = project_root / SUITE_ROOT / "golden"` (the `/ "golden"` literal matches D-05 — only the golden suite ships in M5).
      - **Provider resolution (D-10, D-11):**
        - If `stub`: `provider = StubProvider(); model = "__stub__"`. (Registry key, verified at voss_runtime/providers/__init__.py:22 — `register("__stub__", StubProvider())`.)
        - Else: `res = auth_mod.resolve(preference=auth_pref)`. If `res.source == "none"`: `click.echo("voss eval: no provider creds — pass --stub for hermetic smoke or run /login", err=True)` and `raise click.exceptions.Exit(code=2)`. Otherwise: `model = None` (let `run_turn` resolve via `get_config().default_model`, matching `voss/harness/agent.py:158`); `provider = get_provider(model)` returns either the registered default or LiteLLMProvider per the `get()` factory at voss_runtime/providers/__init__.py:12-18. Do NOT pass the literal string `"__default__"` as a model — that is a registry key, not a model identifier; passing it as `model=` to run_turn would propagate it into provider.complete calls.
      - **Judge provider (D-10 role)**: `judge_res = auth_mod.resolve(preference=auth_pref, role="judge")`. If `stub and judge_res.source == "none"`: `judge_provider = None` (signals "skip judge"). Else `judge_provider = get_provider()`. `judge_model_eff = judge_model or model`.
      - **Output dir (D-02, D-03)**: `ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")`. `out = out_dir or (project_root / ".voss" / "eval" / ts)`. `out.mkdir(parents=True, exist_ok=True)`. `jsonl_path = out / "runs.jsonl"`.
      - **Suite load (D-05)**: `all_tasks = load_suite(suite_root, suite=suite)`. Filter by `task_id` if provided. Raise `click.ClickException(...)` if filter yields no tasks.
      - **Main loop** (D-12 sequential):
        - For each (tid, spec) and each `run_idx in range(k)`:
          - `with tempfile.TemporaryDirectory(prefix=f"voss-eval-{tid}-") as tmp_str:` — auto-cleans on exit.
          - `cwd = _prepare_fixture(suite_root / tid, Path(tmp_str))`.
          - `gate = PermissionGate(mode=spec.mode, auto_yes=spec.auto_approve_edits)`.
          - `started_at = _now_iso()`; `t0 = time.perf_counter()`.
          - `record, final, crashed = asyncio.run(_drive_task(tid, spec, cwd, provider=provider, model=model, permissions=gate))`.
          - `duration_s = time.perf_counter() - t0`.
          - `cost, confidence = _extract_signals(record)`.
          - **Stub cost null (D-11)**: if `stub`: `cost = None` (UNCONDITIONALLY None — never 0.0, never an estimate; satisfies T-M5-fake-cost threat).
          - `diff = _file_diff(cwd)`.
          - **Judge dispatch**:
            - If `crashed`: set `verdict_str = "skipped"`, `judge_conf = 0.0`, `rationale = "agent crashed"`, `success = False`. Judge is NEVER invoked.
            - Elif `stub and judge_provider is None` (no judge creds under stub): set `verdict_str = "skipped"`, `judge_conf = 0.0`, `rationale = "no judge creds under stub"`, `success = None`. Judge is NEVER invoked.
            - Else: `verdict, verdict_str = asyncio.run(judge_run(provider=judge_provider, model=judge_model_eff, task_prompt=spec.prompt, final=final, file_diff=diff, rubric=spec.rubric))`. If verdict is None: `judge_conf = 0.0`, `rationale = "(unparseable)"`, `success = None`. Else `judge_conf = verdict.confidence`, `rationale = verdict.rationale`, `success = (verdict_str == "pass")`.
          - **Row construction (D-04 ALLOWLIST — no spread, never dump untrusted dicts)**: explicit dict literal with the 15 keys: `task_id`, `run_idx`, `success`, `cost_usd`, `confidence`, `duration_s` (round to 3 places), `judge_verdict`, `judge_confidence`, `judge_rationale`, `provider` (use `provider.__class__.__name__`), `model` (the resolved-or-None value passed to run_turn; serialized as JSON null when None), `judge_model` (= judge_model_eff), `seed: None`, `voss_version: VOSS_VERSION`, `started_at`.
          - `_append_row(jsonl_path, row)`.
      - **Summary** (handled by Plan 04's summary.py): `from .summary import write_summary; write_summary(jsonl_path, out / "summary.md")`. If `voss/eval/summary.py` does not yet exist (Plan 04 not landed), wrap in `try/ImportError: pass` so this plan's stub smoke still produces the JSONL even before Wave 3 lands. Remove the guard after Plan 04 merges. (Add a `# Plan 04 dependency: voss/eval/summary.py.write_summary` comment.)
      - Return `out`.

    Update `voss/eval/__init__.py` to: `from .runner import run_suite  # noqa: F401`. Remove the Wave 0 placeholder comment from Plan 01.

    **Tempfile/git env**: when `_prepare_fixture` calls subprocess.run, pass env containing the four GIT_* variables AND inherit os.environ so `git` is found on PATH (`env={**os.environ, **git_env}`).

    **Verification commands the executor should run before committing (pin the three API shapes that were already verified during planning, but re-confirm in case the codebase moved):**
    - `grep -n "from voss_runtime.providers" voss/harness/agent.py voss/harness/cli.py` — expect to see `import get as get_provider` (agent.py:23) and `import LiteLLMProvider` (cli.py:19); confirms `get` and `StubProvider` are still the public symbols.
    - `grep -n "def run_turn\|history:" voss/harness/agent.py | head` — expect `async def run_turn(...)` at line 128 and `history: EpisodicMemory | None = None` at line 138.
    - `grep -n "session_store.load\|history=" voss/harness/cli.py | head` — expect `record, history = session_store.load(...)` in `resume_cmd` and matching `history=history` kwarg pass-through to `_run_repl`.
    If any of these have moved/renamed, adjust the runner imports and resume primitive accordingly (do not paper over with try/except ImportError — fail loudly).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "from voss.eval import run_suite; from voss.eval.runner import _prepare_fixture, _extract_signals, _append_row, _drive_task, _drive_resume; print('OK')"</automated>
  </verify>
  <done>
    `voss/eval/runner.py` exists with all required helpers and `run_suite`. `voss/eval/__init__.py` re-exports `run_suite`. All imports resolve. No syntax errors. (Runtime behavior pinned by Task 2's pytest coverage.)
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: eval_cmd Click command + AGENT_COMMANDS registration + pytest coverage</name>
  <files>voss/harness/cli.py, tests/eval/test_cli_options.py, tests/eval/test_voss_eval_stub.py, tests/eval/test_live_signals.py</files>
  <read_first>
    - voss/harness/cli.py:248-844 — agent command shape (esp. do_cmd / chat_cmd for AUTH_CHOICES + click option idioms)
    - voss/harness/cli.py:795-810 — AGENT_COMMANDS tuple + register() helper
    - tests/cli/test_run.py:22-58 — CliRunner + monkeypatch pattern
    - tests/examples/helpers.py:60-69 — run_voss subprocess helper (analog for stub smoke)
    - tests/harness/test_session_redaction.py — JSON-shape allowlist assertion pattern
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"voss/harness/cli.py:AGENT_COMMANDS" (lines 577-648) — exact eval_cmd shape
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"tests/eval/test_cli_options.py" / "tests/eval/test_voss_eval_stub.py" / "tests/eval/test_live_signals.py" (lines 960-1117) — target shapes
    - .planning/phases/M5-eval-and-distribution-prep/M5-VALIDATION.md rows `cli-eval-command`, `stub-eval-smoke`, `jsonl-cost-stub-null`, `cost-extraction-live`, `confidence-extraction`
    - .planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md §D-01 — Click subcommand options surface (--suite, --stub, --live, -k, --out, --judge-model, --task)
  </read_first>
  <behavior>
    - `voss eval --help` (and `python -m voss.cli eval --help`) lists all 8 flags: `--suite`, `--stub`, `--live`, `-k`, `--out`, `--judge-model`, `--task`, `--auth`.
    - `voss eval --help` shows default value `golden` for `--suite` in the Click help text.
    - `python -m voss.cli eval --stub --task <inline-fixture-id> -k 1 --out <tmp>` (run from a working directory containing `tests/eval/golden/<id>/`) writes exactly one JSONL row to `<tmp>/runs.jsonl`.
    - The row has exactly the 15 D-04 fields (REQUIRED_FIELDS set assertion).
    - The row's `cost_usd` is exactly `None` (JSON null), never `0.0`, never a number.
    - The parametrized stub-smoke test runs all 5 golden task ids successfully under `--stub` (Plan 05 ships the fixtures; this test is keyword-matchable as `task_01` … `task_05` via the parametrize id).
    - The live test module is gated by `pytestmark = pytest.mark.live` and skips cleanly when no creds; when creds present, the row has `cost_usd >= 0.0` (not None) and `confidence` ∈ [0,1].
  </behavior>
  <action>
    Modify `voss/harness/cli.py`:
    1. Add `eval_cmd` Click command defined just before the `AGENT_COMMANDS` tuple (line 795). Verbatim shape per M5-PATTERNS.md lines 605-626:
       - `@click.command("eval")` with options `--suite` (default="golden"), `--stub` (is_flag=True), `--live` (is_flag=True; no-op convenience flag per D-01), `-k "k"` (type=int, default=3), `--out "out_dir"` (type=click.Path(path_type=Path), default=None), `--judge-model "judge_model"` (default=None), `--task "task_id"` (default=None), `--auth "auth_pref"` (type=click.Choice(AUTH_CHOICES), default="auto"). Add `help=` strings to each option that are descriptive enough to satisfy the `cli-eval-command` VALIDATION row's grep — include the flag literal in each help string for grep stability.
       - Docstring: `"""Run the golden eval suite and write JSONL + Markdown report."""`.
       - Body: `from voss.eval import run_suite` (lazy import per M5-PATTERNS.md line 645 — keeps Click startup fast). Call `out = run_suite(suite=suite, stub=stub, k=k, out_dir=out_dir, judge_model=judge_model, task_id=task_id, auth_pref=auth_pref)`. `click.echo(f"eval complete: {out}")`. (The `live` flag is intentionally not passed to run_suite — live is default; the flag is convenience only per D-01.)
    2. Append `eval_cmd` to the AGENT_COMMANDS tuple at line 795-804 (M5-PATTERNS.md lines 629-640). Do NOT reorder the existing 8 entries; append-only.
    3. Confirm `AUTH_CHOICES` is already defined in `voss/harness/cli.py` (used by do_cmd, chat_cmd). Reuse it verbatim. If not present, locate the equivalent constant and use that.

    Create `tests/eval/test_cli_options.py` per M5-PATTERNS.md lines 967-983:
    - `test_eval_help_lists_all_options`: `CliRunner().invoke(eval_cmd, ["--help"])` exit code 0; assert each of the 8 flag literals appears in `result.output`: `--suite`, `--stub`, `--live`, `-k`, `--out`, `--judge-model`, `--task`, `--auth`.
    - `test_eval_default_suite`: same invoke; assert `"golden"` appears in `result.output` (Click renders defaults inline).
    - Import path: `from voss.harness.cli import eval_cmd`.

    Create `tests/eval/test_voss_eval_stub.py` per M5-PATTERNS.md lines 996-1056:
    - Module-level `REQUIRED_FIELDS = {15 D-04 keys exactly: task_id, run_idx, success, cost_usd, confidence, duration_s, judge_verdict, judge_confidence, judge_rationale, provider, model, judge_model, seed, voss_version, started_at}`.
    - `_run_eval(args, cwd)`: subprocess.run([sys.executable, "-m", "voss.cli", "eval", *args], cwd=cwd, capture_output=True, text=True, timeout=120).
    - **Skip dependency on Plan 05 fixtures**: Plan 05 lands the 5 golden task fixtures; until then, build an inline fixture in `tmp_path` and configure run_suite to read from it via the `--out` flag and an explicit `cwd` for subprocess. Add a module-level `@pytest.fixture` named `_golden_repo_root` that:
       - Creates `tmp_path / "tests" / "eval" / "golden" / "02-plan-only" / "fixture"` containing a tiny placeholder `calc.py` (5-line def add).
       - Writes `tmp_path / "tests" / "eval" / "golden" / "02-plan-only" / "task.toml"` with: prompt="x", mode="plan", rubric="PASS if ok".
       - Yields `tmp_path` (used as `cwd=` for the subprocess so SUITE_ROOT resolves to the inline tree).
    - `test_stub_smoke_produces_jsonl(_golden_repo_root, tmp_path)`: subprocess with `["--stub", "--task", "02-plan-only", "-k", "1", "--out", str(tmp_path/"eval-out")]`, cwd=_golden_repo_root. Assert returncode == 0; assert `(tmp_path/"eval-out"/"runs.jsonl").exists()`. Parse jsonl: assert len(rows) == 1; assert set(rows[0].keys()) >= REQUIRED_FIELDS.
    - `test_cost_field_null_under_stub(_golden_repo_root, tmp_path)`: same subprocess invocation; parse row; `assert rows[0]["cost_usd"] is None` (NOT 0.0; this is the D-11 + T-M5-fake-cost pin).
    - **Per-task parametrize (M5-VALIDATION rows task-01..task-05)**: add `@pytest.mark.parametrize("tid", ["01-analyze","02-plan-only","03-approved-edit","04-validation","05-resume"])` test `test_task_runs_under_stub` that depends on a session-scoped fixture which **skips** if Plan 05 fixtures are not yet present (`pytest.skip(...)` if `(Path.cwd() / 'tests/eval/golden' / tid).exists() is False`). When Plan 05 has landed, the test exercises each fixture under `--stub`. This keeps Plan 03 independent of Plan 05 while reserving the keyword-matchable test ids.

    Create `tests/eval/test_live_signals.py` per M5-PATTERNS.md lines 1071-1112:
    - Module top: `pytestmark = pytest.mark.live`.
    - `_has_creds()` helper checks env for ANTHROPIC_API_KEY or OPENAI_API_KEY (per RESEARCH §Environment Availability).
    - `test_cost(tmp_path)`: `@pytest.mark.skipif(not _has_creds(), reason="no provider creds")`. Subprocess `voss eval --task 02-plan-only -k 1 --out <tmp>`, cwd=repo root (resolve via `Path(__file__).resolve().parents[2]`). Timeout 300. Assert returncode==0; parse row; assert `rows[0]["cost_usd"] is not None` and `rows[0]["cost_usd"] >= 0.0`.
    - `test_confidence(tmp_path)`: same skipif gate; same subprocess; assert `rows[0]["confidence"] is not None` and `0.0 <= rows[0]["confidence"] <= 1.0`.
    - These tests require Plan 05's `02-plan-only` fixture; document via module docstring: "Requires Plan 05 fixtures."

    Do NOT modify `voss/cli.py` directly. The existing `register(main)` call at `voss/cli.py:290` (per RESEARCH source list) picks up the new tuple entry automatically.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m voss.cli eval --help && pytest -q -m "not slow and not live" tests/eval/test_cli_options.py tests/eval/test_voss_eval_stub.py::test_stub_smoke_produces_jsonl tests/eval/test_voss_eval_stub.py::test_cost_field_null_under_stub</automated>
  </verify>
  <done>
    `voss eval --help` exits 0 and lists all 8 flags. `eval_cmd` is registered in AGENT_COMMANDS. `test_cli_options.py` passes (2/2). `test_voss_eval_stub.py` passes the two non-parametrize tests (stub smoke + cost-null). Parametrize tests for the 5 golden ids may skip until Plan 05 lands. `test_live_signals.py` exists and skips cleanly without creds (assertable via `pytest -m live --collect-only`).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Agent output → JSONL row | Agent's `final` and judge's `rationale` cross into the JSONL artifact (durable, git-tracked per D-03) |
| Provider response → cost extraction | RunRecord.cost_usd may be 0.0 for OAuth providers; treated honestly as None |
| Fixture cwd → host filesystem | Agent runs with cwd=<tempdir>; the path-jail at run_turn must prevent writes outside that tempdir |
| asyncio.Task.cancel → run_turn internals | RESEARCH Assumption A2 — CancelledError must propagate past per-step `except Exception` |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M5-03-cli-options-drift | T (Tampering) | voss eval CLI surface | mitigate | `test_cli_options.py` asserts all 8 flag literals present in help text; VALIDATION row `cli-eval-command` pins. |
| T-M5-03-fake-cost | I (Info Disclosure) | _extract_signals + stub branch | mitigate | Stub branch unconditionally sets `cost = None` AFTER signal extraction; `test_cost_field_null_under_stub` pins. The `or None` collapse in `_extract_signals` also honors OAuth-provider 0.0 as None (RESEARCH §Common Pitfalls). |
| T-M5-03-fixture-leak | I (Info Disclosure) | tempfile.TemporaryDirectory context | mitigate | `with tempfile.TemporaryDirectory(prefix=...) as tmp_str:` auto-removes the tempdir on context exit; no manual cleanup race. `_prepare_fixture` writes only inside the tempdir. |
| T-M5-03-jsonl-untrusted-spread | I (Info Disclosure) / T (Tampering) | _append_row + row construction | mitigate | Row dict is constructed with explicit 15-key literal (D-04 allowlist); NEVER spread untrusted dicts (e.g., `{**plan_dict}`) into the row. Judge rationale is included but the entire row passes through `json.dumps` so non-string values that should not appear (e.g., raw model API response objects) cannot be serialized. |
| T-M5-03-no-creds-silent | T (Tampering) | run_suite provider resolution | mitigate | When `auth.resolve(...).source == "none"` and `--stub` not passed, exits with `click.exceptions.Exit(code=2)` after echoing the exact D-10 string to stderr. Pattern D in M5-PATTERNS.md. |
| T-M5-03-resume-flake | T (Tampering) | _drive_resume cancel point | mitigate | Cancel uses `asyncio.sleep(RESUME_CANCEL_DELAY_S)` where the delay is read from `EVAL_RESUME_CANCEL_DELAY_S` env var (default 0.05s) — slow CI tunes via env without source edits. Critically, the rubric is **outcome-based** (Plan 05 task.toml asserts "resume succeeded; final summarizes notes.txt"), NOT cancel-timing-based: even if the cancel arrives after the first turn completes, the resume on a fresh `EpisodicMemory` still demonstrates prior-context surfacing. Introducing a deterministic "first tool dispatched" `asyncio.Event` hook into `run_turn` was considered (per checker request) but rejected for M5 scope: it would change `run_turn`'s public signature (called from 8+ sites in cli.py + 2 in tests), expanding the blast radius beyond the eval module. Per RESEARCH Assumption A2, CancelledError propagates past per-step `except Exception` because it is a BaseException in 3.8+. |
| T-M5-03-judge-skipped-on-crash | T (Tampering) | judge dispatch branch | mitigate | When `crashed=True`, judge is NEVER invoked (branch taken before judge_run call). Row records `success=False, judge_verdict="skipped"`. Tested in Plan 02 (`test_judge_skipped.py`) at the judge layer; tested here at the runner layer via the parametrize covering 05-resume which may crash. |
</threat_model>

<verification>
- `python -m voss.cli eval --help` exits 0 and lists all 8 flags.
- `pytest -q -m "not slow and not live" tests/eval/test_cli_options.py tests/eval/test_voss_eval_stub.py::test_stub_smoke_produces_jsonl tests/eval/test_voss_eval_stub.py::test_cost_field_null_under_stub` passes.
- `pytest -m live --collect-only tests/eval/test_live_signals.py` collects 2 tests (executed only if creds present).
- `from voss.eval import run_suite` works.
- `from voss.harness.cli import eval_cmd` works; `eval_cmd` appears in the `AGENT_COMMANDS` tuple.
- No new top-level dependencies.
</verification>

<success_criteria>
1. `voss eval` registered as a Click command via AGENT_COMMANDS.
2. `voss/eval/runner.py` orchestrates suite × k runs with hermetic per-run tempdirs.
3. JSONL row schema is exactly the D-04 15-field allowlist.
4. Stub `cost_usd` is JSON null (never 0.0, never an estimate).
5. Live cost + confidence pull through from RunRecord/Plan correctly.
6. Loud-failure no-creds path produces the exact D-10 string + exit code 2.
7. Crash + missing-judge-creds-under-stub branches set `judge_verdict="skipped"` without invoking judge_run.
8. Task 05-resume routes through `_drive_resume`; asyncio.Task.cancel pattern with env-tunable delay; rubric is outcome-based.
9. Tests pass: `test_cli_options.py`, `test_voss_eval_stub.py::test_stub_smoke_produces_jsonl`, `test_voss_eval_stub.py::test_cost_field_null_under_stub`.
</success_criteria>

<output>
After completion, create `.planning/phases/M5-eval-and-distribution-prep/M5-03-SUMMARY.md` summarizing: exact `eval_cmd` flag set, JSONL row 15-field allowlist, _extract_signals 0.0→None collapse rationale, the Plan 04 `write_summary` ImportError guard (to be removed after Plan 04 merges), the parametrize-skip pattern for Plan 05 fixtures, the asyncio.Task.cancel sleep delay (default 0.05s, overridable via `EVAL_RESUME_CANCEL_DELAY_S`), and the resolved import paths (`get as get_provider` + `StubProvider` from voss_runtime.providers; `model=None` for live so run_turn resolves via config; `history: EpisodicMemory | None` kwarg for resume).
</output>
