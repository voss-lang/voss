---
phase: T6-slash-debt
plan: 02
type: execute
wave: 2
depends_on: ["T6-01-cost-by-tool-approximation"]
files_modified:
  - voss/harness/cli.py
  - tests/harness/test_repl_slash.py
autonomous: true
requirements: [SLASH-01, SLASH-02, SLASH-03, SLASH-04, SLASH-05, SLASH-06, SLASH-07]
must_haves:
  truths:
    - "Typing /help in the REPL prints slashes organised under named group headers, each with its one-line description"
    - "Every registered non-hidden slash still appears in /help output (no slash silently dropped by grouping)"
    - "voss --help contains exactly one signpost line pointing at the in-REPL /help; the full slash list is NOT duplicated into the CLI"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "Grouped _print_slash_help renderer + one-line CLI signpost in the main group docstring"
      contains: "Editing"
    - path: "tests/harness/test_repl_slash.py"
      provides: "Grouped-help test extending TestSlashHelp (asserts group headers + no dropped slashes)"
      contains: "Editing"
  key_links:
    - from: "voss/harness/cli.py _print_slash_help"
      to: "registry.ids() / registry.lookup(name).help"
      via: "group→slash-name buckets rendered with the help_lines width-align style"
      pattern: "_print_slash_help"
---

<objective>
Make slash discoverability match the SC#3/D-04 contract: replace the flat
alphabetical `_print_slash_help` with a GROUPED renderer (named group headers +
one-line description per slash, long-tail bucketed so nothing disappears), and
add exactly ONE signpost line to the `main` group docstring so `voss --help`
points users at the canonical in-REPL `/help` without duplicating the slash list.
Covers the SC#3 discoverability success criterion for all SLASH-01..07.

Purpose: PRD §2.4 / ROADMAP SC#3 — "help discoverability matches Codex",
operationalized (D-04) as: every slash in `/help`, grouped, one-line description;
`voss --help` signposts once (no two-place drift).
Output: Grouped `_print_slash_help` + one-line `main` docstring signpost in
cli.py; grouped-help test in test_repl_slash.py.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/T6-slash-debt/T6-CONTEXT.md
@.planning/phases/T6-slash-debt/T6-PATTERNS.md
@.planning/phases/T6-slash-debt/T6-01-SUMMARY.md

<interfaces>
<!-- Extracted from codebase. No exploration required. -->

Current flat renderer being replaced, voss/harness/cli.py:1587-1589:
  _print_slash_help(registry=None) → registry or _build_slash_registry()
  → click.echo("\n".join(registry.help_lines()))

Registry read API (voss/harness/slash.py):
  registry.ids(include_hidden=False) -> list[str]   # sorted, dedup'd, non-hidden (slash.py:33-43)
  registry.lookup(name) -> SlashCommand | None      # slash.py:30-31
  SlashCommand fields (slash.py:11-18): .name .help .aliases .mutating .hidden
  help_lines() width-align style to preserve per group (slash.py:45-52):
    width = max(len(c.name) for c in commands); f"{c.name:<{width}}  {c.help}"

LIVE registered slash names (voss/harness/cli.py:901-958) — finalize buckets against THIS list:
  /help /exit(/quit) /clear /cost /budget /why /diff /apply /discard /resume
  /tools /login /model /mode /save-session /recall /forget /memory /save
  /analyze /save-plan /plugins /plugin /skills /skill /agents /agent

Edit target for the CLI signpost — the main group docstring (voss/harness/cli.py:2197-2201):
  """voss · agent (standalone harness invocation).

  Usually invoked as `voss do` / `voss chat`. Bare invocation drops into chat.
  """
  (context_settings is help_option_names at 2192-2195 — do NOT add an epilog= kwarg;
   the docstring IS the --help body. Mirror the chat_cmd docstring style, cli.py:1195.)

Existing test that constrains grouping, tests/harness/test_repl_slash.py:81-86:
  TestSlashHelp.test_help_lists_new_commands asserts /login /model /mode --confirm
  all still appear in _print_slash_help() output — grouping must NOT drop them.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Replace _print_slash_help with a grouped renderer (D-04)</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - voss/harness/cli.py:1587-1589 (the flat renderer being replaced)
    - voss/harness/cli.py:901-958 (the live SlashCommand registrations — the authoritative slash set + each command's existing one-line `help` string; D-04 needs NO new descriptions, only grouping)
    - voss/harness/slash.py:30-52 (`ids`, `lookup`, `SlashCommand` fields, the `help_lines` width-align style to preserve per group)
    - T6-PATTERNS.md "Edit Site 2" (grouping spec + the long-tail-bucket-don't-drop rule + the TestSlashHelp constraint)
  </read_first>
  <behavior>
    - _print_slash_help() output contains the literal group headers `Editing`, `Session`, `Insight`, `Control`.
    - Under `Editing`: /diff /apply /discard appear with their existing one-line help.
    - Under `Session`: /resume /budget /cost /clear /save-session appear.
    - Under `Insight`: /why /tools /analyze appear.
    - Under `Control`: /help /exit /mode /model appear.
    - Every registry.ids() name not assigned to a named group appears under a fallback bucket header (e.g. `Other`) — NO registered non-hidden slash is omitted.
    - The pre-existing TestSlashHelp tokens (/login /model /mode --confirm) all still appear in the output.
    - Within each group, rows keep the help_lines-style left-padded name alignment.
  </behavior>
  <action>
    Rewrite `_print_slash_help` (voss/harness/cli.py:1587-1589) to render GROUPED
    output. Define explicit group→slash-name buckets, finalized against the live
    registrations at cli.py:901-958: `Editing` = `/diff` `/apply` `/discard`;
    `Session` = `/resume` `/budget` `/cost` `/clear` `/save-session`;
    `Insight` = `/why` `/tools` `/analyze`; `Control` = `/help` `/exit` `/mode`
    `/model`. For each named group in order, echo the header (the literal group
    name) then the group's members rendered with the existing `help_lines`-style
    width-aligned `name`-left-pad format (compute width per group), reading each
    slash's existing one-line `help` via `registry.lookup(name)`. After the named
    groups, collect every `registry.ids(include_hidden=False)` name NOT already
    placed and echo them under a fallback bucket header (`Other`) so nothing
    silently disappears (M9-03 SlashPalette parity, D-05). Do NOT author new
    descriptions — every `SlashCommand` already carries its `help` string. Keep
    the `registry = registry or _build_slash_registry()` resolution line. Output
    via `click.echo`. No fenced code in this action — preserve the `help_lines`
    alignment style from slash.py:45-52.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "from voss.harness.cli import _print_slash_help; _print_slash_help()" 2>&1 | grep -q "Editing" && python -c "from voss.harness.cli import _print_slash_help; _print_slash_help()" 2>&1 | grep -q "Session"</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from voss.harness.cli import _print_slash_help as h; h()"` output contains the literal group headers `Editing`, `Session`, `Insight`, `Control`.
    - That same output contains `/diff`, `/apply`, `/discard`, `/why`, `/resume`, `/cost`, `/budget`, `/login`, `/model`, `/mode` (no slash dropped by grouping).
    - `python -c "import ast; ast.parse(open('voss/harness/cli.py').read())"` exits 0.
    - The output's slash count equals `len(_build_slash_registry().ids())` (every non-hidden slash placed in some group or the Other bucket) — verifiable: every name from `_build_slash_registry().ids()` appears in the rendered text.
  </acceptance_criteria>
  <done>`_print_slash_help` renders four named group headers plus an Other fallback bucket; every registered non-hidden slash appears exactly once with its existing one-line help; cli.py parses.</done>
</task>

<task type="auto">
  <name>Task 2: Add the single voss --help signpost line + grouped-help test</name>
  <files>voss/harness/cli.py, tests/harness/test_repl_slash.py</files>
  <read_first>
    - voss/harness/cli.py:2192-2205 (the `main` group: `context_settings` with `help_option_names`, the docstring that IS the --help body)
    - voss/harness/cli.py:1195 (`chat_cmd` docstring — the one-line style to mirror)
    - tests/harness/test_repl_slash.py:81-86 (the `TestSlashHelp` class to extend; keep its existing token assertions intact)
    - T6-PATTERNS.md "Edit Site 3" (one signpost line only, no `epilog=` kwarg, extend the docstring)
  </read_first>
  <action>
    Add exactly ONE signpost line to the `main` group docstring
    (voss/harness/cli.py:2197-2201) pointing at the canonical in-REPL `/help`
    — e.g. a trailing sentence like `Interactive commands: run` then a
    backticked `voss chat` then `, then /help`. Match the existing terse
    docstring style (mirror `chat_cmd`'s one-line docstring at cli.py:1195). Do
    NOT add an `epilog=` kwarg and do NOT duplicate the slash list into the CLI
    (D-04 — single canonical `/help`, signpost only, no two-place drift). Then in
    `tests/harness/test_repl_slash.py`, extend the existing `TestSlashHelp` class
    (do not remove its existing `test_help_lists_new_commands`) with a new test
    method that calls `_print_slash_help()` and asserts the four group headers
    (`Editing`, `Session`, `Insight`, `Control`) appear AND that `/diff`,
    `/resume`, `/why` still appear (no slash dropped). This is the SC#3
    discoverability integration check. No fenced code in this action.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest tests/harness/test_repl_slash.py::TestSlashHelp -q 2>&1 | tail -3 && python -m voss.harness --help 2>&1 | grep -c "/help"</automated>
  </verify>
  <acceptance_criteria>
    - `python -m voss.harness --help` output contains exactly one line matching both `voss chat` and `/help` (`python -m voss.harness --help 2>&1 | grep -c '/help'` returns `1`).
    - `python -m voss.harness --help` output does NOT list individual slash commands like `/diff` or `/budget` (no slash-list duplication — grep for `/diff` returns nothing).
    - `python -m pytest tests/harness/test_repl_slash.py::TestSlashHelp -q` exits 0.
    - `grep -n "epilog=" voss/harness/cli.py` shows no `epilog=` was added to the `main` group.
    - The pre-existing `TestSlashHelp.test_help_lists_new_commands` still passes (its /login /model /mode --confirm assertions intact).
  </acceptance_criteria>
  <done>`voss --help` carries exactly one signpost line (no slash list); the grouped-help test passes alongside the unchanged pre-existing TestSlashHelp test.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| REPL user → `/help` | `/help` takes no untrusted args; renders read-only registry metadata |
| CLI user → `voss --help` | Static docstring text rendered by Click; no input crosses |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T6-03 | Information Disclosure | grouped `/help` output | accept | Renders only slash names + their static one-line `help` strings already shipped in the binary; no session/secret data. |
| T-T6-04 | Repudiation | `voss --help` signpost text | accept | Static docstring, no behavior change, no state. Low-value, no integrity concern. |
| T-T6-SC | Tampering | npm/pip/cargo installs | mitigate | No package installs in this plan (harden+test, zero new deps per D-08). N/A — no slopcheck checkpoint required. |
</threat_model>

<verification>
- `python -m pytest tests/harness/test_repl_slash.py -q` exits 0 (full file green, including TestSlashHelp).
- `python -c "from voss.harness.cli import _print_slash_help as h; h()"` shows the four group headers + every registered slash.
- `python -m voss.harness --help | grep -c "/help"` returns 1; grep for `/diff` in the same output returns nothing.
</verification>

<success_criteria>
- SC#3 met: every slash appears in `/help`, grouped under named headers with a one-line description; `voss --help` signposts once with no slash-list duplication.
- No registered non-hidden slash is dropped by grouping (long tail bucketed under Other).
</success_criteria>

<output>
Create `.planning/phases/T6-slash-debt/T6-02-SUMMARY.md` when done.
</output>
