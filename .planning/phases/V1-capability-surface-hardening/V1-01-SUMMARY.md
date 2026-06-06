---
phase: V1-capability-surface-hardening
plan: 01
subsystem: capabilities
tags: [toolentry, capability-metadata, scope, audit, tool-registry]

requires:
  - phase: V0
    provides: "canonical PRD primitives (CAP-01/02/03/06 rows) defining the capability schema"
provides:
  - "Extended frozen ToolEntry: required group + scope_requirements/audit_behavior/is_stateful/output_schema"
  - "CAPABILITY_GROUPS — the nine D-05 groups, enforced via __post_init__"
  - "capability_dict() — normalized CAP-02 view for downstream CLI/MCP/recorder"
  - "Every ToolEntry construction hand-tagged: native registry, memory, subagent, task, multiagent, MCP"
affects: [V1-02+, CLI capability surfacing, MCP unification, recorder]

tech-stack:
  added: []
  patterns:
    - "Capability metadata is explicit per-entry data at registration (D-01) — no name-prefix derivation"
    - "Required dataclass field placed before defaulted fields so untagged sites TypeError loudly"

key-files:
  created:
    - tests/harness/test_capability_metadata.py
  modified:
    - voss/harness/tools.py
    - voss/harness/subagents.py
    - voss/harness/multiagent.py
    - voss/harness/mcp/registry.py

key-decisions:
  - "group is REQUIRED (no default), placed after is_mutating + before is_network so the frozen dataclass allows it and untagged construction TypeErrors instead of mislabeling"
  - "scope_requirements set to (group,) uniformly — coarse group-level buckets (D-03), no per-path/host"
  - "subagent/task/spawn/steer/status/gather → group=review (no tenth orchestration bucket per D-05); the family delegates work whose result the parent reviews/gathers, same bucket as record_run"
  - "record_run audit_behavior=metadata_only — run artifacts can be large; keep the full blob out of the audit log"
  - "is_stateful=True only for handle/job-referencing tools: shell_run_background/monitor/signal, fs_watch/poll, subagent_steer/status/gather"

patterns-established:
  - "ToolEntry.capability_dict() is the single normalized capability view consumers build on"

requirements-completed: [VCAP-01, VCAP-02, VCAP-03, VCAP-06]

duration: 25min
completed: 2026-06-06
---

# Phase V1-01: Capability Surface Hardening — ToolEntry Metadata Summary

**`ToolEntry` now carries explicit, validated capability metadata (group / scope / audit / stateful) at every construction site across the harness, making mutability+group+scope auditable data at registration rather than name-pattern guesswork.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2 / 2 (TDD: RED test first, then implementation)
- **Files modified:** 4 source + 1 test created (+ 7 test files retagged, see deviation)

## Accomplishments

### Task 1 — Extended ToolEntry schema + nine-group constant
- Added module-level `CAPABILITY_GROUPS = (fs, git, test, shell, net, code, memory, review, mcp)` + `_AUDIT_BEHAVIORS`.
- Extended the frozen `ToolEntry` in place (not replaced): new **required** `group: str` (after `is_mutating`, before defaulted fields), plus defaulted `scope_requirements: tuple = ()`, `audit_behavior: str = "full"`, `is_stateful: bool = False`, `output_schema: dict|None = None`. `descriptor`/`is_mutating`/`is_network` semantics unchanged.
- `__post_init__` validates group ∈ CAPABILITY_GROUPS, each scope ∈ CAPABILITY_GROUPS, audit_behavior ∈ allowed → raises ValueError.
- `capability_dict()` returns the 10-key CAP-02 view (name, description, input_schema=parameters, output_schema, is_mutating, is_network, group, scope_requirements as list, audit_behavior, is_stateful).
- RED test written first (groups exact-nine, unknown-group ValueError, missing-group TypeError, bad-scope/audit ValueError, defaults, capability_dict shape).

### Task 2 — Hand-tagged every ToolEntry construction
- **tools.py native registry** (all ~26 entries) + the four `code_*` + the two memory tools.
- **subagents.py**: `subagent_run`, `task` → group=review.
- **multiagent.py**: `subagent_spawn/steer/status/gather` → group=review (steer/status/gather is_stateful=True).
- **mcp/registry.py** (5th site, not in plan's file list — see deviation): MCP entries → group=mcp.
- Group/scope/stateful per the plan's behavior table; `is_mutating`/`is_network` preserved verbatim at every site.
- Added registry-wide completeness test (make_toolset) + attach-helper test (memory + subagent + multiagent against stubs) — the latter is what catches out-of-block untagged regressions.

## Verification

- Plan verify set green: `test_capability_metadata.py` + `test_tools.py` + `test_tools_config_cmds.py`.
- `voss tools --cwd .` exits 0 (make_toolset builds; required group supplied everywhere).
- Source acceptance: `CAPABILITY_GROUPS` exact nine; ToolEntry declares all four new fields; `group="fs"` count = 9; memory→memory, subagent family→review tagged; bogus group → ValueError; no group → TypeError.
- Broad harness regression: the only failures are 11 `AuthenticationError: 401` (no API key in this env) + the pre-existing EXIT_REASONS-frozenset drift + streaming/env tests — **zero failures from this change** (no ToolEntry/group/TypeError/ValueError failures in the run).

## Deviations

- **Tagged a 5th construction site not in the plan's `files_modified`: `voss/harness/mcp/registry.py`.** The required `group` field would TypeError every live MCP session otherwise; tagged group=mcp/scope=(mcp,) for correctness (matches D-05's mcp group).
- **Retagged stub `ToolEntry(...)` constructions in 6 test files** (test_t1_acceptance, test_agent_loop, test_partition_scheduler, test_permissions, eval/test_golden_2_one_shot, perf/test_parallel_read_speedup) with `group="fs"`. Making `group` required necessarily breaks every untagged construction, including test helpers; these are mechanical neutral tags that do not change those tests' is_mutating-based assertions.
- **scope_requirements = (group,) uniformly** including git/test/code/mcp (the plan enumerated only fs/shell/net/memory/review as examples); uniform coarse bucket = each tool's own group, consistent with D-03 and keeps scope filtering meaningful.
