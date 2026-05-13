---
phase: M6
slug: npm-wrapper
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-13
---

# Phase M6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Sourced from M6-RESEARCH.md `## Validation Architecture` (line 956).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (existing) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest -q -m "not slow and not live"` |
| **Full suite command** | `pytest -q -m "not live"` (includes slow) |
| **Estimated runtime** | ~30s quick / multi-minute full (slow packaging tests dominate) |

---

## Sampling Rate

- **After every task commit:** Run `pytest -q -m "not slow and not live"` (fast suite, <30s)
- **After every plan wave:** Run `pytest -q -m "not live"` (includes slow packaging tests)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Phase gate:** Full slow suite green before tagging v0.1.0
- **Max feedback latency:** ~30 seconds for the quick suite

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| M6-01-00 | 01 | 1 | NPM-01 | T-M6-01-03 | `@voss` org owned + 2FA recommended | Manual (human checkpoint) | N/A | N/A | ⬜ pending |
| M6-01-01 | 01 | 1 | NPM-01 | T-M6-01-04 | No stale cargo-dist workflow on tag push | Shell assertions | `test ! -f .github/workflows/release.yml && grep -E 'workflow_dispatch' .github/workflows/rust.yml` | ✅ | ⬜ pending |
| M6-01-02 | 01 | 1 | NPM-01 | — | npm/ scaffold parses as valid JSON | Inline node parse | `node -e "require('./npm/package.json')"` (per task verify) | ✅ | ⬜ pending |
| M6-01-03 | 01 | 1 | NPM-01 | T-M6-01-02 | Same-day name availability re-verified | Shell loop `npm view` | per-task verify (`E404` for all 6 names) | ✅ | ⬜ pending |
| M6-01-04 | 01 | 1 | NPM-01 | T-M6-01-01, T-M6-01-05 | 6 placeholder names claimed at 0.0.0; no token leaks | Shell loop `npm view` | per-task verify (all 6 names report `0.0.0`) | ✅ | ⬜ pending |
| M6-02-* | 02 | 2 | NPM-03 | — | Node shim forwards argv/stdio/exit code/signals | Slow integration | `pytest -m slow tests/packaging/test_npm_install.py::test_shim_forwarding` | ❌ Wave 0 (M6-05 Task 1) | ⬜ pending |
| M6-03-* | 03 | 3 | NPM-02 | — | Platform packages vendor PBS + voss wheel for all 5 platforms | Slow integration | `pytest -m slow tests/packaging/test_npm_install.py::test_platform_package_builds` | ❌ Wave 0 (M6-05 Task 1) | ⬜ pending |
| M6-04-* | 04 | 4 | NPM-01, NPM-02 | T-M6-01-04 | Tag-triggered release workflow publishes 6 packages at the bumped version | Manual (npm publish is a release gate, not a test) | N/A | N/A | ⬜ pending |
| M6-05-01 | 05 | 4 | NPM-04 | T-M6-05-04 | Smoke test module collects 3 tests with correct helpers + markers | AST + pytest collect-only | per-task verify (collects 3 tests, helper set present) | ✅ | ⬜ pending |
| M6-05-02 | 05 | 4 | NPM-04 | T-M6-05-01, T-M6-05-04 | Fresh Node project install + `voss --help/doctor/check/compile` exit cleanly | Slow smoke | `pytest -m slow tests/packaging/test_npm_install.py` (gated on `^[0-9]+ passed` AND no `failed`) | ❌ Wave 0 (M6-05 Task 1) | ⬜ pending |
| M6-05-03 | 05 | 4 | NPM-05 | T-M6-05-02 | README primary install is `npm i -g @voss/cli`; pinned by tests | Fast content assertion | `pytest tests/packaging/test_readme.py` (5 existing + 2 new = 7 passed) | ✅ (extend) | ⬜ pending |
| M6-05-04 | 05 | 4 | NPM-01 (release gate) | T-M6-01-05 | User authorizes the production v0.1.0 publish | Manual (human checkpoint) | N/A | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/packaging/test_npm_install.py` — covers NPM-02, NPM-03, NPM-04 (authored by M6-05 Task 1; tests are stubbed-then-implemented in that task per the plan's specification, then run in M6-05 Task 2)
- [ ] `tests/packaging/test_readme.py` — needs two additional assertions for `npm i -g @voss/cli` presence and npm-before-pip ordering (NPM-05; appended by M6-05 Task 3 to the existing 5-assertion file)
- [ ] Platform build infrastructure must exist before the slow tests can run (M6-02 + M6-03 are prerequisites for the NPM-02/03/04 tests)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `@voss` npm org creation + Automation token issuance | NPM-01 | Requires browser login at npmjs.com; npm CLI cannot create orgs | M6-01 Task 0 checkpoint: create org `voss`, generate Automation token, add as `NPM_TOKEN` GitHub Actions secret |
| `npm publish --access public` for 6 placeholder packages | NPM-01 | Network publish to npm registry; release-class action, not a unit test | M6-01 Task 4 (auto, executes once human prerequisites in Task 0 land) |
| Tag-triggered release workflow for v0.1.0 across 5 platform runners | NPM-01, NPM-02 | GitHub Actions release gate; verified via `npm view @voss/cli@0.1.0` after the workflow lands | M6-05 Task 4 checkpoint: human authorizes `git tag v0.1.0 && git push origin v0.1.0`, then verifies the registry state |
| Clean-machine `npm i -g @voss/cli && voss --help && voss doctor` | NPM-04 | Cross-machine smoke — the in-CI smoke runs in tmp_path, but the user verifies a real end-user install path on their own hardware | M6-05 Task 4 checkpoint step 8 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (with checkpoint tasks marked Manual)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (the only consecutive Manual tasks are M6-01 Task 0 + M6-05 Task 4, which are bookends, not adjacent)
- [ ] Wave 0 covers all MISSING references (`tests/packaging/test_npm_install.py` is authored by M6-05 Task 1 itself — it is both the Wave 0 scaffold and the implementation in a single TDD-style task)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s for the quick suite
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
