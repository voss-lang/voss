---
phase: M15
slug: skill-plugin-marketplace-caps-01f
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-19
completed: 2026-05-20
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

| Req ID | Behavior | Test Type | Automated Command | Status |
|--------|----------|-----------|-------------------|--------|
| SKILL-01 (local) | `voss skill add ./bundle` installs; `voss skill list` shows it | integration | `pytest tests/harness/skill/test_install.py::test_add_local -x` | ✅ green |
| SKILL-01 (github) | `voss skill add owner/repo` resolves + installs | integration | `pytest tests/harness/skill/test_install.py::test_add_github -x -m "not live"` | ✅ green |
| SKILL-02 (register) | After add, `/skill <id>` resolves + runs | integration | `pytest tests/harness/skill/test_registry.py::test_voss_skill_dispatch -x` | ✅ green |
| SKILL-02 (pre-add) | Before add, id does NOT resolve | unit | `pytest tests/harness/skill/test_registry.py::test_unknown_skill_not_found -x` | ✅ green |
| SKILL-03 (tamper) | Tampered manifest → refused, non-zero, nothing installed | unit | `pytest tests/harness/skill/test_trust.py::test_tampered_manifest_refused -x` | ✅ green |
| SKILL-03 (unknown key) | Unknown key → refused until `voss skill trust` | unit | `pytest tests/harness/skill/test_trust.py::test_unknown_key_refused -x` | ✅ green |
| SKILL-03 (trust→add) | After trust, same install succeeds | unit | `pytest tests/harness/skill/test_trust.py::test_trust_then_install_succeeds -x` | ✅ green |
| SKILL-04 (deny) | Tool outside declared scopes → gate blocks | unit | `pytest tests/harness/skill/test_scope.py::test_out_of_scope_blocked -x` | ✅ green |
| SKILL-04 (allow) | Tool inside declared scopes → permitted | unit | `pytest tests/harness/skill/test_scope.py::test_in_scope_allowed -x` | ✅ green |
| SKILL-05 (remove) | After remove, list omits + `/skill` unresolved | integration | `pytest tests/harness/skill/test_lifecycle.py::test_remove -x` | ✅ green |
| SKILL-05 (update tamper) | Update vs tampered upstream → fails, prior intact | integration | `pytest tests/harness/skill/test_lifecycle.py::test_update_tamper_leaves_prior_intact -x` | ✅ green |
| SKILL-06 (e2e) | Fixture bundle passes trust→add→list→run→update→remove cycle | e2e | `pytest tests/e2e/test_skill_lifecycle.py::test_fixture_bundle_e2e -x` | ✅ green |
| SKILL-06 (sig guard) | Committed signature verifies against committed key | unit | `pytest tests/e2e/test_skill_lifecycle.py::test_committed_signature_verifies -x` | ✅ green |

---

## Wave 0 Requirements

- [x] `tests/harness/skill/__init__.py` — package marker
- [x] `tests/harness/skill/test_trust.py` — SKILL-03 (3 tests)
- [x] `tests/harness/skill/test_scope.py` — SKILL-04 (2 tests)
- [x] `tests/harness/skill/test_install.py` — SKILL-01 (5 tests)
- [x] `tests/harness/skill/test_registry.py` — SKILL-02 (3 tests)
- [x] `tests/harness/skill/test_lifecycle.py` — SKILL-05 (2 tests)
- [x] `tests/e2e/test_skill_lifecycle.py` — SKILL-06 (2 tests)
- [x] `examples/skills/voss-git-summary/` — signed fixture bundle + committed test keypair
- [x] Framework install: none needed (pytest already in dev deps)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GitHub-shorthand live network fetch | SKILL-01 | CI runs `-m "not live"`; real GitHub fetch needs network | `pytest tests/harness/skill/test_install.py::test_add_github -m live` against a real repo |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete — 2026-05-20. All 13 automated tests GREEN. SKILL-01..06 satisfied.
