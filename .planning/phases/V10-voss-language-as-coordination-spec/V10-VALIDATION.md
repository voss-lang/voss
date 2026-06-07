---
phase: V10
slug: voss-language-as-coordination-spec
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-07
updated: 2026-06-07
---

# Phase V10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml (existing pytest settings) |
| **Quick run command** | `.venv/bin/python -m pytest tests/parser/test_team_grammar.py tests/voss/test_team_principles_block.py tests/voss/test_team_gate_block.py tests/voss/test_team_memory_block.py tests/voss/test_team_diagnostic_shape.py -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/parser/ tests/voss/ tests/harness/test_team_check_cli.py tests/harness/test_principles_config.py tests/harness/test_voss_loop_parity.py tests/codegen/test_examples.py tests/harness/test_e2e_team_run.py -q` |
| **Estimated runtime** | ~30–90s (team/parser/voss suites are fast; e2e stub run is in-memory) |

> NOTE: use `.venv/bin/python` — bare `python3` lacks deps and cannot run the suite. The e2e test requires `VOSS_HERMETIC=1` to force the stub provider.

---

## Sampling Rate

- **After every task commit:** Run quick run command (parser + voss compile tests).
- **After every plan wave:** Run full suite command.
- **Before `/gsd-verify-work`:** Full suite green + `git diff -- voss/harness/session.py voss_runtime/budget.py` empty of field changes + `git diff -- voss/grammar.lark` coordination-only.
- **Max feedback latency:** < 90s.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| V10-01 T1 | 01 | 1 | VLANG-01a/01b/01c | T-V10-01-02 | parser rejects malformed blocks | RED scaffold | `.venv/bin/python -m pytest tests/parser/test_team_grammar.py -k "principles_block_parses or team_with_principles_block or gate_block_parses or memory_block_parses" -q; test $? -ne 0` | ❌→✅(W0) | ⬜ pending |
| V10-01 T2 | 01 | 1 | VLANG-01a/01b/01c | T-V10-01-01 | tmp_path-only writes | RED scaffold | `.venv/bin/python -m pytest tests/voss/test_team_principles_block.py tests/voss/test_team_gate_block.py tests/voss/test_team_memory_block.py -q; test $? -ne 0` | ❌→✅(W0) | ⬜ pending |
| V10-01 T3 | 01 | 1 | VLANG-02/08 | T-V10-01-01 | e2e uses stub + tmp_path | RED scaffold | `.venv/bin/python -m pytest tests/voss/test_team_diagnostic_shape.py tests/voss/test_org_loop_examples.py tests/harness/test_e2e_team_run.py -q; test $? -ne 0` | ❌→✅(W0) | ⬜ pending |
| V10-02 T1 | 02 | 2 | VLANG-01a/01b/01c, GUARD | T-V10-02-01 | bounded grammar, no new recursion | unit/parser | `.venv/bin/python -c "from voss import parse; parse('principles { diff: \"x\" }\n','<t>'); parse('gate done {\n require tests_passed\n}\n','<t>'); parse('memory { decisions: \"d\" }\n','<t>'); print('PARSE_OK')"` | ✅ | ⬜ pending |
| V10-02 T2 | 02 | 2 | VLANG-01a/01b/01c | T-V10-02-02 | defaulted fields, back-compat | unit/ast | `.venv/bin/python -c "from voss.ast_nodes import PrinciplesBlockDecl,GateBlockDecl,MemoryBlockDecl,TeamDecl; print('NODES_OK')"` | ✅ | ⬜ pending |
| V10-02 T3 | 02 | 2 | VLANG-01a/01b/01c | T-V10-02-02 | duplicate-key VossParseError | unit/parser | `.venv/bin/python -m pytest tests/parser/test_team_grammar.py -k "principles_block_parses or team_with_principles_block or gate_block_parses or memory_block_parses" -q` | ✅(after) | ⬜ pending |
| V10-03 T1 | 03 | 3 | VLANG-01a/01b/01c | T-V10-03-02 | informational configs, no enforcement | unit/compile | `.venv/bin/python -c "from voss.harness.team import GateConfig,MemoryConfig,TeamConfig; print('CFG_OK')"` | ✅ | ⬜ pending |
| V10-03 T2 | 03 | 3 | VLANG-01a/01b/01c | T-V10-03-01/02/03 | reuse V2 merge; config-only paths | unit/compile | `.venv/bin/python -m pytest tests/voss/test_team_principles_block.py tests/voss/test_team_gate_block.py tests/voss/test_team_memory_block.py -q` | ✅(after) | ⬜ pending |
| V10-04 T1 | 04 | 4 | VLANG-02 | T-V10-04-01 | path is user's own input | unit | `.venv/bin/python -c "from voss.harness.team import VossTeamConfigError; print('DIAG_OK')"` | ✅ | ⬜ pending |
| V10-04 T2 | 04 | 4 | VLANG-02 | T-V10-04-02 | actionable construct + hint | unit/compile | `.venv/bin/python -m pytest tests/voss/test_team_diagnostic_shape.py -q` | ✅(after) | ⬜ pending |
| V10-05 T1 | 05 | 5 | VLANG-08, GUARD | T-V10-05-02 | coordination-only samples | smoke | `.venv/bin/python -m pytest tests/voss/test_org_loop_examples.py -q` | ✅(after) | ⬜ pending |
| V10-05 T2 | 05 | 5 | VLANG-08 | T-V10-05-01/03 | stub provider, bounded loop | integration | `VOSS_HERMETIC=1 .venv/bin/python -m pytest tests/harness/test_e2e_team_run.py -q` | ✅(after) | ⬜ pending |
| V10-05 T3 | 05 | 5 | VLANG-VERIFY, GUARD | T-V10-05-02 | frozen-schema + grammar diff guard | regression+guard | `.venv/bin/python -m pytest tests/harness/test_voss_loop_parity.py tests/codegen/test_examples.py tests/parser/test_team_grammar.py tests/voss/test_team_compile.py tests/voss/test_team_backcompat_regression.py -q` + `git diff -- voss/harness/session.py voss_runtime/budget.py` | ✅(after) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 (plan V10-01) creates ALL failing test scaffolds before any production code:

- [ ] `tests/parser/test_team_grammar.py` — add `test_principles_block_parses`, `test_team_with_principles_block`, `test_gate_block_parses`, `test_memory_block_parses` (VLANG-01a/01b/01c)
- [ ] `tests/voss/test_team_principles_block.py` — compile + block/yaml merge precedence (VLANG-01a)
- [ ] `tests/voss/test_team_gate_block.py` — `GateConfig` compile (VLANG-01b)
- [ ] `tests/voss/test_team_memory_block.py` — `MemoryConfig` compile + key defaults (VLANG-01c)
- [ ] `tests/voss/test_team_diagnostic_shape.py` — construct + file:line + fix_hint per error class (VLANG-02)
- [ ] `tests/voss/test_org_loop_examples.py` — `voss check` clean on the three samples (VLANG-08)
- [ ] `tests/harness/test_e2e_team_run.py` — `voss team run` completes on stub against `.voss/team.voss` (VLANG-08)

All scaffolds target the real planned surface (no fictional API; no xfail masks — memory `gsd-scaffold-fictional-api`).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (none) | — | — | All phase behaviors have automated verification. The e2e sign-off prompt is automated via CliRunner `input="approve\n"`. |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (the 7 scaffold files)
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
