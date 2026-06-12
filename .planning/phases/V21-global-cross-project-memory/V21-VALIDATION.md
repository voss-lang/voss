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

Plan/task IDs bound to plans. Decision→test mapping locked from RESEARCH.md.
Wave structure: V21-01 (Wave 0 scaffold) → V21-02 (Wave 1 store/config) → V21-03 + V21-04 (Wave 2, parallel).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| V21-01 T1 | V21-01 | 0 | VGMEM-* infra (tmp_voss_global fixture) | T-V21-01-01 | VOSS_HOME monkeypatched under tmp_path; real ~/.voss untouched | fixture | `pytest tests/harness/conftest.py --collect-only -q` | ❌ W0 | ⬜ pending |
| V21-01 T2 | V21-01 | 0 | VGMEM-* (all, 17 RED stubs) | T-V21-01-02 | stubs assert Hit fields only; no secrets in fixtures | unit stubs (RED) | `pytest tests/harness/test_memory_global.py --collect-only -q` | ❌ W0 | ⬜ pending |
| V21-02 T1 | V21-02 | 1 | VGMEM-01 / D-04 root_override / VOSS_HOME / layout mirror | T-V21-02-01 (VOSS_HOME path traversal) | `Path(voss_home).resolve()` normalizes `..` before `/memory` | unit | `pytest tests/harness/test_memory_global.py -x -k "root_override or voss_home_env or global_layout_mirror"` | ❌ W0 | ⬜ pending |
| V21-02 T2 | V21-02 | 1 | VGMEM-07 / D-07 off-switch | T-V21-02-03 (init when operator disabled) | `make_global_store()` early-returns None when disabled — no chroma open | unit + config | `pytest tests/harness/test_memory_global.py -x -k "global_off_switch_no_init"` | ❌ W0 | ⬜ pending |
| V21-03 T1 | V21-03 | 2 | VGMEM-03 / D-01 promote copy + dedup, D-02 source restriction | T-V21-03-01 (locator prefix validation), T-V21-03-02 (file perms), T-V21-03-04 (dedup collision) | reject turn/ledger before store work; chmod 0o600; dedup via promoted_from where-filter; chroma touches None-guarded | unit + CLI subprocess | `pytest tests/harness/test_memory_global.py -x -k "promote"` | ❌ W0 | ⬜ pending |
| V21-03 T2 | V21-03 | 2 | VGMEM-04 / D-03 forget --global, VGMEM-05 / D-05 vacuum --global, D-13 concurrency | T-V21-03-03 (concurrent promote lost-write) | dual-scope forget (project default); vacuum on global root; promote blocking LOCK_EX serializes concurrent writers | unit + integration (subprocess) | `pytest tests/harness/test_memory_global.py -x -k "forget or vacuum_global or concurrent_promote"` | ❌ W0 | ⬜ pending |
| V21-04 T1 | V21-04 | 2 | VGMEM-06 / D-06 equal RRF, D-07 [global] label, VGMEM-02 / D-08 write guard | T-V21-04-02 (agent write path → global), T-V21-04-03 (locator collision), T-V21-04-04 (global recall crash) | global_store read-only in attach_memory_tools; global: namespacing before merge; try/except falls back to project-only | unit | `pytest tests/harness/test_memory_global.py -x -k "recall_fusion or global_label or agent_cannot_write"` | ❌ W0 | ⬜ pending |
| V21-04 T2 | V21-04 | 2 | VGMEM-02 / D-08 wiring (3 attach sites), D-07 off-switch passthrough | T-V21-04-02 (write path → global) | global_store=None tolerated; read-only ref; do_cmd dispatch pass-through asserted at runtime | unit | `pytest tests/harness/test_memory_global.py -x -k "off_switch_no_init or do_cmd_wires_global_store"` | ❌ W0 | ⬜ pending |
| V21-04 T3 | V21-04 | 2 | VGMEM-08 / D-06 voss recall global corpus | T-V21-04-01 (recall/--json info disclosure) | global hits expose only Hit fields; no new field carries env/secret; preserves V19 [code]/[memory] schema | unit + CLI | `pytest tests/harness/test_memory_global.py::test_voss_recall_global_corpus -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> **Phase-completion gate:** V21-04 T3 is the final task. After the FULL V21 suite is green it flips this file's frontmatter to `nyquist_compliant: true` + `wave_0_complete: true` (+ `status: complete`).

---

## Wave 0 Requirements

- [ ] `tests/harness/test_memory_global.py` — all 17 VGMEM-* test stubs (new file; includes `test_do_cmd_wires_global_store` dispatch pass-through)
- [ ] `tests/harness/conftest.py` amendment — `tmp_voss_global` fixture (`VOSS_HOME` monkeypatch + 7-subdir layout mirror, mirroring `tmp_voss_repo`)

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
- [ ] `nyquist_compliant: true` set in frontmatter (flipped by V21-04 T3 on full-suite green)

**Approval:** pending
</content>
