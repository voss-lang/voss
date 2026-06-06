---
phase: V5
slug: board-state-machine-supersedes-o3
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-06
---

# Phase V5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from V5-RESEARCH.md `## Validation Architecture` + `## Security Domain`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (with pytest-asyncio for async `Board` methods) |
| **Config file** | pyproject.toml (root) |
| **Quick run command** | `.venv/bin/python -m pytest tests/harness/board/ -q --tb=short` |
| **Full suite command** | `.venv/bin/python -m pytest tests/harness/board/ -v` |
| **Estimated runtime** | ~15 seconds (23 files, 92 tests + new) |

> Use `.venv/bin/python` — bare `python3` lacks deps (memory `voss-python-interpreter`).

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/harness/board/ -q --tb=short`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/harness/board/ -v`
- **Before `/gsd-verify-work`:** Full suite green (91+ existing + new tests pass; pre-existing `test_exit_reasons_is_sorted_superset_of_pre_o3` failure fixed)
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Req ID | Behavior | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists |
|--------|----------|------------|-----------------|-----------|-------------------|-------------|
| VBOARD-03 | `Card` carries `idea`/`role`/`acceptance_criteria`/`verification_requirement` with `""` defaults | — | N/A | unit | `.venv/bin/python -m pytest tests/harness/board/test_card_fields_v5.py -x` | ❌ W0 |
| VBOARD-03 | Existing `Card` construction paths still work (back-compat) | — | N/A | unit | `.venv/bin/python -m pytest tests/harness/board/test_card_node_wiring.py tests/harness/board/test_stub_full_lifecycle.py -x` | ✅ |
| VBOARD-03 | `status` derives from column; `budget` derives from envelope | — | N/A | unit | `.venv/bin/python -m pytest tests/harness/board/test_card_fields_v5.py::TestCardStatus -x` | ❌ W0 |
| VBOARD-07 | `move(card,"Done")` with `reviewer=None` raises `BoardGateError("no-reviewer")` | T-V5-01 (EoP) | Worker/EM cannot self-transition to Done without injected reviewer | unit | `.venv/bin/python -m pytest tests/harness/board/test_self_done_guard.py -x` | ❌ W0 |
| VBOARD-07 | Caller cannot pre-inject `GateContext.verdict` (constructed fresh in `Board.move`) | T-V5-02 (Spoofing) | Independence structural — no self-authored verdict path | unit | `.venv/bin/python -m pytest tests/harness/board/test_self_done_guard.py::TestSelfDoneGuard::test_no_verdict_injection -x` | ❌ W0 |
| VBOARD-07 | Valid reviewer verdict (other predicates pass) permits Done | — | N/A | unit | `.venv/bin/python -m pytest tests/harness/board/test_self_done_guard.py::TestSelfDoneGuard::test_valid_reviewer_allows_done -x` | ❌ W0 |
| VBOARD-10 | `voss board` (no arg) renders latest root + exits 0 | — | N/A | smoke | `.venv/bin/python -m pytest tests/harness/board/test_board_cli.py::TestBoardCLI::test_default_latest -x` | ❌ W0 |
| VBOARD-10 | `voss board <root_id>` renders named root + exits 0 | — | N/A | smoke | `.venv/bin/python -m pytest tests/harness/board/test_board_cli.py::TestBoardCLI::test_named_root -x` | ❌ W0 |
| VBOARD-10 | Unknown root → non-zero exit + stderr | — | N/A | smoke | `.venv/bin/python -m pytest tests/harness/board/test_board_cli.py::TestBoardCLI::test_unknown_root_exit_code -x` | ❌ W0 |
| VBOARD-10 | Malicious `root_id` (`../..`) cannot escape `.voss/sessions/` | T-V5-03 (Tampering) | Path resolved must stay under `.voss/sessions/`; else error | unit | `.venv/bin/python -m pytest tests/harness/board/test_board_cli.py::TestBoardCLI::test_path_traversal_rejected -x` | ❌ W0 |
| verify | Shipped board surface (BOARD-01/02/04/05/06/08/09) regresses green | — | N/A | regression | `.venv/bin/python -m pytest tests/harness/board/ -q --tb=short` | ✅ (91 pass) |
| verify | Stale `test_exit_reasons_is_sorted_superset_of_pre_o3` fixed (`issubset`) | — | N/A | unit | `.venv/bin/python -m pytest tests/harness/board/test_session_tree_additive.py -x` | ✅ (1-line fix) |
| bookkeeping | `git diff` shows zero field changes on `RunRecord`/`SessionRecord`/`BudgetScope`/`SessionTreeNode` | — | Frozen-schema invariant | manual/grep | `git diff --stat` review + targeted grep | N/A |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/harness/board/test_card_fields_v5.py` — VBOARD-03 (Card field completeness + status/budget derivation)
- [ ] `tests/harness/board/test_self_done_guard.py` — VBOARD-07 (independence guard + no-injection)
- [ ] `tests/harness/board/test_board_cli.py` — VBOARD-10 (CLI exit codes + column rendering via click `CliRunner` + path-traversal rejection)

*Shared fixtures: reuse existing `tests/harness/board/` conftest patterns (stub reviewer, persisted-node tmp dirs).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Frozen-schema zero-field-change | bookkeeping | `git diff` field-level assertion not expressible as a unit test | Run `git diff` on `session.py`/`recorder`/`voss_runtime` budget modules; confirm no field add/remove/rename on `RunRecord`/`SessionRecord`/`BudgetScope`/`SessionTreeNode` |
| O3 superseded in ROADMAP/STATE | bookkeeping | Doc bookkeeping | Confirm ROADMAP/STATE mark O3 superseded by V5 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (3 new test files)
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
