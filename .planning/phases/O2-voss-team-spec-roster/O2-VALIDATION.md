---
phase: O2
slug: voss-team-spec-roster
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-19
completed: 2026-05-20
---

# Phase O2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest tests/parser/test_team_grammar.py tests/voss/ tests/harness/test_subagent_spec_extensions.py -x -q --tb=short` |
| **Full suite command** | `.venv/bin/python -m pytest tests/parser/test_team_grammar.py tests/voss/ tests/harness/test_subagent_spec_extensions.py tests/harness/test_team_gate_compile.py tests/harness/test_team_tool_filter.py tests/harness/test_team_per_role_net.py tests/harness/test_allow_net.py -v --tb=long` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick suite
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Requirement → Plan Coverage Matrix

| Requirement ID | Description | Plan(s) | Wave | Verify Command | Status |
|----------------|-------------|---------|------|----------------|--------|
| OTEAM-01 | `.voss` parser accepts `team <NAME> { … }` with ceiling/p/agent/roster/board/ritual sub-blocks; malformed → `VossParseError` with location | O2-01 | 1 | `.venv/bin/python -m pytest tests/parser/test_team_grammar.py -x -q` | ✅ green |
| OTEAM-02 | `SubagentSpec` extended with `model`/`mode`/`scope`/`budget`/`tools` (Optional); existing callers keep working with defaults | O2-02 | 2 | `.venv/bin/python -m pytest tests/harness/test_subagent_spec_extensions.py -x -q` | ✅ green |
| OTEAM-03 | Default specialist roster (`backend`/`frontend`/`ui`/`ai`); AI role declares `net` in tools; non-AI roles default to no `net` | O2-02, O2-03 | 2, 3 | `.venv/bin/python -m pytest tests/harness/test_team_per_role_net.py tests/voss/test_team_compile.py -x -q` | ✅ green |
| OTEAM-04 | `ceiling`/`p` parsed into frozen `TeamCeiling`/`TeamPolicy`; no mutation API — EM cannot rewrite at runtime | O2-01, O2-02 | 1, 2 | `.venv/bin/python -m pytest tests/voss/test_team_immutability.py tests/parser/test_team_grammar.py -k frozen -x -q` | ✅ green |
| OTEAM-05 | Compile-time `role.scope ⊆ ceiling.scope` validation; violation raises `VossTeamConfigError` citing both globs | O2-02 | 2 | `.venv/bin/python -m pytest tests/voss/test_team_scope_invariant.py -x -q` | ✅ green |
| OTEAM-06 | Dispatch refuses unknown `agent_id` with existing `<error: unknown subagent {id!r}>` envelope; enriched registry preserves this | O2-02 | 2 | `.venv/bin/python -m pytest tests/voss/test_team_compile.py -k "refuses_unknown" -x -q` | ✅ green |
| OTEAM-07 | `gate_for_role(spec, base_gate)` caps mode (never expands), reuses `_min_mode` from `skill/scope.py`, preserves project policy | O2-03 | 3 | `.venv/bin/python -m pytest tests/harness/test_team_gate_compile.py -x -q` | ✅ green |
| OTEAM-08 | `board { … }` and `ritual <NAME> { … }` parse to opaque `BoardSpec`/`RitualSpec` data — not silently dropped, not interpreted | O2-01 | 1 | `.venv/bin/python -m pytest tests/parser/test_team_grammar.py -k "board_round_trips or ritual_round_trips" -x -q` | ✅ green |

Every OTEAM-01..OTEAM-08 requirement appears in >= 1 plan. Reverse check: every plan declares its OTEAM coverage in `requirements:` frontmatter.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| O2-01-01 | O2-01 | 1 | OTEAM-01, OTEAM-08 | tdd | `.venv/bin/python -c "from voss.parser import _PARSER; _PARSER.parse('team Eng {\n  ceiling {\n    budget: 1000 tokens\n  }\n}\n'); print('OK')"` | ✅ green |
| O2-01-02 | O2-01 | 1 | OTEAM-01, OTEAM-04 | tdd | `.venv/bin/python -c "from voss.ast_nodes import TeamDecl, CeilingDecl; from voss.harness.team import TeamConfig, TeamCeiling; print('OK')"` | ✅ green |
| O2-01-03 | O2-01 | 1 | OTEAM-01, OTEAM-04, OTEAM-08 | tdd | `.venv/bin/python -m pytest tests/parser/test_team_grammar.py -v` | ✅ green |
| O2-02-01 | O2-02 | 2 | OTEAM-02 | tdd | `.venv/bin/python -m pytest tests/harness/test_subagent_spec_extensions.py -v` | ✅ green |
| O2-02-02 | O2-02 | 2 | OTEAM-02, OTEAM-03, OTEAM-05, OTEAM-06 | tdd | `.venv/bin/python -m pytest tests/voss/test_team_compile.py -v` | ✅ green |
| O2-02-03 | O2-02 | 2 | OTEAM-04, OTEAM-05 | tdd | `.venv/bin/python -m pytest tests/voss/test_team_scope_invariant.py tests/voss/test_team_immutability.py -v` | ✅ green |
| O2-03-01 | O2-03 | 3 | OTEAM-07 | tdd | `.venv/bin/python -m pytest tests/harness/test_allow_net.py -v` | ✅ green |
| O2-03-02 | O2-03 | 3 | OTEAM-07, OTEAM-03 | tdd | `.venv/bin/python -m pytest tests/harness/test_team_gate_compile.py tests/harness/test_team_tool_filter.py -v` | ✅ green |
| O2-03-03 | O2-03 | 3 | OTEAM-03 | integration | `.venv/bin/python -m pytest tests/harness/test_team_per_role_net.py -v` | ✅ green |

---

## Wave Structure

| Wave | Plans | Autonomous | Files Modified |
|------|-------|------------|----------------|
| 1 | O2-01 | yes | voss/grammar.lark, voss/ast_nodes.py, voss/parser.py, voss/harness/team.py (new); tests/parser/ |
| 2 | O2-02 | yes | voss/harness/subagents.py, voss/harness/team.py; tests/harness/, tests/voss/ |
| 3 | O2-03 | yes | voss/harness/permissions.py, voss/harness/team.py, voss/harness/tools.py; tests/harness/ |

---

## Wave 0 Requirements

- [x] Existing parser tests pass (regression gate for grammar additions)
- [x] `SubagentSpec` 3-arg construction still works (back-compat baseline)
- [x] `default_subagent_registry()` returns `explorer`/`worker`/`reviewer` with default new fields

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (none) | — | O2 is fully automatable | — |

---

## Test Summary

| Source | Test Count |
|--------|-----------|
| `tests/parser/test_team_grammar.py` | 12 |
| `tests/harness/test_subagent_spec_extensions.py` | 6 |
| `tests/voss/test_team_compile.py` | 10 |
| `tests/voss/test_team_scope_invariant.py` | 7 |
| `tests/voss/test_team_immutability.py` | 8 |
| `tests/harness/test_team_gate_compile.py` | 8+ |
| `tests/harness/test_team_tool_filter.py` | 7+ |
| `tests/harness/test_team_per_role_net.py` | 8 |
| `tests/harness/test_allow_net.py` (additive) | 4 new |
| **Total O2 tests** | **88** (per O2-03-SUMMARY final count) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter
- [x] Every OTEAM-01..OTEAM-08 appears in >= 1 plan
- [x] Every plan declares OTEAM coverage in `requirements:` frontmatter

**Approval:** green 2026-05-20 — 88 O2 tests pass. All OTEAM-01..OTEAM-08 green. Phase complete.
