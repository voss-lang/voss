---
phase: V7
slug: engineering-manager-loop-supersedes-o5
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-06
---

# Phase V7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from V7-RESEARCH.md `## Validation Architecture` + `## Security Domain`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (existing) |
| **Config file** | pyproject.toml (root) |
| **Quick run command** | `.venv/bin/python -m pytest tests/harness/em/ -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/harness/em/ tests/harness/test_team_run_cli.py tests/harness/test_team_check_cli.py -q` |
| **Estimated runtime** | ~20 seconds |

> **Use `.venv/bin/python`** — bare `python3` lacks deps (memory `voss-python-interpreter`).
> **DO NOT** run `tests/harness/board/` in the V7 gate — 13 pre-existing RED failures from V6-01 scaffolds (V6-02..05 unexecuted). V7's "existing O5 em tests pass" criterion targets `tests/harness/em/` (79/79 green today).

---

## Sampling Rate

- **After every task commit:** `.venv/bin/python -m pytest tests/harness/em/ -x -q`
- **After every plan wave:** `.venv/bin/python -m pytest tests/harness/em/ tests/harness/test_team_run_cli.py -q`
- **Before `/gsd-verify-work`:** Full suite green
- **Max feedback latency:** ~20 seconds

---

## Per-Task Verification Map

| Req ID | Behavior | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists |
|--------|----------|------------|-----------------|-----------|-------------------|-------------|
| VEM-CLI | `voss team run "<goal>"` exits 0 on stub provider | — | N/A | integration | `.venv/bin/python -m pytest tests/harness/test_team_run_cli.py::TestTeamRunCLI::test_stub_run_exits_zero` | ❌ W0 |
| VEM-CLI | Run produces ≥1 card + RunFinal (pre-spawn board card) | — | N/A | integration | `.venv/bin/python -m pytest tests/harness/test_team_run_cli.py::TestTeamRunCLI::test_produces_card_and_run_final` | ❌ W0 |
| VEM-CLI | No team file → default 7-role roster | — | N/A | integration | `.venv/bin/python -m pytest tests/harness/test_team_run_cli.py::TestTeamRunCLI::test_default_roster_fallback` | ❌ W0 |
| VEM-CLI | Team file present → overrides default | — | N/A | integration | `.venv/bin/python -m pytest tests/harness/test_team_run_cli.py::TestTeamRunCLI::test_team_file_override` | ❌ W0 |
| VEM-PERSIST | `run-final.json` exists after run under root | T-V7-05 (path) | Path derived from `rf.root_id` (never user input); `chmod 0o600` | integration | `.venv/bin/python -m pytest tests/harness/test_team_run_cli.py::TestTeamRunCLI::test_run_final_persisted` | ❌ W0 |
| VEM-PERSIST | `run-final.json` contains the 10 RunFinal fields (`dataclasses.asdict`) | — | N/A | unit | `.venv/bin/python -m pytest tests/harness/test_team_run_cli.py::TestRunFinalPersist::test_fields_serialized` | ❌ W0 |
| VEM-PERSIST | `run-final.json` re-readable without re-running | — | N/A | unit | `.venv/bin/python -m pytest tests/harness/test_team_run_cli.py::TestRunFinalPersist::test_rereadable` | ❌ W0 |
| VEM-SIGNOFF | CLI prints RunFinal summary + prompts approve/reject | T-V7-04 (Repudiation) | Prompt not optional; both paths covered | integration | `.venv/bin/python -m pytest tests/harness/test_team_run_cli.py::TestSignOff::test_prompt_appears` | ❌ W0 |
| VEM-SIGNOFF | Approve recorded as `sign_off` in `run-final.json` | — | N/A | integration | `.venv/bin/python -m pytest tests/harness/test_team_run_cli.py::TestSignOff::test_approve_recorded` | ❌ W0 |
| VEM-SIGNOFF | Reject recorded; working tree unchanged (no revert) | — | Record-only | integration | `.venv/bin/python -m pytest tests/harness/test_team_run_cli.py::TestSignOff::test_reject_recorded_no_revert` | ❌ W0 |
| verify | Cage: dispatch to undeclared role denied (`EMCageViolation`) | T-V7-02 (Spoof/EoP) | `role_id in roster_ids` check | unit (existing) | `.venv/bin/python -m pytest tests/harness/em/test_em_handle_cage.py` | ✅ |
| verify | Cage: no `set_ceiling`/`set_p`/`extend_budget` on handle | T-V7-01 (EoP) | Methods absent (cage by surface area) | unit (existing) | `.venv/bin/python -m pytest tests/harness/em/test_em_handle_cage.py::TestCageInvariant1Introspection` | ✅ |
| verify | kill/rescope lineage + routing_rationale recorded | — | N/A | unit (existing) | `.venv/bin/python -m pytest tests/harness/em/test_em_handle_dispatch.py tests/harness/em/test_em_lineage.py` | ✅ |
| verify | Existing O5 em tests pass | — | N/A | regression | `.venv/bin/python -m pytest tests/harness/em/ -x -q` | ✅ (79/79) |
| bookkeeping | Zero field changes RunRecord/SessionRecord/BudgetScope | — | Frozen-schema invariant | schema-freeze | `.venv/bin/python -m pytest tests/voss/test_team_backcompat_regression.py -k schema` + `git diff` review | ✅ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/harness/test_team_run_cli.py` — new file covering VEM-CLI / VEM-PERSIST / VEM-SIGNOFF (classes `TestTeamRunCLI`, `TestRunFinalPersist`, `TestSignOff`); uses `DeterministicEMStub` + click `CliRunner(input=...)`; monkeypatch `get_model_tiers()` for default-roster construction.

*Cage/lineage/regression rows reuse existing `tests/harness/em/` files — no new scaffolds needed there.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Frozen-schema zero-field-change | bookkeeping | `git diff` field-level assertion | `git diff` on session/recorder/`voss_runtime` budget modules; confirm zero field add/remove/rename on `RunRecord`/`SessionRecord`/`BudgetScope` |
| O5 superseded in ROADMAP/STATE | bookkeeping | Doc bookkeeping | Confirm ROADMAP/STATE mark O5 superseded by V7 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (1 new test file)
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
