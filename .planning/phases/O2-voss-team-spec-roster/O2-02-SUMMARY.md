---
phase: O2-voss-team-spec-roster
plan: 02
status: complete
completed_at: 2026-05-19
commits:
  - e5e8c6f — feat(O2-02): extend SubagentSpec with team role fields (Task 1)
  - b7815a2 — feat(O2-02): compile_team and scope containment (Task 2)
  - c50a3e3 — test(O2-02): team scope invariant and immutability gates (Task 3)
depends_on: [O2-01]
requirements: [OTEAM-02, OTEAM-03, OTEAM-05, OTEAM-06]
---

# O2-02 Summary — `compile_team` + enriched `SubagentRegistry`

## Objective

Semantic compile step: `TeamDecl` → frozen `TeamConfig` + `SubagentRegistry` with per-role `SubagentSpec` fields. **No** `PermissionGate` derivation (O2-03), **no** CLI wiring (O5).

## Commits

| Commit | Task |
|--------|------|
| `e5e8c6f` | `SubagentSpec` + 6 back-compat tests |
| `b7815a2` | `compile_team`, scope containment, 10 compile tests |
| `c50a3e3` | 7 scope-invariant + 8 immutability tests |

## API surface (for O2-03 / O5)

```python
def compile_team(decl: TeamDecl) -> tuple[TeamConfig, SubagentRegistry]
def subagent_spec_from_role(role_name: str, kvs: Mapping[str, object], ceiling: TeamCeiling) -> SubagentSpec
def subagent_spec_from_agent(agent_decl: TeamAgentDecl, ceiling: TeamCeiling) -> SubagentSpec
DEFAULT_ROSTER: tuple[str, ...]  # backend, frontend, ui, ai
default_team_role_defaults(role_name: str) -> tuple[str, str]
```

Optional hand-off type: `TeamRunContext(team_config, registry, base_gate)` — dataclass shell only.

## Open questions resolved

| ID | Choice | Notes |
|----|--------|-------|
| **OQ-02-A** | **Open roster** | Custom role names compile with fallback description/prompt; four defaults in `DEFAULT_ROSTER` |
| **OQ-02-B** | **Per-role budget cap** | `role.budget ≤ ceiling.budget_tokens` at compile time |
| **OQ-02-C** | **Prefix-to-first-wildcard** | `TeamRoleScope.is_contained_in`; docstring documents `**` limitations |

## Strawman compile facts

- `policy.p`: `Identifier(name="risk_tiered")` — not plain string `"risk_tiered"`
- `ceiling.budget_tokens == 200_000`, `latency_seconds == 1800`
- Registry ids: `ai`, `backend`, `em`, `frontend`, `ui`
- `registry.get("ai").net is True`; engineers `net=False`
- EM `scope: "all"` → compiles to ceiling scope (`src/**`)

## Verification

```
pytest tests/voss/ tests/harness/test_subagent_spec_extensions.py \
     tests/harness/test_subagent_recursion.py tests/parser/test_team_grammar.py -q
```

**46 passed** (10 compile + 7 scope + 8 immutability + 6 spec-ext + 12 grammar + 3 recursion).

## Untouched (per plan)

`cli.py`, `multiagent.py`, `permissions.py`, `tools.py` — no diff.

## Next

**O2-03-PLAN.md** — per-role `PermissionGate` from compiled specs + `scoped_gate` integration.
