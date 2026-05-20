---
phase: O2-voss-team-spec-roster
plan: 03
status: complete
completed_at: 2026-05-19
commits:
  - e94a641 — feat(O2-03): per-gate allow_net override on PermissionGate (Task 1)
  - d1c4f57 — feat(O2-03): gate_for_role and filter_toolset_for_role (Task 2)
  - e812318 — test(O2-03): per-role net cage integration tests (Task 3)
depends_on: [O2-01, O2-02]
requirements: [OTEAM-03, OTEAM-07]
---

# O2-03 Summary — Per-role gate + toolset filter

## Objective

Close the per-role authorization loop: enriched `SubagentSpec` + base `PermissionGate` → role-specific gate and filtered toolset. **Not** wired into `run_subagent` yet (O5).

## Commits

| Commit | Task |
|--------|------|
| `e94a641` | `PermissionGate.allow_net` + 4 additive `test_allow_net` tests |
| `d1c4f57` | `gate_for_role`, `filter_toolset_for_role`, `TOOL_GROUP_ALIASES` |
| `e812318` | 8 strawman integration tests (`test_team_per_role_net`) |

## API

```python
def gate_for_role(spec: SubagentSpec, base_gate: PermissionGate) -> PermissionGate
def filter_toolset_for_role(spec: SubagentSpec, base_toolset: Mapping[str, ToolEntry]) -> dict[str, ToolEntry]
```

`TOOL_GROUP_ALIASES`: `fs`, `test`, `shell`, `net`, `git` → concrete tool names; exact names also accepted.

Network tools filtered: **`web_fetch`**, **`web_search`** (only when `"net"` in expanded `spec.tools`).

## Open questions resolved

| ID | Choice |
|----|--------|
| **OQ-03-A** | Hybrid alias table + exact tool names |
| **OQ-03-B** | Per-gate `allow_net` field on `PermissionGate` (`None` = defer to process config) |

Compiled roles: `allow_net=True if spec.net else False` (never `None`).

## Cage proof (integration)

| Scenario | AI role | Backend role |
|----------|---------|--------------|
| Process `allow_net=True` | `web_fetch` allowed | denied (per-gate override) |
| Process `allow_net=False` | `web_fetch` allowed | denied |

Project-policy deny still wins over `allow_net=True`.

## Deferred to O5 (T-O2-03-03)

EM tool surface must **not** expose arbitrary `PermissionGate(...)` construction. Dispatch should use `subagent_run(agent_id, task)` with harness-owned `gate_for_role` — document for O5 SPEC.

## Verification

```
pytest tests/harness/test_allow_net.py \
     tests/harness/test_team_gate_compile.py \
     tests/harness/test_team_tool_filter.py \
     tests/harness/test_team_per_role_net.py \
     tests/harness/test_subagent_spec_extensions.py \
     tests/voss/ tests/parser/test_team_grammar.py \
     tests/harness/test_subagent_recursion.py -q
```

**88 passed** (10 allow_net + 16 gate + 8 tool-filter + 8 per-role-net + 6 spec-ext + 25 voss + 12 grammar + 3 recursion).

## Phase O2 complete

| Plan | Deliverable |
|------|-------------|
| O2-01 | `team{}` grammar + AST |
| O2-02 | `compile_team` + `SubagentSpec` enrichment |
| O2-03 | `gate_for_role` + `filter_toolset_for_role` |

**Next:** O3 board state machine (or O5 EM wiring when scheduled).

## Untouched

`subagents.py`, `cli.py`, `multiagent.py` — no diff from O2-03.
