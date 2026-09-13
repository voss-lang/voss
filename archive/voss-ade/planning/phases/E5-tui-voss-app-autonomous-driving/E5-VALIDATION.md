---
phase: E5
slug: tui-voss-app-autonomous-driving
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-10
---

# Phase E5 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio + Textual Pilot; Vitest/WebdriverIO; GitHub Actions manual workflow |
| **Config file** | `pyproject.toml`, future `apps/voss-app/wdio.conf.mjs`, future `.github/workflows/voss-app-e2e.yml` |
| **Quick run command** | `python3 -m pytest tests/harness/tui/test_e5_journeys.py -q -m "not live"` |
| **Full suite command** | `python3 -m pytest tests/harness/tui/test_e5_journeys.py tests/harness/tui/test_e5_live_journeys.py -q && pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && pnpm --dir apps/voss-app run test:e2e:tauri -- --spec e2e-tauri/command-palette.wdio.mjs,e2e-tauri/project-open.wdio.mjs,e2e-tauri/themes.wdio.mjs` |
| **Estimated runtime** | ~120s local excluding live model calls; manual Linux workflow separately bounded by GitHub Actions timeout |

---

## Sampling Rate

- **After every task commit:** Run the relevant quick command for the touched surface.
- **After every plan wave:** Run the full local suite for touched surfaces.
- **Before `$gsd-verify-work`:** TUI hermetic tests, app tests/build, TUI live proof, and manual Linux workflow evidence must be complete.
- **Max feedback latency:** 10 minutes local; CI workflow evidence may take longer but must be linked in the phase summary.

---

## Per-Task Verification Map

Requirement IDs are not yet minted because `E5-SPEC.md` is absent. Until that file exists, the map keys requirements by `E5-CONTEXT.md` decisions.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| E5-01-01 | 01 | 1 | D-01, D-03 | T-E5-01 | Stub TUI journeys run in normal suite without provider credentials | unit/integration | `python3 -m pytest tests/harness/tui/test_e5_journeys.py -q -m "not live"` | no | pending |
| E5-02-01 | 02 | 2 | D-02, D-07, D-09 | T-E5-02 | Live journeys skip without credentials and never run in normal suite | live/integration | `python3 -m pytest tests/harness/tui/test_e5_live_journeys.py -q -m live` | no | pending |
| E5-03-01 | 03 | 1 | D-05, D-06 | T-E5-03 | Selected preserved app contracts assert real DOM/protocol outcomes through Tauri-driver/WebDriver and use fake-turn seam | e2e | `pnpm --dir apps/voss-app run test:e2e:tauri -- --spec e2e-tauri/command-palette.wdio.mjs,e2e-tauri/project-open.wdio.mjs,e2e-tauri/themes.wdio.mjs` | no | pending |
| E5-04-01 | 04 | 4 | D-04, D-07, D-08 | T-E5-04 | Manual workflow is dispatch-only, read-only permissions, no provider secrets | CI/manual | `gh workflow run voss-app-e2e.yml` | no | pending |

*Status: pending, green, red, flaky*

---

## Wave 0 Requirements

- [ ] `E5-SPEC.md` or equivalent plan-frontmatter mapping mints/records EVUI requirement IDs before execution.
- [ ] `tests/harness/tui/test_e5_journeys.py` exists with hermetic stub twins.
- [ ] `tests/harness/tui/test_e5_live_journeys.py` exists with `@pytest.mark.live` and credential-gated skip behavior.
- [ ] `.github/workflows/voss-app-e2e.yml` exists as a manual `workflow_dispatch` workflow before desktop closeout.
- [ ] At least three selected app contracts are identified before any Tauri-driver/WebDriver port edits.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TUI live proof | D-02, D-07 | Uses subscription-backed provider credentials and may vary by local auth state | Run `python3 -m pytest tests/harness/tui/test_e5_live_journeys.py -q -m live`; paste command output into phase summary |
| voss-app Tauri e2e proof | D-04, D-07, D-08 | macOS cannot run target WebDriver; proof is Linux manual workflow evidence | Dispatch `voss-app-e2e.yml`; link run URL and artifacts in phase summary |
| Human checkpoint | D-07 | Operator must judge whether the two artifacts satisfy the internal proof posture | Review live pytest output and GitHub Actions run link before marking E5 complete |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies.
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify.
- [ ] Wave 0 covers all missing references.
- [ ] No watch-mode flags.
- [ ] Feedback latency < 10 minutes for local gates.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** pending
