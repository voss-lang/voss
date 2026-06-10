---
phase: E1-eval-substrate
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/config.py
  - voss/harness/cli.py
  - tests/eval/conftest.py
  - tests/eval/test_dev_gate.py
autonomous: true
requirements: [EVSUB-05]
must_haves:
  truths:
    - "voss eval without VOSS_DEV=1 exits non-zero with a one-line internal-tool message, makes zero model calls, writes no output dir"
    - "voss eval with VOSS_DEV=1 proceeds with current behavior"
    - "config [eval] section resolves max_turns (default 15) and judge_model (default pinned gpt-5.x variant)"
    - "--max-turns flag is accepted by eval_cmd (forward into run_suite happens in E1-03 when run_suite gains the param)"
    - "existing eval test suite stays green via autouse VOSS_DEV=1 conftest"
  artifacts:
    - path: "voss/harness/config.py"
      provides: "[eval] section reader + get_eval_max_turns + get_eval_judge_model"
      contains: "def get_eval_max_turns"
    - path: "voss/harness/cli.py"
      provides: "VOSS_DEV gate at eval_cmd entry + --max-turns option"
      contains: "VOSS_DEV"
    - path: "tests/eval/conftest.py"
      provides: "autouse fixture setting VOSS_DEV=1 for the eval test suite"
      contains: "VOSS_DEV"
    - path: "tests/eval/test_dev_gate.py"
      provides: "gate tests: no var => exit!=0 + message + no output; var set => proceeds"
  key_links:
    - from: "voss/harness/cli.py eval_cmd"
      to: "os.environ VOSS_DEV"
      via: "guard at callback entry before importing run_suite"
      pattern: "VOSS_DEV"
    - from: "voss/harness/cli.py eval_cmd"
      to: "--max-turns Click option (forward to run_suite added in E1-03)"
      via: "option registration only in this plan"
      pattern: "max_turns"
---

<objective>
Add the internal-only dev gate (`VOSS_DEV=1`) on the `voss eval` verb (EVSUB-05), the `[eval]` config section that supplies `max_turns` (default 15) and `judge_model` defaults (D-06), the `--max-turns` CLI flag (option only — forward to `run_suite` lands in E1-03), and the autouse conftest that keeps the existing eval test suite green. The gate fails at verb entry before any auth/provider/fixture/model work (D-07); `run_suite` stays importable and usable without the env var (programmatic API unchanged).

Purpose: EVSUB-05 makes `voss eval` refuse to run for non-dev users; the config + flag are the cap-defaults plumbing that plan E1-03 consumes when it wires the turn cap and judge-model split into the runner.
Output: dev-gated `eval_cmd`, `[eval]` config getters, `--max-turns` flag, autouse conftest, gate tests.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/E1-eval-substrate/E1-SPEC.md
@.planning/phases/E1-eval-substrate/E1-CONTEXT.md
@.planning/phases/E1-eval-substrate/E1-PATTERNS.md

<interfaces>
<!-- Codex actor model default (so judge default can be pinned smaller). From voss/harness/providers.py + cli.py. -->
Codex backend actor default model = "gpt-5.5" (voss/harness/providers.py:_OPENAI_MODEL_DEFAULT).
The CLI snaps any non-gpt-5.x default_model to "gpt-5.5" for codex auth (cli.py ~line 515).
=> Judge default must be a SMALLER gpt-5.x variant than gpt-5.5 (D-10). Pinned default: "gpt-5.5-mini".

Existing [agent] section reader pattern (voss/harness/config.py to copy exactly):
  _AGENT_BLOCK = re.compile(r"^\[agent\][^\[]*", re.MULTILINE)
  load_agent_config() -> dict[str,str]  (missing file/section -> {})
  get_max_iterations() -> int  (warnings.warn on bad value, fallback to default)

Existing eval_cmd (voss/harness/cli.py ~3491): options suite/stub/live/-k/--out/--judge-model/--task/--auth;
  body: from voss.eval.runner import run_suite; run_suite(...). run_suite does NOT accept max_turns yet — E1-03 adds the param.
  This plan adds the --max-turns OPTION only (value accepted into eval_cmd signature, NOT yet passed to run_suite —
  passing it now would TypeError against the wave-1 run_suite). E1-03 adds the forward in the same edit that
  gives run_suite the max_turns parameter.

Click Exit pattern for non-zero exit (voss/eval/runner.py:247): raise click.exceptions.Exit(code=...)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add [eval] config section + get_eval_max_turns + get_eval_judge_model</name>
  <files>voss/harness/config.py</files>
  <read_first>
    - voss/harness/config.py (the [agent] section: _AGENT_BLOCK regex, _parse_agent_section, load_agent_config, get_max_iterations with warnings.warn — copy this exact shape)
    - .planning/phases/E1-eval-substrate/E1-PATTERNS.md (config.py section, lines 367-461 — exact [eval] reader shape per D-06)
    - voss/harness/providers.py (lines 471-473 — _OPENAI_MODEL_DEFAULT = "gpt-5.5"; confirms judge default must be smaller)
  </read_first>
  <behavior>
    - Missing config file or missing [eval] section => get_eval_max_turns() == 15.
    - [eval] max_turns = 8 => get_eval_max_turns() == 8.
    - [eval] max_turns = "abc" => warns RuntimeWarning, returns 15.
    - Missing [eval] judge_model => get_eval_judge_model() == "gpt-5.5-mini".
    - [eval] judge_model = "gpt-5.5-nano" => get_eval_judge_model() == "gpt-5.5-nano".
  </behavior>
  <action>
    In voss/harness/config.py add an `[eval]` section following the `[agent]` pattern exactly: `_EVAL_BLOCK = re.compile(r"^\[eval\][^\[]*", re.MULTILINE)`, `_parse_eval_section(text)` (uses existing `_KV.findall`), `load_eval_config() -> dict[str,str]` (missing file/section -> `{}`, mirror load_agent_config including the OSError guard). Add module constants `DEFAULT_MAX_TURNS = 15` (D-04) and `DEFAULT_JUDGE_MODEL = "gpt-5.5-mini"` (D-10 — smaller gpt-5.x variant than the codex actor default gpt-5.5). Add `get_eval_max_turns() -> int` mirroring `get_max_iterations` (int parse, `warnings.warn(..., RuntimeWarning, stacklevel=2)` on bad value, fallback to `DEFAULT_MAX_TURNS`). Add `get_eval_judge_model() -> str` returning `load_eval_config().get("judge_model", DEFAULT_JUDGE_MODEL)`. Do not alter the existing `[agent]` parser.
  </action>
  <verify>
    <automated>.venv/bin/python -c "from voss.harness.config import get_eval_max_turns, get_eval_judge_model; assert get_eval_max_turns()==15; assert get_eval_judge_model()=='gpt-5.5-mini'; print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `from voss.harness.config import get_eval_max_turns, get_eval_judge_model, load_eval_config, DEFAULT_MAX_TURNS, DEFAULT_JUDGE_MODEL` succeeds.
    - With no config file present, `get_eval_max_turns() == 15` and `get_eval_judge_model() == "gpt-5.5-mini"`.
    - A config file with `[eval]\nmax_turns = 8` yields `get_eval_max_turns() == 8`.
    - A config file with `[eval]\nmax_turns = abc` emits a `RuntimeWarning` and returns `15`.
    - `grep -c "def get_eval_max_turns" voss/harness/config.py` returns `1`; `grep -c "def get_eval_judge_model" voss/harness/config.py` returns `1`.
    - Existing config tests still pass: `.venv/bin/python -m pytest tests/harness -k config -q`.
  </acceptance_criteria>
  <done>[eval] section reader returns max_turns (default 15) and judge_model (default gpt-5.5-mini); bad values warn and fall back; [agent] parser untouched.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Dev gate on eval_cmd + --max-turns flag + autouse conftest + gate tests</name>
  <files>voss/harness/cli.py, tests/eval/conftest.py, tests/eval/test_dev_gate.py</files>
  <read_first>
    - voss/harness/cli.py (eval_cmd at ~line 3491 — options + body that calls run_suite; AUTH_CHOICES; existing import of os at top of file)
    - voss/cli.py (lines 236-238 — os.environ.get env-check pattern to copy)
    - voss/eval/runner.py (lines 246-248 — click.exceptions.Exit(code=...) loud-exit pattern)
    - tests/harness/conftest.py (lines 28-31 — autouse env-fixture pattern with monkeypatch.setenv)
    - tests/eval/test_voss_eval_stub.py (subprocess tests use os.environ.copy(); confirm autouse conftest propagates VOSS_DEV into copied env so these stay green)
    - .planning/phases/E1-eval-substrate/E1-PATTERNS.md (cli.py + conftest sections, lines 313-490 — exact gate + conftest shapes per D-07/D-08/D-09)
  </read_first>
  <behavior>
    - `voss eval --stub --task 02-plan-only ...` with VOSS_DEV unset => exit != 0, stderr one-line internal-tool message, no `runs.jsonl` written, no model/provider/fixture work.
    - Same invocation with VOSS_DEV=1 => proceeds (current stub behavior, exit 0).
    - run_suite imported and called directly (no CLI) works regardless of VOSS_DEV (programmatic API ungated).
    - All existing tests/eval/ subprocess tests stay green because conftest autouse sets VOSS_DEV=1 into os.environ (carried into os.environ.copy()).
  </behavior>
  <action>
    In voss/harness/cli.py `eval_cmd`: as the FIRST statement in the callback (D-07, before `from voss.eval.runner import run_suite`), add a guard `if os.environ.get("VOSS_DEV") != "1": click.echo("voss eval: internal tool — set VOSS_DEV=1 to run", err=True); raise click.exceptions.Exit(code=1)`. Add a new option `@click.option("--max-turns", "max_turns", default=None, type=int, help="Turn cap per task (overrides config default).")` and add `max_turns: int | None` to the eval_cmd signature. Do NOT pass max_turns into the `run_suite(...)` call in this plan — run_suite does not accept the parameter until E1-03, and forwarding now would TypeError every CLI eval invocation in wave 1. E1-03 adds `max_turns=max_turns` to the call site in the same edit that gives run_suite the parameter. Use `VOSS_DEV` (generic, D-08), not an eval-specific var.

    Create tests/eval/conftest.py with an autouse fixture `_set_voss_dev(monkeypatch)` that calls `monkeypatch.setenv("VOSS_DEV", "1")` so the whole eval suite (including subprocess tests that copy os.environ) runs gated-open.

    Create tests/eval/test_dev_gate.py with two subprocess tests mirroring tests/eval/test_voss_eval_stub.py's `_run_eval` harness: (a) build env via os.environ.copy(), pop VOSS_DEV, run `eval --stub --auth none --task 02-plan-only --out <dir>` => assert returncode != 0, assert the internal-tool message in stderr, assert the out dir / runs.jsonl was NOT created; (b) set env VOSS_DEV=1, same invocation => assert returncode == 0 and runs.jsonl exists. Reuse the golden_repo_root tmp-fixture approach from test_voss_eval_stub.py (a single 02-plan-only fixture) so the test is hermetic.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_dev_gate.py tests/eval/test_voss_eval_stub.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "VOSS_DEV" voss/harness/cli.py` returns ≥1 and the guard appears inside `eval_cmd` before the `run_suite` import.
    - `--max-turns` appears in `voss eval --help`: `.venv/bin/python -m voss.cli eval --help` (with VOSS_DEV=1) lists `--max-turns`.
    - tests/eval/conftest.py exists with an `autouse=True` fixture setting `VOSS_DEV`.
    - test_dev_gate.py case (a): exit code != 0, stderr contains `internal tool`, no runs.jsonl created.
    - test_dev_gate.py case (b): exit code 0, runs.jsonl exists.
    - `.venv/bin/python -m pytest tests/eval/ -q` → existing eval suite green (autouse conftest keeps subprocess tests passing).
  </acceptance_criteria>
  <done>voss eval is dev-gated at verb entry; --max-turns option registered (forward lands in E1-03); programmatic run_suite stays ungated; autouse conftest keeps the eval suite green; two gate tests prove both directions.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| operator shell → voss eval | the verb is now internal-only; uncontrolled invocation could burn weekly subscription limits |
| env VOSS_DEV → gate | a single env var is the entire access control for an internal tool (low-value, internal-only posture) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E1-04 | Elevation | accidental `voss eval` invocation by non-dev | mitigate | VOSS_DEV=1 gate at verb entry exits before any auth/provider/model work; zero sub-credit spend without the explicit opt-in |
| T-E1-05 | Repudiation | gate bypass via programmatic import | accept | `run_suite` is intentionally importable for tests/dev; internal-only tool, no untrusted callers; gate is a footgun guard not a security boundary |
| T-E1-06 | Spoofing | env var trivially settable | accept | Internal-only dev tool on the operator's own machine; VOSS_DEV is a friction gate, not auth. Documented as such. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/eval/ -q` → full eval suite green (conftest autouse VOSS_DEV=1)
- `.venv/bin/python -m pytest tests/harness -k config -q` → config tests green
- `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --help` lists `--max-turns`
- Dev-gate negative path: eval without VOSS_DEV exits non-zero, writes nothing
</verification>

<success_criteria>
- `voss eval` without `VOSS_DEV=1` exits non-zero with a one-line message, zero model calls, no output dir (EVSUB-05)
- With `VOSS_DEV=1`, behavior unchanged; programmatic `run_suite` import works without the var
- `[eval]` config supplies `max_turns` (15) and `judge_model` (gpt-5.5-mini) defaults
- `--max-turns` flag accepted (forward to run_suite is E1-03's edit); existing eval suite green
</success_criteria>

<output>
Create `.planning/phases/E1-eval-substrate/E1-02-SUMMARY.md` when done
</output>
