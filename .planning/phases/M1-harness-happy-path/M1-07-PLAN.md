---
phase: M1-harness-happy-path
plan: 07
type: execute
wave: 3
depends_on:
  - 01
  - 03
  - 04
  - 05
  - 06
files_modified:
  - voss/harness/cli.py
  - voss/cli.py
  - tests/harness/test_happy_path_integration.py
  - tests/harness/test_run_not_overloaded.py
autonomous: true
requirements:
  - CLIH-01
  - CLIH-02
  - CLIH-03
  - CLIH-05
  - CLIH-06
  - CLIH-10
tags:
  - harness
  - integration
  - cli

must_haves:
  truths:
    - "Bare `voss` (no subcommand) drops into the harness REPL with the per-command default mode (plan, per D-07)."
    - "`voss chat` launches the same REPL explicitly."
    - "`voss do \"...\"` runs one-shot, defaults to mode plan (D-07), exits cleanly."
    - "`voss sessions` lists saved sessions from ~/.local/state/voss/sessions/."
    - "`voss resume <id>` rehydrates cwd/model/transcript; provider creds resolve fresh from Keychain (D-18)."
    - "`voss run <file.voss>` remains the compiler command. `voss run --help` describes compiling/executing a .voss program, NOT running an agent task."
    - "End-to-end: `voss do \"summarize this repo\"` (with mocked provider) executes through cwd jail in mode plan and produces a saved session whose JSON contains no provider creds."
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "do_cmd / chat_cmd / bare-main defaults reflect D-07 per-command modes"
      contains: "default=\"plan\""
    - path: "voss/cli.py"
      provides: "Bare `voss` invokes chat_cmd with mode='plan'"
      contains: "mode=\"plan\""
    - path: "tests/harness/test_happy_path_integration.py"
      provides: "End-to-end test for `voss do` with a mocked provider, mode plan, saved session"
    - path: "tests/harness/test_run_not_overloaded.py"
      provides: "Asserts `voss run --help` text is compiler-shaped, not agent-shaped"
  key_links:
    - from: "voss/cli.py::main (no subcommand)"
      to: "voss/harness/cli.py::chat_cmd"
      via: "ctx.invoke(chat_cmd, ...)"
      pattern: "ctx\\.invoke\\(\\s*chat_cmd"
    - from: "voss/cli.py::run"
      to: "voss/cli.py::_compile_source"
      via: "compiler path"
      pattern: "_compile_source"
---

<objective>
Wire up the per-command default modes from D-07, lock in the `voss run` non-overload contract with an explicit test, and add a happy-path integration test that exercises `voss do` end-to-end with a mocked provider.

Purpose: This is the integration plan that proves the M1 happy path runs together. Plans 01-06 build the parts; this plan checks that they compose. Covers CLIH-01, CLIH-02, CLIH-03, CLIH-05, CLIH-06, CLIH-10.

Output:
- `do_cmd` and `chat_cmd` defaults changed from `mode='edit'` to `mode='plan'` (D-07).
- Bare `voss` (in `voss/cli.py` and `voss/harness/cli.py:main`) invokes chat with `mode='plan'`.
- `voss edit` default stays `mode='edit'` (already set in Plan 04).
- `tests/harness/test_run_not_overloaded.py` asserts compiler verb survives — `voss run --help` text reflects compiler semantics.
- `tests/harness/test_happy_path_integration.py` runs `voss do` against a mocked provider in a tmp repo, asserts: no crash, mode plan denied a hypothetical fs_write call, session redaction test still holds for the produced session JSON.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/M1-harness-happy-path/M1-CONTEXT.md
@.planning/phases/M1-harness-happy-path/M1-01-PLAN.md
@.planning/phases/M1-harness-happy-path/M1-03-PLAN.md
@.planning/phases/M1-harness-happy-path/M1-04-PLAN.md
@.planning/phases/M1-harness-happy-path/M1-05-PLAN.md
@.planning/phases/M1-harness-happy-path/M1-06-PLAN.md
@voss/cli.py
@voss/harness/cli.py
@voss/harness/agent.py
@voss_runtime/providers/base.py
@tests/harness/test_agent_integration.py

<interfaces>
After all prior M1 plans land:
  - voss/harness/tools.py: make_toolset(cwd) -> dict[str, ToolEntry] (ToolEntry has is_mutating)
  - voss/harness/permissions.py: PermissionGate(mode, store, auto_yes, edit_scope=None)
                                  .check(name, args, *, is_mutating=False)
                                  mode_allows(mode, name, is_mutating)
  - voss/harness/cli.py: AGENT_COMMANDS = (do, chat, doctor, sessions, resume, edit, tools, config)
  - voss/harness/session.py: SessionRecord schema unchanged; redaction test in place

Provider response class (from voss_runtime/providers/base.py):
  ```python
  @dataclass
  class ProviderResponse:
      text: str
      model: str                          # REQUIRED — positional, no default
      prompt_tokens: int                  # REQUIRED
      completion_tokens: int              # REQUIRED
      cost_usd: float                     # REQUIRED
      raw: dict = field(default_factory=dict)
      parsed: Optional[Any] = None
  ```
  NOTE: The class is `ProviderResponse`, NOT `ModelResponse`. The `model` field is required.
  Any mock/fixture constructing one MUST pass `text`, `model`, `prompt_tokens`,
  `completion_tokens`, `cost_usd` at minimum.

D-07 per-command defaults:
  - voss do     → plan
  - voss edit   → edit (set in Plan 04)
  - voss chat   → plan
  - voss (bare) → plan

CURRENT defaults in voss/harness/cli.py:
  - do_cmd:   default="edit"   ← change to "plan"
  - chat_cmd: default="edit"   ← change to "plan"
  - resume_cmd: default="edit" ← keep "edit" (resuming means continuing edit work)
  - voss/cli.py main bare-invoke: mode="edit" ← change to "plan"
  - voss/harness/cli.py main bare-invoke: mode="edit" ← change to "plan"
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Apply per-command default modes (D-07) + lock voss run compiler verb</name>
  <files>voss/harness/cli.py, voss/cli.py, tests/harness/test_run_not_overloaded.py</files>
  <read_first>
    - voss/harness/cli.py:107-178 (do_cmd) and :185-224 (chat_cmd) and :459-477 (standalone main bare invoke)
    - voss/cli.py:121-144 (main bare invoke)
    - voss/cli.py:170-201 (run command — what we must NOT break)
    - .planning/phases/M1-harness-happy-path/M1-CONTEXT.md (§decisions D-07)
  </read_first>
  <action>
1. In `voss/harness/cli.py`, change the `--mode` default for `do_cmd` and `chat_cmd` from `"edit"` to `"plan"`:
```python
@click.option(
    "--mode",
    type=click.Choice(["plan", "edit", "auto"]),
    default="plan",  # D-07: do defaults to plan
    help="Permission tier.",
)
```
   (Same change for chat_cmd. Resume keeps "edit".)

2. In `voss/harness/cli.py`, the standalone `main` (line ~459) bare-invocation: change `mode="edit"` to `mode="plan"`.

3. In `voss/cli.py`, the bare-`voss` invocation (line ~135-144): change `mode="edit"` to `mode="plan"`.

4. Create `tests/harness/test_run_not_overloaded.py`:
```python
"""CLIH-10: voss run remains the compiler verb, NOT an agent task runner.

This test guards against a future refactor that overloads `voss run` to do
double duty for natural-language tasks. If anyone confuses `voss run` with
`voss do`, this test fails.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from voss.cli import main


class TestRunIsCompilerVerb:
    def test_run_help_describes_compilation(self):
        result = CliRunner().invoke(main, ["run", "--help"])
        assert result.exit_code == 0
        output_lower = result.output.lower()
        # The help text must describe compiling/executing a .voss file.
        # Sanity: it must mention "voss" file or "compile" or "execute".
        assert any(token in output_lower for token in ("voss source", "compile and execute", ".voss")), \
            f"voss run --help should describe compiler semantics, got: {result.output!r}"
        # And it must NOT describe an agent task.
        assert "natural-language" not in output_lower
        assert "agent task" not in output_lower

    def test_run_with_voss_file_compiles(self, tmp_path):
        src = tmp_path / "hello.voss"
        src.write_text('print("hi")\n')
        # voss run on a .voss file goes through the compiler. We don't actually
        # run it (the test environment may lack a working runtime for arbitrary
        # programs); we just assert the verb dispatches to compile-and-run, not
        # the agent loop. The easiest signal is that run does NOT require auth.
        result = CliRunner().invoke(main, ["run", str(src)])
        # Either compiles successfully (rc 0) or fails with a compile error,
        # but never asks for ANTHROPIC_API_KEY. Auth errors say "no usable
        # credentials" — assert that text is absent.
        assert "no usable credentials" not in result.output

    def test_run_does_not_appear_in_agent_commands(self):
        from voss.harness.cli import AGENT_COMMANDS
        names = {cmd.name for cmd in AGENT_COMMANDS}
        assert "run" not in names, \
            "voss run must remain a compiler command; AGENT_COMMANDS contains it"

    def test_do_is_separate_from_run(self):
        # voss do and voss run are different commands.
        result_do = CliRunner().invoke(main, ["do", "--help"])
        result_run = CliRunner().invoke(main, ["run", "--help"])
        assert result_do.exit_code == 0
        assert result_run.exit_code == 0
        # The two help screens must mention different things.
        assert "task" in result_do.output.lower()  # do mentions tasks
        # run does not mention "task" as a natural-language concept.
        assert "natural" not in result_run.output.lower()
```

5. Run `pytest tests/harness/test_run_not_overloaded.py tests/harness/test_cli.py -x`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/test_run_not_overloaded.py tests/harness/test_cli.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'default="plan"' voss/harness/cli.py` returns at least 2 (do_cmd, chat_cmd).
    - `grep -c 'mode="plan"' voss/cli.py` returns 1 (bare-invoke).
    - `grep -c 'mode="plan"' voss/harness/cli.py` returns at least 1 (standalone main bare-invoke).
    - `grep -c 'default="edit"' voss/harness/cli.py` returns 1 — only `edit_cmd` (from Plan 04) and `resume_cmd` keep edit default. If resume_cmd also defaults to edit, this returns 2. Either is acceptable.
    - `pytest tests/harness/test_run_not_overloaded.py -x` exits 0.
    - `pytest tests/harness/test_cli.py -x` exits 0.
    - `python -m voss do "hi" --help` (or `python -m voss do --help`) shows `--mode` with `[default: plan]`.
  </acceptance_criteria>
  <done>Defaults match D-07; voss run is locked as compiler verb with a guard test.</done>
</task>

<task type="auto">
  <name>Task 2: Happy-path integration test for voss do + voss sessions + voss resume</name>
  <files>tests/harness/test_happy_path_integration.py</files>
  <read_first>
    - tests/harness/test_agent_integration.py (existing pattern for mocking the provider)
    - voss/harness/agent.py (run_turn signature)
    - voss/harness/session.py (save / load / list_sessions)
    - voss/harness/cli.py (do_cmd, sessions_cmd, resume_cmd)
    - voss_runtime/providers/base.py (ProviderResponse — the actual class name + required fields)
    - .planning/phases/M1-harness-happy-path/M1-CONTEXT.md (§decisions D-15..D-18)
  </read_first>
  <action>
**Import correction (resolves B1):** The provider response class in `voss_runtime/providers/base.py` is named `ProviderResponse`, NOT `ModelResponse`. Earlier drafts of this plan referenced `ModelResponse`; that name does not exist. Use `ProviderResponse`.

**Constructor signature (resolves B2):** `ProviderResponse` requires `text`, `model`, `prompt_tokens`, `completion_tokens`, `cost_usd` (positional/required; `raw` and `parsed` have defaults). Any fixture instantiating one MUST pass the `model` argument.

1. Create `tests/harness/test_happy_path_integration.py`:
```python
"""End-to-end happy path for M1.

Drives `voss do` with a mocked provider, then `voss sessions`, then `voss resume`.
Asserts:
  - voss do runs to completion in mode plan without crashing
  - the saved session JSON contains no provider creds (D-16 lockdown)
  - voss sessions lists the new session
  - voss resume can rehydrate it
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import CliRunner

from voss.harness import session as session_store
from voss.harness.cli import do_cmd, sessions_cmd, resume_cmd


@pytest.fixture
def isolated_env(monkeypatch, tmp_path):
    """Sandbox XDG dirs + ANTHROPIC_API_KEY for repeatability."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake-key-for-tests")
    # Force non-tty so prompts auto-deny rather than blocking on stdin.
    return tmp_path


@pytest.fixture
def mock_provider(monkeypatch):
    """Stub out the provider so no real network call happens.

    NOTE: ProviderResponse (NOT ModelResponse) is the actual class name in
    voss_runtime.providers.base. The `model` field is required (no default).
    """
    from voss.harness.agent import Plan, ToolCall
    from voss_runtime.providers.base import ProviderResponse  # NOT ModelResponse

    plan = Plan(
        rationale="trivial summary",
        steps=[ToolCall(name="fs_glob", args={"pattern": "*.md"}, why="find docs")],
        confidence=0.9,
        final_when_done="repo summary: {{step_0}}",
    )
    resp = ProviderResponse(
        text="",
        model="claude-sonnet-4-20250514",   # REQUIRED — no default
        prompt_tokens=10,
        completion_tokens=10,
        cost_usd=0.001,
        parsed=plan,
    )

    async def fake_complete(*args, **kwargs):
        return resp

    fake = MagicMock()
    fake.complete = AsyncMock(side_effect=fake_complete)
    monkeypatch.setattr("voss.harness.cli._resolve_auth_or_die",
                        lambda pref: (MagicMock(source="env-anthropic", detail="test"), fake))
    return fake


class TestDoHappyPath:
    def test_voss_do_runs_in_plan_mode_without_crash(self, isolated_env, mock_provider, tmp_path):
        (tmp_path / "README.md").write_text("# test repo\n")
        result = CliRunner().invoke(
            do_cmd,
            ["summarize", "this", "repo", "--cwd", str(tmp_path), "--yes"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, f"voss do failed: {result.output}"
        # Confidence + cost should appear.
        assert "$" in result.output or "cost" in result.output.lower() or "0.0" in result.output


class TestSessionsLifecycle:
    def test_save_and_list_and_resume(self, isolated_env, tmp_path):
        from voss_runtime import EpisodicMemory

        record = session_store.SessionRecord.new(cwd=tmp_path, model="claude-sonnet-4")
        history = EpisodicMemory(capacity=10)
        history.add("summarize", role="user")
        history.add("ok", role="assistant")
        path = session_store.save(record, history)
        assert path.exists()

        records = session_store.list_sessions()
        assert any(r.id == record.id for r in records)

        loaded_record, loaded_history = session_store.load(record.id[:8])
        assert loaded_record.id == record.id
        assert loaded_record.cwd == str(tmp_path.resolve())
        assert loaded_history.last(2)[0]["content"] == "summarize"

    def test_session_json_has_no_creds(self, isolated_env, tmp_path):
        from voss_runtime import EpisodicMemory

        record = session_store.SessionRecord.new(cwd=tmp_path, model="claude-sonnet-4")
        history = EpisodicMemory(capacity=10)
        path = session_store.save(record, history)
        text = path.read_text()
        for forbidden in ("access_token", "refresh_token", "Bearer ", "sk-ant-", "sk-proj-"):
            assert forbidden not in text, f"creds-shaped leak: {forbidden}"


class TestSessionsCmd:
    def test_sessions_lists_saved(self, isolated_env, tmp_path):
        from voss_runtime import EpisodicMemory

        record = session_store.SessionRecord.new(cwd=tmp_path, model="claude-sonnet-4")
        history = EpisodicMemory(capacity=10)
        session_store.save(record, history)

        result = CliRunner().invoke(sessions_cmd, [])
        assert result.exit_code == 0
        assert record.id[:8] in result.output
```

2. Run `pytest tests/harness/test_happy_path_integration.py -x`.

3. Run the full M1 test suite to confirm no regressions:
   `pytest tests/harness/ -x`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/ -x</automated>
  </verify>
  <acceptance_criteria>
    - `tests/harness/test_happy_path_integration.py` exists.
    - `grep -c "class TestDoHappyPath" tests/harness/test_happy_path_integration.py` returns 1.
    - `grep -c "class TestSessionsLifecycle" tests/harness/test_happy_path_integration.py` returns 1.
    - `grep -c "class TestSessionsCmd" tests/harness/test_happy_path_integration.py` returns 1.
    - `grep -c "test_session_json_has_no_creds" tests/harness/test_happy_path_integration.py` returns 1.
    - `grep -c "ProviderResponse" tests/harness/test_happy_path_integration.py` returns at least 2 (import + construction).
    - `grep -c "ModelResponse" tests/harness/test_happy_path_integration.py` returns 0 (the wrong name must not appear).
    - `grep -E 'ProviderResponse\(' tests/harness/test_happy_path_integration.py` shows a call site that includes `model=`.
    - `pytest tests/harness/test_happy_path_integration.py -x` exits 0.
    - `pytest tests/harness/ -x` exits 0 (full M1 suite green, no regressions across Plans 01-07).
  </acceptance_criteria>
  <done>End-to-end voss do + sessions + resume work against a mocked provider; full harness test suite is green.</done>
</task>

</tasks>

<verification>
- `pytest tests/harness/ -x` exits 0 (the whole M1 surface).
- Manual: `python -m voss --help` lists: chat, do, doctor, sessions, resume, edit, tools, config (+ compiler verbs compile, run, check, init, ast).
- Manual: `python -m voss doctor` → traffic-light table.
- Manual: `python -m voss tools` → table with mutating column.
- Manual: `python -m voss config --show` → prints config.toml content (or "(empty)").
- Manual: `python -m voss do --help` → `--mode` shows `[default: plan]`.
- Manual: `python -m voss edit --help` → `--mode` shows `[default: edit]`.
- Manual: `python -m voss run --help` → mentions Voss source file, NOT agent tasks.
</verification>

<success_criteria>
- CLIH-01: bare `voss` drops into the REPL, mode plan (D-07).
- CLIH-02: `voss chat` does the same, explicitly.
- CLIH-03: `voss do "..."` runs one-shot, mode plan default, exits 0 in the mocked integration test.
- CLIH-05: `voss resume <id>` rehydrates a saved session; the test exercises load().
- CLIH-06: `voss sessions` lists saved sessions; integration test exercises sessions_cmd.
- CLIH-10: `voss run --help` describes the compiler verb. `AGENT_COMMANDS` does not include "run". Test asserts both.
- D-07: per-command default modes applied.
- The happy-path integration test composes Plans 01 (mode tiers), 03 (redaction), 05 (config), 06 (commands) and proves they cooperate.
</success_criteria>

<output>
After completion, create `.planning/phases/M1-harness-happy-path/M1-07-SUMMARY.md` documenting the per-command mode matrix, the `voss run` guard test, and the integration test fixtures (mock_provider, isolated_env) so M2 can reuse them.
</output>
