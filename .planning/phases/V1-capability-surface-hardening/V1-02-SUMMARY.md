---
phase: V1-capability-surface-hardening
plan: 02
subsystem: cli
tags: [capabilities, cli, click, discovery, json]

requires:
  - phase: V1-01
    provides: "ToolEntry.group + capability_dict() normalized view; CAPABILITY_GROUPS ordering"
provides:
  - "voss capabilities list — names grouped by group (human + --json)"
  - "voss capabilities inspect <name> — full normalized detail (human + --json); unknown errors non-zero"
affects: [agents/operators discovering the capability registry, V1-03+ consumers]

tech-stack:
  added: []
  patterns:
    - "JSON-first CLI command mirroring mcp_group; build registry via make_toolset then render"

key-files:
  created:
    - tests/harness/test_capabilities_cli.py
  modified:
    - voss/harness/cli.py

key-decisions:
  - "Empty groups omitted from `list` output (only groups with ≥1 capability shown)"
  - "list iterates CAPABILITY_GROUPS for deterministic ordering; names sorted within each group"
  - "inspect renders capability_dict() field:value lines (human) / json.dumps(indent=2, default=str) (--json)"
  - "unknown capability → stderr `<error: unknown capability: NAME>` + Exit(1)"

patterns-established:
  - "capabilities_group registered into AGENT_COMMANDS like every other agent command"

requirements-completed: [VCAP-04, VCAP-05]

duration: 10min
completed: 2026-06-06
---

# Phase V1-02: Capability Surface Hardening — capabilities CLI Summary

**`voss capabilities list` and `voss capabilities inspect <name>` make the V1-01 capability registry discoverable and inspectable by agents and operators, JSON-first with a grouped human render.**

## Performance

- **Duration:** ~10 min
- **Tasks:** 1 / 1 (TDD)
- **Files modified:** 1 source + 1 test created

## Accomplishments

- Added `capabilities_group` (click.Group) with two subcommands, mirroring `mcp_group`, both taking `--cwd` + `--json`:
  - **list** — groups entries by `entry.group`, iterates `CAPABILITY_GROUPS` for stable order, prints `group:` header + sorted indented names; `--json` emits `{group: sorted(names)}` for groups present.
  - **inspect** — looks up the name in `make_toolset(cwd)`; unknown → `<error: unknown capability: NAME>` on stderr + `Exit(1)`; else renders `entry.capability_dict()` as aligned `field : value` lines, or `--json` as pretty JSON.
- Imported `CAPABILITY_GROUPS` into cli; registered `capabilities_group` into `AGENT_COMMANDS` so it attaches to the main CLI group.
- TDD test (`test_capabilities_cli.py`): list human + JSON shape, inspect JSON + human, unknown-errors-nonzero, registered-in-AGENT_COMMANDS.

## Verification

- `pytest tests/harness/test_capabilities_cli.py` → 6/6 green.
- `voss capabilities list --cwd .` → exit 0, grouped output (fs/git/test/shell/... headers, names indented).
- `voss capabilities inspect fs_write --cwd . --json` → valid JSON, group=fs, is_mutating=True.
- `voss capabilities inspect nope` → exit 1.

## Notes

- `make_toolset(cwd)` with no `net` session means MCP tools are not merged into `list`/`inspect` output (consistent with `tools_cmd`); the `mcp` group simply won't appear unless MCP is active. Acceptable for a static capability listing.
