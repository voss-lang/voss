---
phase: M11-voss-aware-tools-caps-01b
plan: 02
type: execute
wave: 2
depends_on: [M11-01]
files_modified:
  - voss/harness/tools.py
  - voss/harness/cli.py
  - tests/harness/test_tools.py
  - tests/harness/test_repl_slash.py
  - tests/harness/test_voss_inspect.py
autonomous: true
requirements: [VTOOL-02, VTOOL-03, VTOOL-05]
---

<objective>
Expose the M11-01 core through user and agent surfaces for probable decisions
and budget traces:

- read-only tools: `voss_probable_inspect`, `voss_budget_trace`
- CLI: `voss inspect probable <session>` and `voss inspect budget <session>`
- slash: `/probable <session>` and `/btrace <session>`

Do not add `/budget`; it is already the T6 USD budget command.
</objective>

<context>
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-CONTEXT.md
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-RESEARCH.md
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-PATTERNS.md
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-01-recorded-data-inspect-core-PLAN.md

Read first:
- `voss/harness/tools.py` (`make_toolset`, `ToolEntry`)
- `voss/harness/cli.py` (`_build_slash_registry`, `AGENT_COMMANDS`)
- `tests/harness/test_tools.py`
- `tests/harness/test_repl_slash.py`
</context>

<threat_model>
All new tools and slashes are read-only. They must not mutate sessions, write
files, launch processes, or add new recorder/runtime fields. `/budget` is an
existing mutating session-setting surface and must remain untouched; M11 uses
`/btrace` for budget tracing to avoid semantic collision.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Register read-only inspector tools</name>
  <action>
    In `voss/harness/tools.py`, add:

    - `voss_probable_inspect(session: str, decision: int | None = None) -> str`
    - `voss_budget_trace(session: str) -> str`

    Both should call `voss_inspect.load_run()` and the relevant renderer from
    M11-01. Both are `ToolEntry(..., is_mutating=False)`. Catch
    `FileNotFoundError`/`ValueError` and return a concise error string rather
    than raising into the agent loop.
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/test_tools.py -k "ToolEntryClassification or descriptor"</automated>
  </verify>
  <done>`make_toolset()` exposes both tools as non-mutating descriptors.</done>
</task>

<task type="auto">
  <name>Task 2: Add `voss inspect` CLI group</name>
  <action>
    In `voss/harness/cli.py`, add a click group:

    - `voss inspect probable <session-id-or-name> --decision N --cwd .`
    - `voss inspect budget <session-id-or-name> --cwd .`

    Register the group in `AGENT_COMMANDS`. Use `voss_inspect.load_run()` and
    print the same core renderers used by the tools. Keep `voss run` untouched.
  </action>
  <verify>
    <automated>python3 -m voss.harness inspect --help</automated>
  </verify>
  <done>Both subcommands appear in CLI help and read existing session records only.</done>
</task>

<task type="auto">
  <name>Task 3: Add slash commands `/probable` and `/btrace`</name>
  <action>
    Extend `_build_slash_registry()` with:

    - `/probable <session-id-or-name> [--decision N]`
    - `/btrace <session-id-or-name>`

    The handlers should call the same M11-01 renderers. If no session arg is
    provided, default to `ctx.record.id` so a live REPL can inspect the current
    session. Keep `/budget` behavior unchanged.
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/test_repl_slash.py -k "budget or m11 or t6_prd_slash_commands_registered"</automated>
  </verify>
  <done>`/probable` and `/btrace` are registered, `/budget` still passes T6 tests.</done>
</task>

<task type="auto">
  <name>Task 4: Extend tests for CLI/tool/slash surfaces</name>
  <action>
    Extend existing tests surgically:

    - `tests/harness/test_tools.py`: include both new tools in read-only list
      and update non-mutating count by +2.
    - `tests/harness/test_repl_slash.py`: assert `/probable` and `/btrace`
      registration, and assert `/budget` still exists.
    - `tests/harness/test_voss_inspect.py`: add one CLI runner or direct click
      command test using a temporary `.voss/sessions/<id>.json` fixture.
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/test_voss_inspect.py tests/harness/test_tools.py tests/harness/test_repl_slash.py</automated>
  </verify>
  <done>Focused surface tests pass.</done>
</task>

</tasks>

<verification>
Run:

```bash
python3 -m pytest -q tests/harness/test_voss_inspect.py tests/harness/test_tools.py tests/harness/test_repl_slash.py
python3 -m pytest -q tests/harness/tui/test_no_new_runtime_hooks.py
git diff --check
```
</verification>

<success_criteria>
- Probable and budget surfaces are available through CLI, slash, and agent
  tools.
- `/budget` remains the T6 USD-budget command; M11 uses `/btrace`.
- All new tools are read-only.
</success_criteria>
