---
phase: V2-principles-layer
plan: 03
type: execute
wave: 2
depends_on: [V2-01]
files_modified:
  - voss/harness/cli.py
  - tests/harness/test_principles_cli.py
  - tests/harness/test_principles_guard.py
autonomous: true
requirements: [VPRIN-03, VPRIN-07]
must_haves:
  truths:
    - "`voss principles show` exits 0 and lists every active principle with its source label (default vs project)"
    - "With no project file, show lists exactly the six defaults each labeled source=default"
    - "A project file adding key X → show lists six defaults + X(source=project); overriding `tests` shows the project string; disable:[scope] omits scope"
    - "`voss principles show --json` emits machine-readable JSON of the merged set + sources"
    - "A guard test asserts no harness/agent code path conditionals on individual principle keys/strings"
    - "git diff shows zero field changes on RunRecord/SessionRecord/BudgetScope"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "principles click group + show subcommand, registered in AGENT_COMMANDS"
      contains: "principles"
    - path: "tests/harness/test_principles_cli.py"
      provides: "show exit-0 + source-label + json + merge-scenario CLI tests"
      contains: "principles"
    - path: "tests/harness/test_principles_guard.py"
      provides: "no-control-flow-branching guard (AST/grep) + schema-freeze assertion"
      contains: "def test_"
  key_links:
    - from: "voss/harness/cli.py:principles_group"
      to: "AGENT_COMMANDS"
      via: "tuple registration (same as capabilities_group/memory_group)"
      pattern: "principles_group"
    - from: "tests/harness/test_principles_guard.py"
      to: "voss/harness source tree"
      via: "AST/grep assertion that no code branches on principle keys"
      pattern: "ast\\.|grep"
---

<objective>
Add the `voss principles show` CLI command (a `principles` click group + `show` subcommand registered in `AGENT_COMMANDS`, JSON-first per project convention) that prints the merged active principles with each one's source (default vs project). Add the VPRIN-03 no-control-flow-branching guard test (principles are opaque text — no code path conditionals on individual keys/strings) and a schema-freeze assertion that `RunRecord`/`SessionRecord`/`BudgetScope` carry no field changes.

Purpose: Make the active principle set inspectable (VPRIN-07) and lock the opaque-text / immutable / schema-freeze invariants (VPRIN-03 + hard constraint).
Output: `voss principles show` command + guard test + schema-freeze test.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V2-principles-layer/V2-SPEC.md
@.planning/phases/V2-principles-layer/V2-CONTEXT.md

<interfaces>
<!-- CLI group registration pattern + the resolver to call -->
From voss/harness/cli.py:
- `@click.group("capabilities") def capabilities_group()` (L3672) with `@capabilities_group.command("list")` + `--json` flag (L3677-3701) — the EXACT click-group + JSON-first pattern to mirror for `principles`/`show`. Note the `import json as json_lib` local import + `click.echo(json_lib.dumps(...))` convention and `--cwd` option.
- `AGENT_COMMANDS = (do_cmd, ..., hooks_group, capabilities_group)` (L3740-3769) — append `principles_group` here so `register()` (L3772) attaches it.

From voss/harness/principles.py (V2-01 output):
- `resolve_with_sources(cwd) -> tuple[tuple[str, str, str], ...]` returning `(key, text, source)` with source ∈ {"default","project"} — the data `show` prints.
- `VossPrinciplesConfigError` — show should surface a clear error (exit nonzero) if the project file is malformed.

Schema-freeze targets (must NOT change — hard constraint, O1/V4 redaction invariant):
- `voss/harness/session.py` — `@dataclass class RunRecord` (L118), `@dataclass class SessionRecord` (L155). (V2-CONTEXT cites recorder.py; the dataclasses actually live in session.py — assert against session.py.)
- `voss_runtime/budget.py` — `class BudgetScope` (L12).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: `voss principles show` click group + subcommand</name>
  <files>voss/harness/cli.py, tests/harness/test_principles_cli.py</files>
  <read_first>
    - voss/harness/cli.py (L3672-3701 capabilities_group + list pattern with --json; L3740-3775 AGENT_COMMANDS + register)
    - voss/harness/principles.py (V2-01: resolve_with_sources, VossPrinciplesConfigError)
    - .planning/phases/V2-principles-layer/V2-SPEC.md (Requirement 6 — `voss principles show`)
    - .planning/phases/V2-principles-layer/V2-CONTEXT.md (D-06 — click group → AGENT_COMMANDS, JSON-first, per-principle source)
  </read_first>
  <action>
    In `voss/harness/cli.py` add `@click.group("principles") def principles_group()` and a `@principles_group.command("show")` subcommand mirroring `capabilities_group`/`capabilities_list_cmd` (same `--cwd` `click.Path` option + `--json` flag + `import json as json_lib` local-import convention). `show` resolves the active merged set via `resolve_with_sources(Path(cwd_str).resolve())` and: in `--json` mode emits `click.echo(json_lib.dumps(...))` of a list/dict of `{key, text, source}` entries (JSON-first per D-06); in human mode prints one line per principle showing key, source label (default vs project), and text (lock formatting here — Claude's discretion: e.g. `key  [source]  text` aligned). On a malformed project file, catch `VossPrinciplesConfigError`, print the message to stderr, and exit nonzero (mirror the `capabilities_inspect_cmd` `click.exceptions.Exit(1)` error path). Register `principles_group` in the `AGENT_COMMANDS` tuple (L3740-3769) so `register()` attaches it. Create `tests/harness/test_principles_cli.py` using click's `CliRunner` (follow the existing CLI-test pattern in tests/harness/test_cli.py / test_capabilities_cli.py): assert (a) no project file → exit 0 + all six default keys each labeled default; (b) a tmp `.voss/principles.yml` adding key `bias` → exit 0 + six defaults + bias(project); overriding `tests` → project string shown; `disable: [scope]` → scope absent; (c) `--json` → valid JSON parsing to the merged set with sources; (d) malformed file → nonzero exit + non-silent error.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_principles_cli.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `voss principles show` exits 0 and lists every active principle with its source (default/project); no-file case lists exactly the six defaults as source=default.
    - Project-file scenarios (add key / override `tests` / `disable: [scope]`) reflect correctly in the output.
    - `voss principles show --json` emits parseable JSON of the merged set + sources.
    - `principles_group` is in `AGENT_COMMANDS`; malformed file → nonzero exit + non-silent error.
    - `.venv/bin/python -m pytest tests/harness/test_principles_cli.py -x -q` exits 0.
  </acceptance_criteria>
  <done>`voss principles show` (+ `--json`) prints the merged active principles with per-principle source, is registered in AGENT_COMMANDS, errors loudly on malformed input; CLI tests green.</done>
</task>

<task type="auto">
  <name>Task 2: No-branching guard test + schema-freeze assertion</name>
  <files>tests/harness/test_principles_guard.py</files>
  <read_first>
    - voss/harness/principles.py, voss/harness/agent.py (the code that handles principles — guard scans these for key-conditionals)
    - voss/harness/session.py (L117-160 RunRecord/SessionRecord field lists — schema-freeze targets)
    - voss_runtime/budget.py (L12 BudgetScope — schema-freeze target)
    - .planning/phases/V2-principles-layer/V2-SPEC.md (Requirement 2 + Acceptance Criteria 7 & 8)
    - .planning/phases/V2-principles-layer/V2-CONTEXT.md (D-07 — no-control-flow-branching guard)
  </read_first>
  <action>
    Create `tests/harness/test_principles_guard.py` with two guards. GUARD 1 (VPRIN-03 no-control-flow-branching): assert no harness/agent code path conditionals on individual principle keys/strings. Implement via AST: parse `voss/harness/principles.py` and `voss/harness/agent.py` (and any module that consumes principles), walk for `ast.If`/`ast.Compare`/`ast.Match` nodes whose operands are string literals equal to any of the six principle keys (diff/evidence/tests/scope/review/reversibility) OR equal to any default principle text — fail if found (principles must be treated as opaque data, never branched on). Allow the literal keys to appear in DATA contexts (the `DEFAULT_PRINCIPLES` constant definition, dict/tuple construction) — only flag them in conditional/branch positions. Document the rule in a module docstring. GUARD 2 (schema-freeze hard constraint): assert the exact field name sets of `RunRecord` and `SessionRecord` (import from `voss.harness.session`) and `BudgetScope` (import from `voss_runtime.budget`) match a frozen expected set captured in the test (use `dataclasses.fields(...)` names, or `__dataclass_fields__` keys / `__annotations__` for BudgetScope) — so any field add/remove fails the test, protecting the O1/V4 redaction invariant. Add a comment that V2 must add ZERO fields here (audit recording of principles is V9).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_principles_guard.py -x -q && git diff --stat voss/harness/session.py voss_runtime/budget.py | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - GUARD 1: an AST scan of principles.py/agent.py finds no conditional/branch keyed on any of the six principle keys or any default principle text; `pytest tests/harness/test_principles_guard.py` exits 0.
    - GUARD 2: the field-name sets of RunRecord/SessionRecord/BudgetScope equal the frozen expected sets; adding/removing a field would fail the test.
    - `git diff --stat voss/harness/session.py voss_runtime/budget.py` shows zero field changes (no V2 edits to these schema files).
    - `.venv/bin/python -m pytest tests/harness/test_principles_guard.py -x -q` exits 0.
  </acceptance_criteria>
  <done>A no-control-flow-branching AST guard and a schema-freeze field-set assertion both pass; RunRecord/SessionRecord/BudgetScope provably unchanged.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI invocation → principles resolver | `voss principles show` reads the project `.voss/principles.yml` (untrusted) via the V2-01 loader. |
| code review → opaque-text invariant | The guard test is the enforcement boundary keeping principle text non-executable / non-branching. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V2-07 | Information Disclosure | `principles show` output | accept | Prints only project-authored principle text + source labels; no secrets/PII surface. |
| T-V2-08 | Tampering | schema-freeze invariant | mitigate | GUARD 2 field-set assertion fails on any RunRecord/SessionRecord/BudgetScope field change (protects O1/V4 redaction invariant). |
| T-V2-09 | Elevation of Privilege | principle-keyed control flow | mitigate | GUARD 1 AST scan fails if any code branches on a principle key/string (principles stay opaque data). |
| T-V2-SC | Tampering | npm/pip installs | mitigate | No package installs in this plan; legitimacy gate N/A. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_principles_cli.py tests/harness/test_principles_guard.py -q` passes.
- `git diff --stat voss/harness/session.py voss_runtime/budget.py` shows no field changes (schema-freeze).
- `grep -n "principles_group" voss/harness/cli.py` confirms group defined + registered in AGENT_COMMANDS.
- The harness redaction test still passes (run the existing redaction test to confirm the invariant stays green).
</verification>

<success_criteria>
- `voss principles show` (+ `--json`) inspects the merged active set with per-principle source (VPRIN-07).
- No-branching guard + schema-freeze assertion both green (VPRIN-03 + hard constraint).
- RunRecord/SessionRecord/BudgetScope provably unchanged.
</success_criteria>

<output>
Create `.planning/phases/V2-principles-layer/V2-03-SUMMARY.md` when done.
</output>
