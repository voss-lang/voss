---
phase: V1-capability-surface-hardening
plan: 02
type: execute
wave: 2
depends_on: ["V1-01"]
files_modified:
  - voss/harness/cli.py
  - tests/harness/test_capabilities_cli.py
autonomous: true
requirements: [VCAP-04, VCAP-05]
must_haves:
  truths:
    - "An operator can run `voss capabilities list` and see every capability grouped under its group header"
    - "An operator can run `voss capabilities inspect <name>` and see full normalized detail for one capability"
    - "Both commands emit machine-readable JSON under `--json`"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "capabilities click group with list + inspect subcommands"
      contains: "capabilities"
    - path: "tests/harness/test_capabilities_cli.py"
      provides: "CLI output + JSON-shape assertions"
      contains: "def test_"
  key_links:
    - from: "capabilities list/inspect"
      to: "make_toolset / ToolEntry.capability_dict"
      via: "build registry then render"
      pattern: "make_toolset"
    - from: "capabilities_group"
      to: "AGENT_COMMANDS"
      via: "registered into the main click group"
      pattern: "capabilities_group"
---

<objective>
Add `voss capabilities list` and `voss capabilities inspect <name>` (CAP-04/05, D-04) as a new click group, JSON-first with a grouped human render. `list` = compact names grouped by group; `inspect` = full normalized detail for one capability.

Purpose: Makes the capability registry discoverable and inspectable by agents and operators — the acceptance criterion "agent can list and inspect available capabilities."
Output: A `capabilities` command group registered in the CLI, plus CLI tests.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V1-capability-surface-hardening/V1-CONTEXT.md

<interfaces>
<!-- Existing `voss tools` command pattern to mirror: voss/harness/cli.py L2863-2885 (tools_cmd) -->
<!-- Command registration: AGENT_COMMANDS tuple at cli.py L3667-3699; register() adds each to main group. -->
<!-- A group example: mcp_group = click.group("mcp") at cli.py L3237. -->
<!-- ToolEntry.capability_dict() (from V1-01) yields the normalized inspect payload. -->
<!-- make_toolset(cwd) builds the registry; tools_cmd calls it with no session_id. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: capabilities list + inspect commands</name>
  <files>voss/harness/cli.py, tests/harness/test_capabilities_cli.py</files>
  <read_first>
    - voss/harness/cli.py (L2863-2885 tools_cmd for the make_toolset/render pattern; L3237 mcp_group for click.group shape; L3667-3699 AGENT_COMMANDS + register)
    - voss/harness/tools.py (CAPABILITY_GROUPS + ToolEntry.capability_dict from V1-01)
    - .planning/phases/V1-capability-surface-hardening/V1-CONTEXT.md (D-04 output shape, JSON-first)
  </read_first>
  <behavior>
    - `voss capabilities list` prints one header per group (in the fixed CAPABILITY_GROUPS order) with that group's capability NAMES underneath; groups with no capabilities are omitted (or shown empty — pick + state in summary). No badges/columns (D-04).
    - `voss capabilities list --json` prints a JSON object mapping group -> sorted list of capability names.
    - `voss capabilities inspect <name>` prints the full normalized detail: description, input schema, output schema, mutability, network, group, scope_requirements, audit_behavior, is_stateful (i.e. capability_dict()).
    - `voss capabilities inspect <name> --json` prints capability_dict() as JSON.
    - `voss capabilities inspect <unknown>` exits non-zero with a clear `<error: unknown capability: NAME>` style message.
  </behavior>
  <action>
    Add a `capabilities_group = click.Group("capabilities")` (mirror `mcp_group`) near the other groups in cli.py. Add `@capabilities_group.command("list")` and `@capabilities_group.command("inspect")`, each with the `--cwd` option (default ".", `click.Path(file_okay=False)`) copied from tools_cmd, plus a `--json/--no-json` flag (default human render). Both build the registry via `make_toolset(cwd)` (no session_id, like tools_cmd). For `list`: group entries by `entry.group`, iterate CAPABILITY_GROUPS for deterministic ordering, print `group:` header then sorted names indented; under `--json` emit `json.dumps({group: sorted(names)})`. For `inspect`: look up the name in the registry; if absent, `click.echo("<error: unknown capability: NAME>", err=True)` then `raise click.exceptions.Exit(1)`; else render `entry.capability_dict()` — human render as aligned `field: value` lines, `--json` as `json.dumps(capability_dict(), indent=2, default=str)`. Register `capabilities_group` into the `AGENT_COMMANDS` tuple at L3667. Write tests/harness/test_capabilities_cli.py using `click.testing.CliRunner`: invoke list (assert exit 0 + every present group header appears + a known name like `fs_write` listed); invoke `list --json` (assert valid JSON dict, `fs` key contains `fs_write`); invoke `inspect fs_write --json` (assert is_mutating True, group "fs", has input_schema + audit_behavior keys); invoke `inspect bogus` (assert non-zero exit).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_capabilities_cli.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `voss capabilities list` exits 0 and prints group headers drawn only from the nine groups (fs git test shell net code memory review mcp)
    - `voss capabilities list --json` emits a JSON object whose keys ⊆ the nine groups and whose `fs` list contains `fs_write`
    - `voss capabilities inspect fs_write` shows mutability=true, group=fs, scope_requirements, audit behavior, and input/output schema
    - `voss capabilities inspect <unknown>` exits non-zero
    - `pytest tests/harness/test_capabilities_cli.py` exits 0
  </acceptance_criteria>
  <done>capabilities list/inspect implemented JSON-first with grouped human render, unknown-name errors non-zero, group registered into the CLI, CLI tests green.</done>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_capabilities_cli.py -q` exits 0
- `.venv/bin/python -m voss.harness capabilities list` exits 0 and shows grouped names
- `.venv/bin/python -m voss.harness capabilities inspect fs_write --json` exits 0 and is valid JSON
</verification>

<success_criteria>
- `voss capabilities list` (compact grouped) + `--json` both work
- `voss capabilities inspect <name>` (full detail) + `--json` both work; unknown name errors
- Commands registered and reachable from the main CLI group
</success_criteria>

<output>
Create `.planning/phases/V1-capability-surface-hardening/V1-02-SUMMARY.md` when done
</output>
