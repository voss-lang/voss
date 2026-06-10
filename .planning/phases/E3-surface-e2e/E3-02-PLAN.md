---
phase: E3-surface-e2e
plan: 02
type: execute
wave: 2
depends_on: [E3-01]
files_modified:
  - voss/eval/runner.py
  - tests/eval/test_surface_drivers.py
autonomous: true
requirements: [EVSRF-02]
must_haves:
  truths:
    - "_drive_cli_do spawns `python -m voss.cli do <prompt> --plain` as a real subprocess and returns stdout as final"
    - "_drive_cli_chat drives a single non-interactive turn via piped stdin (input() -> EOFError -> clean exit) and returns stdout"
    - "_drive_cli_edit spawns `python -m voss.cli edit <target_file> --plain` requiring spec.target_file; clear crash_reason when target_file is missing"
    - "All three CLI drivers inherit live auth env (no auth keys stripped) and inject NO sitecustomize.py (live, not stub)"
    - "A non-zero subprocess returncode becomes a crash_reason (recorded as a row), never an unhandled exception"
    - "_drive_task routes cli:do/cli:chat/cli:edit to these drivers; internal path stays unchanged"
  artifacts:
    - path: "voss/eval/runner.py"
      provides: "_live_env + _drive_cli_do/_drive_cli_chat/_drive_cli_edit + wired dispatch"
      contains: "_drive_cli_do"
    - path: "tests/eval/test_surface_drivers.py"
      provides: "stub-mode CLI driver tests (sitecustomize injected in TESTS ONLY via CliRunner)"
      contains: "def test_cli_do"
  key_links:
    - from: "voss/eval/runner.py _drive_task cli:* branches"
      to: "_drive_cli_do/_drive_cli_chat/_drive_cli_edit"
      via: "await driver, map (final, crash_reason, capped) into the return tuple"
      pattern: "_drive_cli_(do|chat|edit)"
    - from: "voss/eval/runner.py _live_env"
      to: "os.environ (inherited, auth NOT stripped)"
      via: "dict(os.environ) + litellm/offline guards; no sitecustomize"
      pattern: "_live_env"
---

<objective>
Implement the three CLI subprocess drivers — `cli:do`, `cli:chat`, `cli:edit` — that drive `voss do/chat/edit` as real subprocesses with live auth env and NO stub injection (D-05, D-06, EVSRF-02). Wire them into the `_drive_task` dispatch seam from E3-01. Cover them with stub-mode tests that use the `tests/e2e/runner.py` `CliRunner` (which DOES inject sitecustomize — permitted in tests only, forbidden in the live drivers).

Purpose: First proof that `voss do/chat/edit` work end-to-end as the user runs them, scored through the E1 hybrid substrate.
Output: `_live_env` helper, three driver coroutines, wired dispatch, stub-mode driver tests.

HARD PRECONDITION: E1-03/E1-04 merged (consumes the E1 row/scoring path); E3-01 merged (TaskSpec.surface/target_file + dispatch skeleton). Wave ordering guarantees both.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/E3-surface-e2e/E3-CONTEXT.md
@.planning/phases/E3-surface-e2e/E3-RESEARCH.md
@.planning/phases/E3-surface-e2e/E3-PATTERNS.md
@.planning/phases/E3-surface-e2e/E3-01-SUMMARY.md

<interfaces>
CLI verbs (voss/harness/cli.py) — confirmed flags:
- do_cmd:   positional prompt; --cwd dir; --plain  (reads piped stdin when not a TTY, appends a separator line)
- chat_cmd: --cwd dir; --plain  -> _run_repl(); input() reads first piped line, next call EOFError -> clean exit
- edit_cmd: positional path (click.Path(exists=True) — MUST exist at call time); --cwd dir; --plain -> _run_repl() same EOF exit
- serve_cmd: NO --cwd (cwd comes via session create body) — relevant to E3-03, not here
- Module entry: `python -m voss.cli VERB` (voss/cli.py exposes main; pyproject voss = "voss.cli:main")

_drive_task return tuple contract (from E3-01): (record, final, crash_reason_or_None, capped).
The cli:* dispatch branches (a not-implemented crash_reason stub from E3-01) get replaced here.

tests/e2e/runner.py CliRunner (lines 157-208):
- .env() STRIPS ANTHROPIC_API_KEY / OPENAI_API_KEY and injects sitecustomize.py + StubProvider — the STUB path.
- .run("do", "PROMPT", "--plain") -> Result(returncode, stdout, stderr, ...).
- E3 LIVE drivers must NOT use CliRunner.env() — they use _live_env (auth inherited, no sitecustomize).

_live_env target shape (RESEARCH Pattern 2 lines 243-251):
dict(os.environ) + LITELLM_LOCAL_MODEL_COST_MAP=true, VOSS_DEV=1, PYDANTIC_DISABLE_PLUGINS=1,
HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1 ; DO NOT strip auth keys.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: _live_env helper + three CLI subprocess drivers</name>
  <files>voss/eval/runner.py</files>
  <read_first>
    - voss/eval/runner.py (FULL — imports lines 1-35 confirm asyncio/json/os/subprocess/httpx already present; _drive_task dispatch from E3-01; _file_diff lines 73-81 — caller computes diff, drivers do not)
    - tests/e2e/runner.py (FULL — CliRunner.run() lines 181-208 for subprocess invocation ergonomics; CliRunner.env() lines 157-178 to see exactly what the STUB path strips/injects so the LIVE drivers deliberately do NOT replicate the stripping)
    - voss/harness/cli.py (do_cmd lines 1659-1700 piped-stdin separator behavior; chat_cmd lines 1826-1860 + _run_repl EOF exit; edit_cmd lines 1896-1941 positional path click.Path(exists=True))
    - .planning/phases/E3-surface-e2e/E3-PATTERNS.md (runner.py drivers section lines 76-146 — exact _live_env + driver bodies)
    - .planning/phases/E3-surface-e2e/E3-RESEARCH.md (Pattern 2 lines 217-278; Pitfall 3 stdin separator lines 584-588; Pitfall 2 --plain forces PlainRenderer lines 578-582)
  </read_first>
  <action>
    In voss/eval/runner.py add `import sys` if not present (asyncio/json/os/subprocess/httpx already imported). Add:

    `_live_env(cwd: Path) -> dict[str, str]`: env = dict(os.environ); set env["LITELLM_LOCAL_MODEL_COST_MAP"]="true", env["VOSS_DEV"]="1", env["PYDANTIC_DISABLE_PLUGINS"]="1", env["HF_HUB_OFFLINE"]="1", env["TRANSFORMERS_OFFLINE"]="1". DO NOT delete ANTHROPIC_API_KEY / OPENAI_API_KEY / codex auth keys — live auth pass-through is the point of E3 (contrast with CliRunner.env() which strips them for the stub path). Do NOT add sitecustomize to PYTHONPATH (D-05 — no stub injection in live drivers).

    `_drive_cli_do(spec, cwd, *, timeout=120.0) -> tuple[str, str | None, bool]`: subprocess.run([sys.executable, "-m", "voss.cli", "do", spec.prompt, "--cwd", str(cwd), "--plain"], cwd=str(cwd), env=_live_env(cwd), input="", capture_output=True, text=True, timeout=timeout). Use input="" (NOT stdin=DEVNULL) — matches CliRunner.run() default so the piped-stdin branch appends nothing meaningful (Pitfall 3). If result.returncode != 0: return ("", f"returncode={result.returncode}: {result.stderr[:200]}", False). Else return (result.stdout.strip(), None, False).

    `_drive_cli_chat(spec, cwd, *, timeout=120.0) -> tuple[str, str | None, bool]`: same skeleton with command ["...","chat","--cwd",str(cwd),"--plain"] and input=spec.prompt + "\n" (single line → input() reads it → next call EOFError → clean exit). Same returncode handling.

    `_drive_cli_edit(spec, cwd, *, timeout=120.0) -> tuple[str, str | None, bool]`: if not spec.target_file: return ("", "cli:edit requires target_file in task.toml", False). target = cwd / spec.target_file. Command ["...","edit",str(target),"--cwd",str(cwd),"--plain"], input=spec.prompt + "\n". Same returncode handling. (edit_cmd's positional path uses click.Path(exists=True); the fixture provides target_file — see E3-04.)

    Each driver is `async def` so the dispatch awaits it uniformly (the body is a synchronous subprocess.run; awaiting a coroutine that does sync work is fine inside run_suite's asyncio.run). Wrap each subprocess.run in try/except subprocess.TimeoutExpired → return ("", "timeout", False) so a hung CLI becomes a row, not a raised exception.
  </action>
  <verify>
    <automated>.venv/bin/python -c "from voss.eval.runner import _live_env, _drive_cli_do, _drive_cli_chat, _drive_cli_edit; from pathlib import Path; e=_live_env(Path('.')); assert e['VOSS_DEV']=='1' and e['LITELLM_LOCAL_MODEL_COST_MAP']=='true' and 'sitecustomize' not in e.get('PYTHONPATH',''); print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "_drive_cli_do" voss/eval/runner.py` >= 1, same for `_drive_cli_chat` and `_drive_cli_edit`.
    - `_live_env` returns a dict whose VOSS_DEV=="1" and LITELLM_LOCAL_MODEL_COST_MAP=="true" and that does NOT strip ANTHROPIC_API_KEY (if present in os.environ, it survives into the returned dict).
    - `grep -c "sitecustomize" voss/eval/runner.py` == 0 in the driver/_live_env code (no stub injection in live drivers — D-05).
    - The drivers invoke `python -m voss.cli` with `--plain` and `--cwd`: `grep -c -- "--plain" voss/eval/runner.py` >= 3 (one per CLI driver) and `grep -c "voss.cli" voss/eval/runner.py` >= 3.
    - `_drive_cli_edit` returns a non-None crash_reason string mentioning target_file when spec.target_file is None (assert in Task 2 stub test).
    - `.venv/bin/python -c "import voss.eval.runner"` imports cleanly; the import-level verify command prints `ok`.
  </acceptance_criteria>
  <done>Three live CLI subprocess drivers exist; _live_env inherits auth and injects no sitecustomize; returncode/timeout become crash_reason rows not exceptions.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire cli:* dispatch + stub-mode CLI driver tests</name>
  <files>voss/eval/runner.py, tests/eval/test_surface_drivers.py</files>
  <read_first>
    - voss/eval/runner.py (the _drive_task cli:* dispatch branches from E3-01 — replace the not-implemented stubs with await _drive_cli_*; keep the (record, final, crash_reason, capped) tuple shape)
    - tests/e2e/runner.py (CliRunner full — its stub env + sitecustomize injection is what the TESTS use; lines 83-208)
    - tests/eval/conftest.py (autouse VOSS_DEV=1 — inherited by tests/eval/ test files; no re-add needed)
    - tests/eval/test_checks.py (lines 1-8 import + direct-function-call test style analog)
    - .planning/phases/E3-surface-e2e/E3-PATTERNS.md (test_surface_drivers.py section lines 316-389 — stub CLI test pattern + CliRunner usage)
    - .planning/phases/E3-surface-e2e/E3-RESEARCH.md (Validation Architecture lines 766-799 — EVSRF-02/03/04 commands; Wave 0 gaps lines 795-799)
  </read_first>
  <action>
    In voss/eval/runner.py _drive_task: replace the cli:do / cli:chat / cli:edit not-implemented stub branches (from E3-01) with real calls. For each: `final, crash_reason, capped = await _drive_cli_<x>(spec, cwd)`; then `return record, final, crash_reason, capped`. Keep the `serve` branch as the not-implemented stub (E3-03 fills it). The internal branch stays unchanged.

    Create tests/eval/test_surface_drivers.py covering the CLI drivers under STUB mode (D-10 — stub injection allowed in tests; the live drivers themselves never inject it). Import `from tests.e2e.runner import CliRunner` and use it to seed a stubbed CLI invocation environment, OR (preferred — tests the actual driver code path) monkeypatch the driver subprocess to point at a stubbed CLI: set the CliRunner stub env (which injects sitecustomize + StubProvider + strips auth) and call the driver with that env via monkeypatching `_live_env` to return the CliRunner stub env for the test. Concretely:

    - test_cli_do_stub: build a tmp fixture project dir with one seed file; monkeypatch voss.eval.runner._live_env to return a CliRunner-style stub env (sitecustomize + StubProvider, VOSS_DEV=1); run `asyncio.run(_drive_cli_do(TaskSpec(prompt="Say hello.", mode="plan", rubric="...", surface="cli:do"), cwd))`; assert crash_reason is None and the returned final (stdout) is non-empty (StubProvider emits a canned turn).
    - test_cli_chat_stub: same pattern with surface="cli:chat"; assert crash_reason is None and stdout non-empty (single piped turn then clean EOF exit — process returncode 0).
    - test_cli_edit_requires_target_file: TaskSpec(..., surface="cli:edit", target_file=None); assert _drive_cli_edit returns a crash_reason containing "target_file" (no subprocess spawned).
    - test_cli_edit_stub: fixture with a seed target file (e.g. calc.py); TaskSpec(..., surface="cli:edit", target_file="calc.py"); assert crash_reason is None.

    Reuse the Wave-0 hazard guard (MEMORY "GSD scaffold fictional API"): before asserting, confirm the imported driver names exist (`from voss.eval.runner import _drive_cli_do, _drive_cli_chat, _drive_cli_edit`) — a NameError fails loudly rather than an xfail hiding a fictional API.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_surface_drivers.py -x -q -k "cli"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "_drive_cli_do(spec" voss/eval/runner.py` >= 1 (dispatch wired, not the not-implemented stub).
    - The `serve` branch still returns a not-implemented crash_reason (E3-03 fills it): `grep -c "serve" voss/eval/runner.py` >= 1.
    - test_surface_drivers.py imports `_drive_cli_do, _drive_cli_chat, _drive_cli_edit` from voss.eval.runner without NameError.
    - test_cli_do_stub and test_cli_chat_stub pass with crash_reason None and non-empty stdout against StubProvider (no live auth, no network).
    - test_cli_edit_requires_target_file asserts the crash_reason string contains "target_file" when target_file is None.
    - The tests do NOT require real credentials: `.venv/bin/python -m pytest tests/eval/test_surface_drivers.py -q -k "cli"` is green offline.
    - Full eval suite stays green: `.venv/bin/python -m pytest tests/eval -q -m 'not live'`.
  </acceptance_criteria>
  <done>cli:do/cli:chat/cli:edit dispatch is wired to the real drivers; stub-mode tests prove the subprocess + EOF-exit + target_file paths offline; serve remains stubbed for E3-03.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| eval runner → CLI subprocess (live auth env) | os.environ (incl. live auth keys) crosses into a spawned process; must not leak creds into artifacts |
| subprocess stdout/stderr → JSONL final/crash_reason | captured output flows into recorded rows; truncate stderr, never embed full env |
| test stub path vs live driver path | sitecustomize injection must stay test-only; live drivers must never inject it |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E3-04 | Information | live auth creds leaking into JSONL/summary or test fixtures | mitigate | drivers record only stdout (final) + truncated stderr[:200] (crash_reason); _live_env is never serialized into any row; no env dump in artifacts |
| T-E3-05 | Tampering | stub sitecustomize injected into a live driver | mitigate | _live_env never sets PYTHONPATH to a sitecustomize dir; grep gate (sitecustomize count == 0 in driver code); CliRunner stub env used ONLY inside tests |
| T-E3-06 | Denial | hung CLI subprocess burning the run | mitigate | per-driver timeout=120s + try/except TimeoutExpired → crash_reason row (no hang, no raise) |
| T-E3-SC | Tampering | npm/pip/cargo installs | accept | zero new packages (RESEARCH Package Legitimacy Audit: not applicable); no install tasks |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/eval/test_surface_drivers.py -q -k "cli"` → CLI driver stub tests green offline
- `.venv/bin/python -m pytest tests/eval -q -m 'not live'` → full eval suite green
- _live_env inherits auth, injects no sitecustomize; drivers use --plain + --cwd
- returncode/timeout → crash_reason row, never an exception
</verification>

<success_criteria>
- cli:do/cli:chat/cli:edit drivers spawn real `python -m voss.cli` subprocesses with live auth env, no stub injection (EVSRF-02, D-05, D-06)
- cli:edit requires target_file with a clear crash_reason otherwise
- dispatch wired in _drive_task; internal unchanged; serve still stubbed for E3-03
- stub-mode tests prove the driver paths offline; no credential leakage into artifacts
</success_criteria>

<output>
Create `.planning/phases/E3-surface-e2e/E3-02-SUMMARY.md` when done
</output>
