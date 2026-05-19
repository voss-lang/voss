---
phase: M15
slug: skill-plugin-marketplace-caps-01f
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-19
---

# Phase M15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: M15-RESEARCH.md `## Validation Architecture` (HIGH confidence).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (`pyproject.toml` `[tool.pytest.ini_options]`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/harness/skill/ -x -q` |
| **Full suite command** | `pytest tests/harness/skill/ tests/e2e/test_skill_lifecycle.py -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/harness/skill/ -x -q`
- **After every plan wave:** Run `pytest tests/harness/skill/ tests/e2e/test_skill_lifecycle.py -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Requirement → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists |
|--------|----------|-----------|-------------------|-------------|
| SKILL-01 (local) | `voss skill add ./bundle` installs; `voss skill list` shows it | integration | `pytest tests/harness/skill/test_install.py::test_add_local -x` | ❌ W0 |
| SKILL-01 (github) | `voss skill add owner/repo` resolves + installs | integration | `pytest tests/harness/skill/test_install.py::test_add_github -x -m "not live"` | ❌ W0 |
| SKILL-02 (register) | After add, `/skill <id>` resolves + runs | integration | `pytest tests/harness/skill/test_registry.py::test_voss_skill_dispatch -x` | ❌ W0 |
| SKILL-02 (pre-add) | Before add, id does NOT resolve | unit | `pytest tests/harness/skill/test_registry.py::test_unknown_skill_not_found -x` | ❌ W0 |
| SKILL-03 (tamper) | Tampered manifest → refused, non-zero, nothing installed | unit | `pytest tests/harness/skill/test_trust.py::test_tampered_manifest_refused -x` | ❌ W0 |
| SKILL-03 (unknown key) | Unknown key → refused until `voss skill trust` | unit | `pytest tests/harness/skill/test_trust.py::test_unknown_key_refused -x` | ❌ W0 |
| SKILL-03 (trust→add) | After trust, same install succeeds | unit | `pytest tests/harness/skill/test_trust.py::test_trust_then_install_succeeds -x` | ❌ W0 |
| SKILL-04 (deny) | Tool outside declared scopes → gate blocks | unit | `pytest tests/harness/skill/test_scope.py::test_out_of_scope_blocked -x` | ❌ W0 |
| SKILL-04 (allow) | Tool inside declared scopes → permitted | unit | `pytest tests/harness/skill/test_scope.py::test_in_scope_allowed -x` | ❌ W0 |
| SKILL-05 (remove) | After remove, list omits + `/skill` unresolved | integration | `pytest tests/harness/skill/test_lifecycle.py::test_remove -x` | ❌ W0 |
| SKILL-05 (update tamper) | Update vs tampered upstream → fails, prior intact | integration | `pytest tests/harness/skill/test_lifecycle.py::test_update_tamper_leaves_prior_intact -x` | ❌ W0 |
| SKILL-06 (e2e) | Fixture bundle passes add→list→run→remove cycle | e2e | `pytest tests/e2e/test_skill_lifecycle.py::test_fixture_bundle_e2e -x` | ❌ W0 |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _planner-fills_ | — | — | SKILL-01..06 | — | — | — | (map per Requirement→Test Map above) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · Planner/nyquist-auditor binds task IDs to the Requirement→Test Map rows above.*

---

## Wave 0 Requirements

- [ ] `tests/harness/skill/__init__.py` — package marker
- [ ] `tests/harness/skill/test_trust.py` — SKILL-03 (3 tests)
- [ ] `tests/harness/skill/test_scope.py` — SKILL-04 (2 tests)
- [ ] `tests/harness/skill/test_install.py` — SKILL-01 (2 tests)
- [ ] `tests/harness/skill/test_registry.py` — SKILL-02 (2 tests)
- [ ] `tests/harness/skill/test_lifecycle.py` — SKILL-05 (2 tests)
- [ ] `tests/e2e/test_skill_lifecycle.py` — SKILL-06 (1 test)
- [ ] `examples/skills/<fixture-bundle>/` — signed fixture bundle + committed test keypair
- [ ] Framework install: none needed (pytest already in dev deps)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GitHub-shorthand live network fetch | SKILL-01 | CI runs `-m "not live"`; real GitHub fetch needs network | `pytest tests/harness/skill/test_install.py::test_add_github -m live` against a real repo |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
