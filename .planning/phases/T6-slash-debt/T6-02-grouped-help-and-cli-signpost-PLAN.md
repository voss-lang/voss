---
phase: T6-slash-debt
plan: 02
type: execute
wave: 2
depends_on: [T6-01-cost-by-tool-approximation]
files_modified:
  - voss/harness/cli.py
  - voss/cli.py
  - tests/harness/test_repl_slash.py
autonomous: true
requirements: [SLASH-01, SLASH-02, SLASH-03, SLASH-04, SLASH-05, SLASH-06, SLASH-07]
must_haves:
  truths:
    - "Typing /help in the REPL prints slashes organised under named group headers, each slash keeping its one-line description"
    - "Every registered non-hidden slash appears in /help output exactly once (no slash silently dropped by grouping)"
    - "BOTH the production `voss --help` (voss.cli:main) AND `python -m voss.harness --help` contain exactly one signpost line pointing at the in-REPL /help; the full slash list is NOT duplicated into either CLI"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "Grouped _print_slash_help renderer + one-line signpost in the harness main group docstring"
      contains: "Editing"
    - path: "voss/cli.py"
      provides: "Same one-line in-REPL /help signpost in the production voss.cli:main docstring (operator-approved D-04 widening)"
      contains: "/help"
    - path: "tests/harness/test_repl_slash.py"
      provides: "Grouped-help test extending TestSlashHelp (asserts group headers + no dropped slashes)"
      contains: "Editing"
  key_links:
    - from: "voss/harness/cli.py _print_slash_help"
      to: "registry.ids() / registry.lookup(name).help"
      via: "group→slash-name buckets rendered with the help_lines width-align style; ungrouped names fall to an Other bucket"
      pattern: "_print_slash_help"
    - from: "voss/cli.py main + voss/harness/cli.py main docstrings"
      to: "in-REPL /help"
      via: "the SAME one signpost line in BOTH entry docstrings; no epilog= kwarg; no slash-list duplication"
      pattern: "/help"
---

<objective>
Make slash discoverability match the SC#3 / D-04 contract: replace the flat
alphabetical `_print_slash_help` (cli.py:1587-1589) with a GROUPED renderer
(named group headers + one-line description per slash, long-tail bucketed under
`Other` so nothing disappears), and add exactly ONE signpost line — the SAME
text — to BOTH CLI entry docstrings (`voss/cli.py` `main` AND
`voss/harness/cli.py` `main`) so every `--help` surface points users at the
canonical in-REPL `/help` WITHOUT duplicating the slash list. Covers the SC#3
discoverability success criterion for all SLASH-01..07.

Purpose: PRD §2.4 / ROADMAP T6 SC#3 — "help discoverability matches Codex",
operationalized by D-04 as: every slash in `/help`, grouped, one-line
description; the CLI `--help` signposts once (single canonical source, no
two-place drift). This depends on T6-01 because both plans edit
`voss/harness/cli.py` (file-ownership serialization) and the grouped help must
list the post-T6-01 `/cost` description.

D-04 SCOPE WIDENING (W3 — deliberate, operator-approved): the original D-04
cited only the `python -m voss.harness` entry. The operator widened it so the
signpost ALSO lands in the production `voss = voss.cli:main` entry
(`voss/cli.py:~149-155`) — what pip/npm users actually see on `voss --help`.
Both docstrings get the SAME one-line signpost; this is NOT slash-list
duplication (still a single canonical `/help`). Record this widening verbatim in
T6-02-SUMMARY per `<output>`.
Output: Grouped `_print_slash_help` + one-line signpost in BOTH `main`
docstrings; grouped-help test in test_repl_slash.py.
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

<!-- ENV NOTE (W4): All verify/acceptance commands assume the project venv is
     active (execute-plan activates it); otherwise prefix `.venv/bin/`. The
     production entry is `voss = voss.cli:main`; if the `voss` console script
     is not on PATH, `python -m voss.cli --help` (or `.venv/bin/voss --help`)
     is the equivalent invocation. -->

<interfaces>
<!-- Extracted from codebase. No exploration required. -->

Current flat renderer being replaced, voss/harness/cli.py:1587-1589:
  def _print_slash_help(registry: SlashRegistry | None = None) -> None:
      registry = registry or _build_slash_registry()
      click.echo("\n".join(registry.help_lines()))

Registry read API (voss/harness/slash.py):
  registry.ids(include_hidden=False) -> list[str]   # sorted, dedup'd, non-hidden (slash.py:33-43)
  registry.lookup(name) -> SlashCommand | None      # slash.py:30-31
  SlashCommand fields (slash.py:11-18): .name .help .aliases .mutating .hidden
  help_lines() width-align style to PRESERVE per group (slash.py:45-52):
    width = max(len(c.name) for c in commands); rows are f"{c.name:<{width}}  {c.help}"

LIVE registered slash names (voss/harness/cli.py:901-958) — finalize the buckets
against THIS exact set; every name must land in a named group OR the Other bucket:
  /help /exit(alias /quit) /clear /cost /budget /why /diff /apply /discard
  /resume /tools /login /model /mode /save-session /recall /forget /memory
  /save /analyze /save-plan /plugins /plugin /skills /skill /agents /agent
  (each SlashCommand already carries its one-line `help` string — D-04 needs
   NO new descriptions, only grouping.)

Signpost edit target #1 — the harness main group docstring (voss/harness/cli.py:2197-2201):
  @click.pass_context
  def main(ctx: click.Context) -> None:
      """voss · agent (standalone harness invocation).

      Usually invoked as `voss do` / `voss chat`. Bare invocation drops into chat.
      """
  context_settings is help_option_names at cli.py:2192-2195 — do NOT add an
  epilog= kwarg; the docstring IS the --help body. Mirror the terse one-line
  style of the chat_cmd docstring (cli.py:1195).

Signpost edit target #2 (W3 widening) — the production voss.cli:main docstring
(voss/cli.py:~149-155): the `voss = voss.cli:main` console-script entry; its
docstring is the body rendered by `voss --help` for pip/npm users. Add the SAME
one signpost line, same style; do NOT add an epilog= kwarg; do NOT list slashes.
(The executor must read voss/cli.py around the `main` definition to confirm the
exact docstring lines before editing — the ~149-155 range is approximate.)

Existing test that constrains grouping, tests/harness/test_repl_slash.py:81-86:
  class TestSlashHelp:
      def test_help_lists_new_commands(self, capsys):
          _print_slash_help()
          captured = capsys.readouterr()
          for token in ("/login", "/model", "/mode", "--confirm"):
              assert token in captured.out
  → grouping must NOT drop these tokens (the long tail must be bucketed, not omitted).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Replace _print_slash_help with a grouped renderer (D-04)</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - voss/harness/cli.py:1587-1589 (the flat `_print_slash_help` being replaced — keep its `registry = registry or _build_slash_registry()` resolution line)
    - voss/harness/cli.py:901-958 (the live `SlashCommand` registrations — the AUTHORITATIVE slash set + each command's existing one-line `help` string; D-04 needs NO new descriptions, only grouping; finalize bucket membership against THIS list)
    - voss/harness/slash.py:30-52 (`ids`, `lookup`, `SlashCommand` fields, the `help_lines` width-align style at 45-52 to preserve PER GROUP)
    - T6-PATTERNS.md "Edit Site 2" (the grouped-renderer spec + the long-tail Other bucket rule + the TestSlashHelp constraint)
  </read_first>
  <behavior>
    - _print_slash_help() output contains the literal group headers `Editing`, `Session`, `Insight`, `Control`.
    - Under `Editing`: /diff /apply /discard appear with their existing one-line help.
    - Under `Session`: /resume /budget /cost /clear /save-session appear.
    - Under `Insight`: /why /tools /analyze appear.
    - Under `Control`: /help /exit /mode /model appear.
    - Every registry.ids() name NOT assigned to a named group appears under a fallback `Other` header — NO registered non-hidden slash is omitted.
    - The pre-existing TestSlashHelp tokens (/login /model /mode --confirm) all still appear in the output.
    - Within each group, rows keep the help_lines-style left-padded name alignment (width computed per group).
    - Each slash appears exactly once (no duplication across buckets).
  </behavior>
  <action>
    Rewrite `_print_slash_help` (voss/harness/cli.py:1587-1589) to render GROUPED
    output. Keep the `registry = registry or _build_slash_registry()` resolution
    line. Define explicit ordered group→slash-name buckets, finalized against the
    live registrations at cli.py:901-958: `Editing` = `/diff` `/apply`
    `/discard`; `Session` = `/resume` `/budget` `/cost` `/clear`
    `/save-session`; `Insight` = `/why` `/tools` `/analyze`; `Control` =
    `/help` `/exit` `/mode` `/model`. For each named group in order, echo the
    header (the literal group name) then that group's members rendered with the
    existing `help_lines`-style width-aligned `name`-left-pad format (compute
    width PER GROUP), reading each slash's existing one-line `help` via
    `registry.lookup(name)`. After the named groups, collect every
    `registry.ids(include_hidden=False)` name NOT already placed and echo them
    under a fallback `Other` header so nothing silently disappears (M9-03
    SlashPalette parity, D-05). Do NOT author new descriptions — every
    `SlashCommand` already carries its `help` string (D-04 = grouping only).
    Output via `click.echo`. Each slash must appear exactly once. No fenced code
    in this action — preserve the `help_lines` alignment style from
    slash.py:45-52.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "import ast; ast.parse(open('voss/harness/cli.py').read())" && python -c "from voss.harness.cli import _print_slash_help as h; h()" 2>&1 | grep -q "Editing" && python -c "from voss.harness.cli import _print_slash_help as h; h()" 2>&1 | grep -q "Other"</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "import ast; ast.parse(open('voss/harness/cli.py').read())"` exits 0.
    - `python -c "from voss.harness.cli import _print_slash_help as h; h()"` output contains the literal group headers `Editing`, `Session`, `Insight`, `Control`, and a fallback `Other`.
    - That same output contains `/diff`, `/apply`, `/discard`, `/why`, `/resume`, `/cost`, `/budget`, `/login`, `/model`, `/mode` (no slash dropped by grouping).
    - Every name from `_build_slash_registry().ids()` appears in the rendered text (verify: `python -c "from voss.harness.cli import _build_slash_registry,_print_slash_help; ..."` — each id substring present), and each appears exactly once.
    - The existing one-line `help` strings are preserved verbatim (e.g. the output still contains the `/cost` help text registered at cli.py:905-909, post-T6-01).
  </acceptance_criteria>
  <done>`_print_slash_help` renders four named group headers plus an `Other` fallback bucket; every registered non-hidden slash appears exactly once with its existing one-line help; cli.py parses; TestSlashHelp tokens preserved.</done>
</task>

<task type="auto">
  <name>Task 2: Add the single in-REPL /help signpost to BOTH CLI entry docstrings (W3) + grouped-help test</name>
  <files>voss/harness/cli.py, voss/cli.py, tests/harness/test_repl_slash.py</files>
  <read_first>
    - voss/harness/cli.py:2192-2205 (the harness `main` group: `context_settings` with `help_option_names`, the docstring that IS the `python -m voss.harness --help` body)
    - voss/cli.py around the `main` definition (~149-155 — read to confirm the exact docstring lines; this is the production `voss = voss.cli:main` entry rendered by `voss --help`)
    - voss/harness/cli.py:1195 (`chat_cmd` docstring — the terse one-line style to mirror in BOTH docstrings)
    - tests/harness/test_repl_slash.py:81-86 (the `TestSlashHelp` class to EXTEND; keep its existing `test_help_lists_new_commands` token assertions intact)
    - T6-PATTERNS.md "Edit Site 3" (the dual-docstring signpost spec: same one line in both `main` docstrings, no `epilog=`, no slash-list duplication)
  </read_first>
  <action>
    Add exactly ONE signpost line — the SAME text in BOTH entry docstrings — of
    the form `Interactive commands: run` + a backticked `voss chat` + `, then
    /help`, matching the existing terse docstring style (mirror `chat_cmd`'s
    one-line docstring at cli.py:1195). (a) Add it to the harness `main` group
    docstring (voss/harness/cli.py:2197-2201). (b) W3 widening — add the IDENTICAL
    line to the production `voss/cli.py` `main` docstring (~149-155; read the
    file to confirm exact lines first). Do NOT add an `epilog=` kwarg to either
    `@click.group`/`@click.command` and do NOT duplicate the slash list into
    either CLI help (D-04 — single canonical `/help`, signpost only in both
    entries, no two-place slash drift; the signpost itself is intentionally
    duplicated per the operator-approved widening, the slash LIST is not). Then in
    `tests/harness/test_repl_slash.py`, EXTEND the existing `TestSlashHelp` class
    (do NOT remove or weaken its existing `test_help_lists_new_commands`) with a
    new test method that calls `_print_slash_help()` and asserts the four group
    headers (`Editing`, `Session`, `Insight`, `Control`) appear AND that `/diff`,
    `/resume`, `/why` still appear (no slash dropped by grouping). This is the
    SC#3 discoverability integration check. No fenced code in this action.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest tests/harness/test_repl_slash.py::TestSlashHelp -q --tb=short; echo "pytest-exit:$?"; test "$(python -m voss.harness --help 2>&1 | grep -c '/help')" = "1" && test "$(python -m voss.cli --help 2>&1 | grep -c '/help')" = "1" && echo "signpost-both:OK"</automated>
  </verify>
  <acceptance_criteria>
    - `python -m voss.harness --help 2>&1 | grep -c '/help'` returns exactly `1` (exactly one signpost line referencing the in-REPL `/help` in the harness entry).
    - `python -m voss.cli --help 2>&1 | grep -c '/help'` returns exactly `1` (the SAME signpost line in the production `voss.cli:main` entry that pip/npm `voss --help` users see).
    - On BOTH `--help` outputs, `grep -c 'voss chat'` returns `1` and that is the same signpost line (it mentions both `voss chat` and `/help`).
    - `python -m voss.harness --help 2>&1 | grep -E '/diff|/budget|/discard|/resume'` returns NO match AND `python -m voss.cli --help 2>&1 | grep -E '/diff|/budget|/discard|/resume'` returns NO match (no slash-list duplication into either CLI — proves there is no second slash list, only the single signpost).
    - `grep -n "epilog=" voss/harness/cli.py voss/cli.py` shows NO `epilog=` was added to either `main`.
    - `python -m pytest tests/harness/test_repl_slash.py::TestSlashHelp -q` exits 0, AND the pre-existing `test_help_lists_new_commands` still passes (its `/login` `/model` `/mode` `--confirm` assertions intact).
    - `python -m pytest tests/harness/test_repl_slash.py -q` exits 0 (full file green).
  </acceptance_criteria>
  <done>BOTH `voss --help` (voss.cli:main) AND `python -m voss.harness --help` carry exactly one identical signpost line (no slash list, no `epilog=` in either); the new grouped-help test passes alongside the unchanged pre-existing `TestSlashHelp` test; full slash test file green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| REPL user → `/help` | `/help` takes no untrusted args; it renders read-only registry metadata (slash names + static `help` strings) |
| CLI user → `voss --help` / `python -m voss.harness --help` | Static docstring text rendered by Click; no user input crosses into it |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T6-03 | Information Disclosure | grouped `/help` output | accept | Renders only slash names + their static one-line `help` strings already shipped in the binary; no session, file, or secret data is read or surfaced. No input sink — pure string assembly over the in-process registry. |
| T-T6-04 | Tampering | the two `main` signpost docstrings (`voss/cli.py`, `voss/harness/cli.py`) | accept | Static docstrings, no behavior change, no state, no input. Low-value, no integrity concern; Click renders them verbatim. The deliberate duplication is the same constant string in two entry points — no drift surface beyond a one-line literal. |
| T-T6-SC | Tampering | npm/pip/cargo installs | mitigate | No package installs in this plan (harden+test, zero new deps per D-08). N/A — no slopcheck checkpoint required; no `[ASSUMED]`/`[SUS]` packages introduced. |

No `high`-severity threat. ASVS L1: the help renderer is pure read-only string
output over the in-process slash registry — no input validation, auth, or
injection sink is added or touched.
</threat_model>

<verification>
- `python -m pytest tests/harness/test_repl_slash.py -q` exits 0 (full file green, including the unchanged TestSlashHelp.test_help_lists_new_commands).
- `python -c "from voss.harness.cli import _print_slash_help as h; h()"` shows the four group headers + an `Other` bucket + every registered slash exactly once.
- `python -m voss.harness --help 2>&1 | grep -c '/help'` returns `1` AND `python -m voss.cli --help 2>&1 | grep -c '/help'` returns `1`; neither output has a second slash list (grep for `/diff`/`/budget`/`/resume` returns nothing in either).
- `grep -n "epilog=" voss/harness/cli.py voss/cli.py` returns no match.
</verification>

<success_criteria>
- SC#3 met: every slash appears in `/help`, grouped under named headers (Editing / Session / Insight / Control + Other) with its existing one-line description; BOTH `voss --help` (voss.cli:main) and `python -m voss.harness --help` signpost once at the in-REPL `/help` with no slash-list duplication.
- No registered non-hidden slash is dropped by grouping (long tail bucketed under `Other`); each slash appears exactly once.
</success_criteria>

<output>
Create `.planning/phases/T6-slash-debt/T6-02-SUMMARY.md` when done. The SUMMARY
MUST record: (1) the finalized group→slash membership map (the exact buckets +
whichever names landed in `Other`) so M9-03 SlashPalette and any later slash
addition can reconcile against it; (2) verbatim, that the dual-CLI signpost
(same line in BOTH `voss/cli.py` `main` AND `voss/harness/cli.py` `main`) is a
DELIBERATE, OPERATOR-APPROVED D-04 scope widening — the original D-04 cited only
the `python -m voss.harness` entry; the operator widened it so pip/npm `voss
--help` users also see the in-REPL `/help` signpost. This is signpost
duplication (one constant line), NOT slash-list duplication.
</output>
