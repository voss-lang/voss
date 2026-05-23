---
phase: F5-commit-with-critique-hook
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/consensus.py
  - voss/harness/cli.py
  - tests/harness/test_consensus.py
autonomous: true
requirements:
  - D-01
  - D-02
  - D-03
  - D-04
  - D-08
  - D-09
  - D-10
  - D-11
  - D-12
  - D-13
  - D-14
  - D-15
  - D-16

must_haves:
  truths:
    - "voss consensus --staged critiques a staged diff against constraints.yml rules"
    - "voss consensus exits 0 and skips silently when no constraints.yml exists"
    - "voss consensus exits 1 on violations when mode is block, exits 0 when mode is warn"
    - "voss consensus prints structured violations with constraint text, file:line, and explanation"
    - "voss consensus prints a one-liner on clean pass"
    - "voss consensus fails open on any LLM error (exit 0 + warning)"
    - "voss consensus accepts --staged, --diff REF, and --stdin input modes"
  artifacts:
    - path: "voss/harness/consensus.py"
      provides: "Critique logic, Pydantic models, diff capture, prompt assembly"
      exports: ["run_critique", "CritiqueResponse", "Violation", "CritiqueSummary", "ConstraintsConfig", "load_constraints", "capture_diff"]
    - path: "tests/harness/test_consensus.py"
      provides: "Unit tests covering D-01..D-04, D-08..D-16"
      min_lines: 80
    - path: "voss/harness/cli.py"
      provides: "consensus_cmd registered in AGENT_COMMANDS"
      contains: "consensus_cmd"
  key_links:
    - from: "voss/harness/cli.py"
      to: "voss/harness/consensus.py"
      via: "import run_critique"
      pattern: "from voss\\.harness\\.consensus import"
    - from: "voss/harness/consensus.py"
      to: "provider.complete"
      via: "single-shot LLM call with response_format=CritiqueResponse"
      pattern: "provider\\.complete"
    - from: "voss/harness/consensus.py"
      to: "yaml.safe_load"
      via: "constraints.yml parsing"
      pattern: "yaml\\.safe_load"
---

<objective>
Implement `voss consensus` — a standalone CLI command that performs single-shot LLM critique of diffs against natural-language constraints defined in `.voss/constraints.yml`. This is the core module and CLI entry point; the git hook lifecycle (Plan 02) wraps this command.

Purpose: Enables developers to get AI-powered commit critique against project-specific rules, either standalone or as a pre-commit hook target.

Output: `voss/harness/consensus.py` (new module), `consensus_cmd` in `cli.py`, full test suite in `tests/harness/test_consensus.py`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/F5-commit-with-critique-hook/F5-CONTEXT.md
@.planning/phases/F5-commit-with-critique-hook/F5-RESEARCH.md
@.planning/phases/F5-commit-with-critique-hook/F5-PATTERNS.md

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From voss/harness/agent.py (lines 196-211) — Pydantic model pattern with extra="ignore":
  class RunSemantics(BaseModel):
      model_config = {"extra": "ignore"}
      goal: str = ""
      avoided: list[dict] = Field(default_factory=list)
      ...

From voss/harness/agent.py (lines 1404-1453) — Single-shot provider.complete pattern:
  async def _record_run_call(provider, model: str, transcript: str):
      try:
          resp = await provider.complete(
              messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}],
              model=model, response_format=RunSemantics, temperature=0.0, max_tokens=800,
          )
      except Exception:  # noqa: BLE001
          return None
      if resp.parsed is None:
          return None
      return resp.parsed

From voss/harness/providers.py (line 249) — provider.complete signature:
  async def complete(self, *, messages: list[dict], model: str,
                     response_format: Optional[type] = None, tools: Optional[list[dict]] = None,
                     temperature: float = 1.0, max_tokens: Optional[int] = None,
                     timeout: Optional[float] = None) -> ProviderResponse

From voss/harness/cli.py (line 177) — AUTH_CHOICES:
  AUTH_CHOICES = ("auto", "claude", "codex", "api", "none")

From voss/harness/cli.py (lines 401-402) — _resolve_auth_or_die:
  def _resolve_auth_or_die(preference: str) -> tuple[auth_mod.Resolution, ModelProvider]:

From voss/harness/cli.py (lines 206-214) — _resolve_default_model:
  def _resolve_default_model(user_explicit: str | None) -> None:
      # 1. user_explicit (--model flag) wins
      # 2. else ~/.config/voss/config.toml [harness] preferred_model
      # 3. else leave get_config().default_model untouched

From voss_runtime/_config.py (lines 7-8, 36-37):
  class RuntimeConfig:
      default_model: str = "claude-sonnet-4-5"
  def get_config() -> RuntimeConfig: ...

From voss/harness/cli.py (lines 3163-3188) — AGENT_COMMANDS tuple:
  AGENT_COMMANDS = (do_cmd, chat_cmd, edit_cmd, ..., skill_group, ..., logs_group, eval_cmd,)

From voss/harness/cli.py (lines 2596-2598) — Click group pattern:
  @click.group("skill")
  def skill_group() -> None: ...

From voss/harness/recorder.py (lines 430-443) — git subprocess pattern:
  def _git_diff_stat(cwd: Path) -> str:
      out = subprocess.run(["git", "diff", "--stat"], cwd=str(cwd),
                           capture_output=True, text=True, timeout=5)

From voss/harness/code/config.py (line 46) — YAML safe_load pattern:
  raw = yaml.safe_load(defaults_path.read_text(encoding="utf-8")) or {}

From voss/harness/diagnostics.py (lines 115-124) — check_git_on_path:
  def check_git_on_path() -> Check:
      path = shutil.which("git")
      ...

From tests/harness/test_cli.py (lines 1-19) — test patterns:
  from click.testing import CliRunner
  from voss.harness.cli import main
  class TestUnifiedVossCli:
      def test_voss_help_lists_agent_verbs(self) -> None:
          r = CliRunner().invoke(voss_main, ["--help"])
          assert r.exit_code == 0
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create consensus.py module with Pydantic models, constraint loading, diff capture, and single-shot critique</name>
  <files>voss/harness/consensus.py</files>
  <read_first>
    - voss/harness/agent.py (lines 196-211 for RunSemantics Pydantic model pattern; lines 1404-1453 for _record_run_call single-shot provider.complete pattern)
    - voss/harness/providers.py (lines 249-259 for provider.complete signature)
    - voss/harness/recorder.py (lines 430-443 for _git_diff_stat subprocess pattern)
    - voss/harness/code/config.py (line 46 for yaml.safe_load pattern)
    - voss/harness/diagnostics.py (lines 115-124 for check_git_on_path)
  </read_first>
  <action>
    Create voss/harness/consensus.py as a new module. Contains:

    **Pydantic models (per D-10, D-13):**
    - Violation: fields constraint (str), file (str, default ""), line (int | None, default None), explanation (str). All models use model_config = {"extra": "ignore"} per RunSemantics pattern (agent.py:199-203).
    - CritiqueSummary: fields total_checked (int), violation_count (int).
    - CritiqueResponse: fields violations (list[Violation], default_factory=list), summary (CritiqueSummary).
    - ConstraintsConfig: fields mode (str, default "warn" per A2 assumption), rules (list[str], default_factory=list). Validated via model_validate(raw).

    **load_constraints(cwd: Path) function (per D-01, D-03, D-04):**
    - Resolves cwd / ".voss" / "constraints.yml".
    - If file does not exist, returns None (caller skips silently per D-04).
    - Reads with yaml.safe_load(path.read_text(encoding="utf-8")) or {} — exact pattern from code/config.py:46.
    - Validates with ConstraintsConfig.model_validate(raw).
    - On yaml.YAMLError or pydantic.ValidationError: returns None (graceful degradation, same spirit as D-04).

    **capture_diff(mode: str, cwd: Path, ref: str | None = None) function (per D-08):**
    - Three modes: "staged" runs subprocess.run(["git", "diff", "--cached"], cwd=str(cwd), capture_output=True, text=True, timeout=10); "ref" runs ["git", "diff", ref] with the provided ref; "stdin" reads sys.stdin.read().
    - Pre-flight: subprocess.run(["git", "rev-parse", "--git-dir"], cwd=str(cwd), capture_output=True, timeout=5) — if returncode != 0, raise a RuntimeError("not a git repository") (Pitfall 4; caller decides exit code).
    - Truncate output at MAX_DIFF_CHARS = 30_000, append "[diff truncated]" marker when truncated (Pitfall 5).
    - Return the diff text string. Empty string = no staged changes.

    **build_prompt(constraints: ConstraintsConfig, diff_text: str) function (per D-02):**
    - Builds a system prompt string injecting numbered constraint rules and the full diff.
    - System prompt instructs the model to return structured JSON with violations for each rule that is violated. Explicit instruction: only flag violations, do not list passing rules. Include file path and line number when determinable. Use the exact constraint text in the violation's constraint field.

    **async run_critique(provider, model: str, constraints: ConstraintsConfig, diff_text: str) function (per D-13, D-14, D-16):**
    - Calls provider.complete(messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": "Review the staged diff above against the constraints."}], model=model, response_format=CritiqueResponse, temperature=0.0, max_tokens=2000).
    - Wraps in try/except Exception (noqa: BLE001) — on failure returns None (caller handles fail-open per D-16).
    - If resp.parsed is None: returns None (Pitfall 1).
    - Returns CritiqueResponse on success.

    **format_violations(result: CritiqueResponse) function (per D-10, D-11, D-12):**
    - If result.violations is empty: return the one-liner string with checkmark and constraint count per D-12.
    - Otherwise: format each violation as a block: constraint text cited, file:line reference (omit line if None, omit file if empty), explanation. Summary line at bottom: "N violations / M constraints checked" per D-10.
    - Returns (formatted_text: str, has_violations: bool).

    No conventions.py import anywhere in this module (per D-03). No run_turn usage (per Research anti-patterns). No budget cap logic (per D-15).
  </action>
  <acceptance_criteria>
    - File voss/harness/consensus.py exists and is importable: `python -c "from voss.harness.consensus import run_critique, CritiqueResponse, Violation, CritiqueSummary, ConstraintsConfig, load_constraints, capture_diff, format_violations, build_prompt"`
    - grep -c "yaml.safe_load" voss/harness/consensus.py returns >= 1
    - grep -c "yaml.load[^_]" voss/harness/consensus.py returns 0 (never unsafe load)
    - grep -c 'extra.*ignore' voss/harness/consensus.py returns >= 1 (Pydantic extra=ignore on models)
    - grep -c "provider.complete" voss/harness/consensus.py returns >= 1
    - grep -c "response_format=CritiqueResponse" voss/harness/consensus.py returns >= 1
    - grep -c "run_turn" voss/harness/consensus.py returns 0 (never agentic loop)
    - grep -c "conventions" voss/harness/consensus.py returns 0 (D-03 boundary)
    - grep -c "MAX_DIFF_CHARS" voss/harness/consensus.py returns >= 1 (diff truncation guard)
    - grep -c 'mode.*warn' voss/harness/consensus.py returns >= 1 (default mode is warn)
  </acceptance_criteria>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "from voss.harness.consensus import run_critique, CritiqueResponse, Violation, CritiqueSummary, ConstraintsConfig, load_constraints, capture_diff, format_violations, build_prompt; print('OK')"</automated>
  </verify>
  <done>consensus.py exists with all public functions and Pydantic models. Importable with no errors. Uses yaml.safe_load, provider.complete with response_format, extra="ignore" on models. No conventions.py dependency. No run_turn usage.</done>
</task>

<task type="auto">
  <name>Task 2: Create test suite covering all consensus D-01..D-16 requirements</name>
  <files>tests/harness/test_consensus.py</files>
  <read_first>
    - voss/harness/consensus.py (the module just created in Task 1)
    - tests/harness/test_cli.py (lines 1-86 for CliRunner + monkeypatch patterns)
    - tests/harness/test_provider_response.py (lines 45-70 for async provider mock pattern)
  </read_first>
  <action>
    Create tests/harness/test_consensus.py with pytest unit tests. All tests mock the LLM provider — no real LLM calls. Tests use CliRunner for CLI integration, monkeypatch for provider mocking, tmp_path for filesystem.

    **Test fixtures:**
    - A constraints.yml fixture dict: {"mode": "block", "rules": ["No print statements", "All functions need docstrings"]} — written to tmp_path / ".voss" / "constraints.yml" via yaml.dump.
    - A mock provider that returns a SimpleNamespace(parsed=CritiqueResponse(...)) from its complete method. Monkeypatch _resolve_auth_or_die in voss.harness.cli to return (mock_resolution, mock_provider).
    - A mock_git_diff fixture that monkeypatches subprocess.run to return a CompletedProcess with stdout containing a sample diff (add a function without docstring).

    **Required tests (one per requirement cluster):**
    - test_load_constraints_from_yaml (D-01): Create constraints.yml in tmp_path/.voss/, call load_constraints(tmp_path), assert rules list matches, mode matches.
    - test_skip_when_no_constraints_file (D-04): Call load_constraints(tmp_path) with no file present, assert returns None.
    - test_constraints_no_conventions_import (D-03): assert "conventions" not in the source text of consensus.py (or grep the module file).
    - test_single_shot_one_call (D-13): Mock provider, run run_critique, assert provider.complete was called exactly once (mock.call_count == 1).
    - test_response_format_is_critique_response (D-13): Assert provider.complete was called with response_format=CritiqueResponse.
    - test_block_mode_exits_1 (D-09): Via CliRunner invoke consensus with mode=block constraints, mock provider returns violations, assert exit_code == 1.
    - test_warn_mode_exits_0 (D-09): Same but mode=warn, assert exit_code == 0.
    - test_clean_pass_output (D-12): Mock provider returns zero violations, assert output contains the checkmark one-liner pattern and "0 violations".
    - test_violation_output_format (D-10, D-11): Mock provider returns 1 violation, assert output contains constraint text, file reference, explanation. Assert clean constraints are NOT printed.
    - test_fail_open_on_llm_error (D-16): Mock provider.complete to raise Exception, assert exit_code == 0 and stderr contains "LLM request failed" and "Commit proceeds".
    - test_fail_open_on_none_parsed (D-16): Mock provider returns resp.parsed = None, assert exit_code == 0 and stderr contains warning.
    - test_diff_input_staged (D-08): Monkeypatch subprocess.run, invoke with --staged, assert git diff --cached was called.
    - test_diff_input_ref (D-08): Invoke with --diff HEAD~3, assert git diff HEAD~3 was called.
    - test_empty_diff_exits_0 (Pitfall 2): Mock git diff returns empty, assert exit 0 without LLM call.
    - test_large_diff_truncated (Pitfall 5): Mock git diff returns >30000 chars, assert diff passed to provider is truncated and contains "[diff truncated]".
    - test_consensus_in_voss_help: Invoke voss --help via CliRunner, assert "consensus" appears in output.

    Use .venv/bin/python -m pytest tests/harness/test_consensus.py as the run command per F5-VALIDATION.md.
  </action>
  <acceptance_criteria>
    - File tests/harness/test_consensus.py exists with >= 15 test functions
    - .venv/bin/python -m pytest tests/harness/test_consensus.py -q exits 0 with all tests passing
    - grep -c "def test_" tests/harness/test_consensus.py returns >= 15
    - grep -c "CliRunner" tests/harness/test_consensus.py returns >= 1
    - grep -c "monkeypatch" tests/harness/test_consensus.py returns >= 1
    - grep -c "tmp_path" tests/harness/test_consensus.py returns >= 1
    - No test makes a real LLM call (grep -c "provider.complete" in test file should be 0 or only in mock setup)
  </acceptance_criteria>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/test_consensus.py -q</automated>
  </verify>
  <done>15+ tests all GREEN covering D-01..D-04, D-08..D-16, edge cases (empty diff, large diff, None parsed). No real LLM calls. consensus and hooks appear in voss --help.</done>
</task>

<task type="auto">
  <name>Task 3: Register consensus_cmd in cli.py AGENT_COMMANDS</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - voss/harness/cli.py (lines 1285-1350 for do_cmd option patterns; lines 2596-2712 for skill_group/agent_group patterns; lines 3163-3188 for AGENT_COMMANDS tuple)
    - voss/harness/consensus.py (the module created in Task 1 — to know the import path and function signatures)
  </read_first>
  <action>
    Add a consensus_cmd Click command to cli.py. This is the CLI surface for the consensus module.

    **consensus_cmd definition (following do_cmd option patterns):**
    - @click.command("consensus") decorator.
    - Options: --staged (flag_value="staged", is default input mode), --diff (takes a REF string, metavar="REF"), --stdin (flag_value="stdin"), --cwd (default=".", type=click.Path(file_okay=False)), --auth (type=click.Choice(AUTH_CHOICES), default="auto"), --model (default=None).
    - The --staged/--diff/--stdin options should be mutually exclusive. Use Click's standard pattern: a single "input_mode" param with flag_values, plus a separate "ref" param for --diff.
    - Function body: resolve cwd from cwd_str. Call _resolve_default_model(model). Call load_constraints(cwd) — if None, exit 0 silently (D-04). Determine diff mode from options. Call capture_diff(mode, cwd, ref) — if RuntimeError (not a git repo), print error and sys.exit(2). If diff is empty, print one-liner and exit 0 (Pitfall 2). Call _resolve_auth_or_die(auth_pref) to get provider. Call asyncio.run(run_critique(provider, get_config().default_model, constraints, diff_text)). If result is None, print fail-open warning to stderr and sys.exit(0) (D-16). Call format_violations(result) to get output text and has_violations flag. Print output. If has_violations and constraints.mode == "block": sys.exit(1). Else: sys.exit(0).
    - Import from voss.harness.consensus: run_critique, load_constraints, capture_diff, format_violations. Place import at function scope (lazy) to avoid circular imports, consistent with other cli.py patterns.

    **Registration:**
    - Add consensus_cmd to the AGENT_COMMANDS tuple (after eval_cmd).

    Do NOT add hooks_group here — that is Plan 02.
  </action>
  <acceptance_criteria>
    - grep -c "consensus_cmd" voss/harness/cli.py returns >= 2 (definition + AGENT_COMMANDS entry)
    - grep -c '@click.command("consensus")' voss/harness/cli.py returns 1
    - grep -c "from voss.harness.consensus import" voss/harness/cli.py returns >= 1
    - AGENT_COMMANDS tuple contains consensus_cmd (grep confirms)
    - .venv/bin/python -c "from voss.harness.cli import consensus_cmd; print('OK')" exits 0
    - CliRunner().invoke(voss_main, ["--help"]) output contains "consensus"
    - .venv/bin/python -m pytest tests/harness/test_consensus.py -q still all GREEN after cli.py changes
    - .venv/bin/python -m pytest tests/harness/test_cli.py -q still GREEN (no regression)
  </acceptance_criteria>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/test_consensus.py tests/harness/test_cli.py -q</automated>
  </verify>
  <done>consensus_cmd registered in cli.py. "voss consensus" appears in --help. All consensus tests pass. No regression in test_cli.py.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User filesystem -> consensus.py | constraints.yml is user-authored YAML; untrusted input |
| Git subprocess -> consensus.py | Staged diff content is untrusted (may contain adversarial content) |
| LLM response -> consensus.py | Model output parsed as Pydantic JSON; text fields untrusted |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-F5-01 | Tampering | yaml.safe_load in load_constraints | mitigate | Use yaml.safe_load() exclusively (never yaml.load); validate with Pydantic ConstraintsConfig model |
| T-F5-02 | Denial | Large diff overwhelming LLM context | mitigate | Truncate diff at MAX_DIFF_CHARS=30000 with "[diff truncated]" marker before sending to provider |
| T-F5-03 | Spoofing | LLM response containing injected commands | mitigate | Response parsed exclusively as Pydantic CritiqueResponse model; text fields are printed but never executed; extra="ignore" drops unexpected fields |
| T-F5-04 | Information Disclosure | API credentials in diff content | accept | Diff is user's own staged content; provider transport is HTTPS; no additional masking at this layer |
| T-F5-05 | Denial | LLM infrastructure failure blocking commits | mitigate | Fail-open pattern (D-16): any LLM exception or None parsed -> warning on stderr + exit 0 |
| T-F5-SC | Tampering | npm/pip installs | accept | Zero new packages installed in this phase; all deps already in pyproject.toml |
</threat_model>

<verification>
After Plan 01 completes:
1. `voss consensus` appears in `voss --help`
2. `.venv/bin/python -m pytest tests/harness/test_consensus.py -q` — all tests GREEN
3. `.venv/bin/python -m pytest tests/harness/test_cli.py -q` — no regression
4. `grep -c "conventions" voss/harness/consensus.py` returns 0 (D-03 boundary)
5. `grep -c "run_turn" voss/harness/consensus.py` returns 0 (single-shot only)
</verification>

<success_criteria>
- voss/harness/consensus.py exists with run_critique, load_constraints, capture_diff, format_violations, build_prompt, and all Pydantic models
- consensus_cmd registered in AGENT_COMMANDS and appears in voss --help
- 15+ unit tests all GREEN covering D-01..D-04, D-08..D-16
- No regression in existing test_cli.py tests
- No new dependencies added to pyproject.toml
- consensus.py has zero imports from conventions.py (D-03)
- consensus.py uses provider.complete, not run_turn (D-13)
</success_criteria>

<output>
Create `.planning/phases/F5-commit-with-critique-hook/F5-01-SUMMARY.md` when done
</output>
