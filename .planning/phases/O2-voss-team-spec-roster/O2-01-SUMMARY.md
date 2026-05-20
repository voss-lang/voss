---
phase: O2-voss-team-spec-roster
plan: 01
status: complete
completed_at: 2026-05-19
commits:
  - 7c95828 — feat(O2-01): add team_decl grammar productions (Task 1)
  - 2dde50b — feat: team AST nodes + harness types (partial, pre-Task-2 message)
  - 2902672 — feat(O2-01): team AST, frozen value objects, parser transformer (Task 2)
  - 5513eff — test(O2-01): team grammar acceptance suite + strawman fixture (Task 3)
requirements: [OTEAM-01, OTEAM-04, OTEAM-08]
---

# O2-01 Summary — `team{}` grammar + AST + frozen value objects (parse-only)

## Objective

Pure **parse / shape** plan: `team { … }` in `.voss` grammar → `TeamDecl` AST + frozen runtime value-object shells in `voss/harness/team.py`. **No** `compile_team()`, **no** `SubagentSpec` changes (O2-02 / O2-03).

## Commits (execution order)

| Commit | Task | What |
|--------|------|------|
| `7c95828` | 1 | `team_decl` + sub-productions in `grammar.lark`; `TOKEN_BUDGET` accepts `k`/`m` suffix |
| `2902672` | 2 | Parser transformer pipeline; kv newline/comma flexibility; `_resolve_token_budget` |
| `5513eff` | 3 | `team_strawman.voss` + 12 acceptance tests |

(Intermediate `2dde50b` on branch also introduced `ast_nodes` / `team.py` types.)

## Files

| File | Role |
|------|------|
| `voss/grammar.lark` | `team_decl`, ceiling/roster/board/ritual productions |
| `voss/ast_nodes.py` | `TeamDecl`, `CeilingDecl`, `TeamAgentDecl`, `RosterDecl`, `RosterRoleDecl`, `BoardDecl`, `RitualDecl` (frozen) |
| `voss/parser.py` | Transformer methods; missing/duplicate ceiling → `VossParseError` |
| `voss/harness/team.py` | `TeamConfig`, `TeamCeiling`, `TeamPolicy`, `TeamRoleScope`, `BoardSpec`, `RitualSpec`, `VossTeamConfigError` (frozen shells) |
| `tests/parser/examples/team_strawman.voss` | Strawman fixture |
| `tests/parser/test_team_grammar.py` | 12 tests |

**Untouched (per plan):** `subagents.py`, `permissions.py`, `skill/scope.py`, `tools.py`.

## Verification

```
.venv/bin/python -m pytest tests/parser/test_team_grammar.py -q   # 12 passed
.venv/bin/python -m pytest tests/parser/ -x -q                    # full suite green (skips unchanged)
```

Strawman: `TeamDecl(name="Engineering")` with agents, rosters, board, rituals.

## Open questions resolved

### OQ-01-A — scope literal form

**Chosen:** Quoted strings (`scope: "src/**"`) + grammar allows `STRING | list_lit` for ceiling/role values. No bare `GLOB` terminal.

### OQ-01-B — `team_agent` vs `agent_decl`

**Chosen:** Keep `agent` keyword inside `team_body`; Earley disambiguates via `(` after IDENT for top-level `agent_decl`. **`test_team_agent_no_paren_collision` passes** — no rename to `role`.

**Note:** `team_body` items are separated by `_NL+`; multiline team blocks need newlines between `ceiling`, `agent`, `roster`, etc.

## Strawman deviations (documented)

Fixture path: `tests/parser/examples/team_strawman.voss`

| ORCHESTRATION-PLAN | O2-01 fixture |
|--------------------|---------------|
| `gate Done(code) { tests: pass, … }` | `gate Done -> code { "pass_tests", … }` — grammar uses `gate IDENT -> target { expr, … }` |
| `latency: 30m` | `latency: 1800s` — `30m` not in `budget_literal` today |
| `gather(session_tree)` | `gather: "session_tree"` |
| `//` comments | `#` comments (Voss `COMMENT` terminal) |

Board/ritual semantics are **opaque** (OTEAM-08): stored on AST, not interpreted.

## Transformer helpers for O2-02

- `_resolve_token_budget(s: str) -> int` in `voss/parser.py` (`200k tokens` → `200_000`)
- `TeamRoleScope.is_contained_in` → `NotImplementedError` until O2-02 compile

## Next

**O2-02-PLAN.md** — `compile_team(TeamDecl) -> (TeamConfig, SubagentRegistry)` + scope containment validation.
