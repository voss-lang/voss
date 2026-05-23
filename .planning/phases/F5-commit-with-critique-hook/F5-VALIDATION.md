---
phase: F5
slug: commit-with-critique-hook
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-22
---

# Phase F5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest tests/harness/test_consensus.py -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/harness/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/harness/test_consensus.py -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/harness/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| F5-01-01 | 01 | 1 | D-01..D-04 | T-F5-01 (YAML deser) | `yaml.safe_load` only | unit | `.venv/bin/python -m pytest tests/harness/test_consensus.py::test_constraints_loaded -q` | ❌ W0 | ⬜ pending |
| F5-01-02 | 01 | 1 | D-13,D-14 | — | N/A | unit | `.venv/bin/python -m pytest tests/harness/test_consensus.py::test_single_shot_call -q` | ❌ W0 | ⬜ pending |
| F5-01-03 | 01 | 1 | D-09 | — | N/A | unit | `.venv/bin/python -m pytest tests/harness/test_consensus.py::test_block_mode_exits_1 -q` | ❌ W0 | ⬜ pending |
| F5-01-04 | 01 | 1 | D-10..D-12 | — | N/A | unit | `.venv/bin/python -m pytest tests/harness/test_consensus.py::test_output_format -q` | ❌ W0 | ⬜ pending |
| F5-01-05 | 01 | 1 | D-16 | — | Fail-open | unit | `.venv/bin/python -m pytest tests/harness/test_consensus.py::test_fail_open -q` | ❌ W0 | ⬜ pending |
| F5-02-01 | 02 | 2 | D-05..D-07 | T-F5-03 (hook overwrite) | Refuse if exists | unit | `.venv/bin/python -m pytest tests/harness/test_consensus.py::test_hooks_install -q` | ❌ W0 | ⬜ pending |
| F5-02-02 | 02 | 2 | D-06,D-08 | — | N/A | unit | `.venv/bin/python -m pytest tests/harness/test_consensus.py::test_shim_content -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/harness/test_consensus.py` — stubs for D-01..D-16 requirements
- [ ] `voss/harness/consensus.py` — new module (at least importable stub)

*Existing infrastructure (pytest config, .venv, Click test runner) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `voss consensus --staged` integration | D-08 | Requires live git repo with staged changes + LLM provider | Stage a change, run `voss consensus --staged`, verify output |
| Pre-commit hook invocation | D-05/D-06 | Requires `voss hooks install` + actual `git commit` | Install hook, stage a change, commit, verify critique runs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
