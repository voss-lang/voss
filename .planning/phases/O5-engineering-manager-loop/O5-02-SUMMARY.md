---
phase: O5-engineering-manager-loop
plan: 02
status: complete
completed_at: 2026-05-20
commits: []
depends_on: [O5-01]
requirements: [OEM-02, OEM-06, OEM-07, OEM-08]
---

# O5-02 Summary — EMBoardHandle (Wave 2)

## Objective

Land EMBoardHandle -- the cage-bounded facade that is the EM's ONLY board API. Exposes 11 legal verbs (snapshot, all_cards_terminal, create_ticket, set_ac, set_dod, dispatch_card, kill_card, rescope_card, tick, force_block_all, finalize_run) and refuses everything else by omission. BoardProtocol typed against O3-SPEC so W2 runs without importing from `voss.harness.board.*`.

## Files changed

- `voss/harness/em/protocols.py` -- **new** (33 lines): `Column` Literal, `TERMINAL_COLUMNS` frozenset, `CardProtocol` and `BoardProtocol` as `@runtime_checkable` Protocols typed against O3-SPEC.
- `voss/harness/em/handle.py` -- **new** (361 lines): `BoardSnapshot` frozen-slots dataclass, `_NodeAudit` internal side-table dataclass, `EMBoardHandle` class with all 11 legal verbs.
- `voss/harness/em/__init__.py` -- extended: re-exports `EMBoardHandle`, `BoardSnapshot`, `BoardProtocol`, `CardProtocol`, `Column`.
- `tests/harness/em/conftest.py` -- **new**: shared fixtures (StubBoard, StubCard, stub_recorder, tiny_team_config, base_gate, make_handle factory).
- `tests/harness/em/test_em_handle.py` -- **new** (8 tests): happy-path create_ticket, set_ac, set_dod, snapshot immutability, all_cards_terminal, tick delegation.
- `tests/harness/em/test_em_handle_cage.py` -- **new** (8 tests): cage invariants 1-5 (introspection, non-roster dispatch, budget absence, kill-Done refusal, rescope-Done refusal, scope-containment).
- `tests/harness/em/test_em_handle_dispatch.py` -- **new** (6 tests): RoutingRationale emission before subagent, gate_for_role plumbing, filter_toolset_for_role plumbing, no SubagentSpec construction, no SubagentRegistry.register, kill finalize_node(exit_reason="killed").

## Test counts

| File | Tests |
|------|-------|
| `test_em_handle.py` | 8 |
| `test_em_handle_cage.py` | 8 |
| `test_em_handle_dispatch.py` | 6 |
| `conftest.py` | (fixtures) |
| **Total (new)** | **22** |

## Key facts

- **Cage by omission:** `dir(handle)` filtered to non-underscore names contains NONE of {set_ceiling, set_p, set_budget, extend_budget, register_role, register_agent, mutate_team_config}. Introspection test enforces this.
- **7 forbidden verbs absent:** The handle simply never defines these methods. No runtime check needed -- the method doesn't exist.
- **_NodeAudit side-table:** Audit records (RoutingRationale, KillRecord, RescopeRecord) live in `handle._node_audit: dict[node_id, _NodeAudit]`, NOT on SessionTreeNode directly. This preserves O1 SPEC-5's strict-additive field invariant.
- **kill_card flow:** Appends KillRecord to side-table, then calls `finalize_node(node, exit_reason="killed", cwd=...)`. The node JSON stays on disk (L-04).
- **rescope_card flow:** Kills predecessor (KillRecord with successor_card_id), allocates successor, emits RescopeRecord with predecessor_card_id. Bidirectional pointers confirmed by test.
- **dispatch_card flow:** Emits RoutingRationale BEFORE subagent fires (audit-survives-crash invariant). Derives per-role gate via `gate_for_role(spec, base_gate)` and per-role toolset via `filter_toolset_for_role(spec, base_toolset)` -- handle never widens.
- **subagent_runner injection:** Constructor accepts `subagent_runner: Callable` for test substitution. W4 loop injects the real `run_subagent`.

## Audit-On-Side-Table Decision

RESEARCH Q3 assumed audit attributes (routing_rationales, kill_record, rescope_record) would live directly on SessionTreeNode. The execution chose an in-memory side-table (`_node_audit`) instead. Rationale: extending SessionTreeNode would violate O1 SPEC-5 (strict-additive field blast radius) and couple the EM facade to the O1 schema. The side-table lets W5 integration confirm the on-disk persistence shape without modifying O1's contract.

## Deviations from plan

- **subagent_runner dispatch is placeholder:** The `asyncio.ensure_future(...)` call in `dispatch_card` is wrapped in `if False else None` -- effectively a no-op. Real dispatch is deferred to W4 loop integration.
- **finalize_run does not persist RunFinal to disk:** W2 returns the RunFinal in-memory; on-disk persistence (`_run_final.json`) deferred to W5 integration.

## Unchanged

- `voss/harness/session_tree.py` -- no diff; read-only via `SessionTreeManager` and `finalize_node`.
- `voss/harness/team.py` -- no diff; read-only via `gate_for_role` + `filter_toolset_for_role`.
- W1 tests -- all still green.

## Next

W3 lands the LLM schema (EMPlanResponse pydantic v2) + em_plan wrapper + DeterministicEMStub.
