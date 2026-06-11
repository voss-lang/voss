---
phase: V21
slug: global-cross-project-memory
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase V21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `V21-RESEARCH.md` § Validation Architecture (full decision→test pre-map lives there).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `pyproject.toml [tool.pytest.ini_options]` |
| **Quick run command** | `.venv/bin/python -m pytest tests/harness/test_memory_global.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/harness/ tests/memory/ -q` |
| **Estimated runtime** | quick ~10s; harness+memory suites ~1-2min |

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** `.venv/bin/python -m pytest tests/harness/ tests/memory/ -q`
- **Before `/gsd-verify-work`:** Full suite green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Plan/task IDs filled by planner. Decision→test mapping locked from RESEARCH.md:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | VGMEM-* (all) | — | — | unit stubs (RED) | `tests/harness/test_memory_global.py` scaffold | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-04 root_override / VOSS_HOME / layout mirror | T: VOSS_HOME path traversal | `Path(voss_home).resolve()` + is-dir validation | unit | `pytest tests/harness/test_memory_global.py::test_root_override -x` (+ test_voss_home_env, test_global_layout_mirror) | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-01 promote copy + dedup | T: malicious note content | text-only storage, no exec path | unit | `pytest tests/harness/test_memory_global.py::test_promote_copies_with_provenance -x` (+ test_promote_dedup_on_repromote) | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-02 source restriction | I: validation of locator prefix | promote rejects turn/ledger, exit 1 | unit + CLI | `pytest tests/harness/test_memory_global.py::test_promote_rejects_turn_ledger -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-03 forget --global | — | tombstone scoped to global only | unit | `pytest tests/harness/test_memory_global.py::test_forget_global_tombstones_global -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-05 vacuum --global | — | N/A | unit | `pytest tests/harness/test_memory_global.py::test_vacuum_global -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-06 equal RRF fusion | — | N/A | unit | `pytest tests/harness/test_memory_global.py::test_recall_fusion_rrf -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-07 [global] label + off-switch | — | off-switch skips init entirely | unit + config | `pytest tests/harness/test_memory_global.py::test_global_label_in_recall -x` (+ test_global_off_switch_no_init) | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-08 write guard | E: agent writes to global | no agent tool path reaches global store | unit | `pytest tests/harness/test_memory_global.py::test_agent_cannot_write_global -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-13 concurrency | — | portalocker blocks 2nd process | integration (subprocess) | `pytest tests/harness/test_memory_global.py::test_concurrent_promote_lock -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/harness/test_memory_global.py` — all VGMEM-* test stubs (new file)
- [ ] `tests/harness/conftest.py` amendment — `global_root` fixture (`VOSS_HOME` monkeypatch) + `tmp_voss_global` fixture mirroring `tmp_voss_repo`

**Wave-0 anti-pattern guard (project memory):** stubs MUST target the real planned API (import paths, signatures from plans); never `xfail(strict=False)`; verify imports resolve against planned module paths.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Two live voss sessions in different repos sharing global store | D-13 | full end-to-end across real sessions | open two repos, promote from one, `voss recall` in the other, confirm `[global]` hit |
| File perms on shared machine | V4 access control | environment-specific | `ls -la ~/.voss/memory/notes/` → files 0600 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
