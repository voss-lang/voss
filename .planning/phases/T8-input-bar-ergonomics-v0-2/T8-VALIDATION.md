---
phase: T8
slug: input-bar-ergonomics-v0-2
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-17
---

# Phase T8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Per-Task Verification Map is filled by gsd-planner / gsd-plan-checker once plans exist.
> See T8-RESEARCH.md `## Validation Architecture` for the per-behavior verification design (Textual snapshot states, recorder-event assertions, hermetic episodic seeding, stub-provider pattern).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (pytest-asyncio already configured) + pytest-textual-snapshot 1.1.0 (Wave 0 installs — not yet in pyproject `[project.optional-dependencies.dev]`) |
| **Config file** | pyproject.toml (pytest config present); snapshot baselines via `--snapshot-update` (Wave 0) |
| **Quick run command** | `pytest tests/ -k input_bar -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~TBD by planner (snapshot suite is fast; stub-provider, no live creds) |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** TBD by planner (target: seconds — hermetic snapshot + stub provider, no network)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {filled by planner — one row per task; INPUT-01..05 mapped to snapshot/recorder-event assertions} | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Add `pytest-textual-snapshot` to `pyproject.toml` `[project.optional-dependencies.dev]`
- [ ] Establish baseline snapshots (`--snapshot-update`) before behavior implementation
- [ ] Hermetic episodic-history seed fixture (for INPUT-04 Ctrl-R corpus) + stub-provider fixture (T7 precedent) for `shell.local` / `memory.note` recorder-event assertions
- [ ] `tests/` input-bar test module/conftest (no existing input-bar tests)

*Filled/confirmed by planner against T8-RESEARCH.md Validation Architecture.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OS-clipboard image paste on real Linux/macOS/Windows | INPUT-05 | Real OS clipboard + terminal can't be fully driven headlessly; PIL.ImageGrab Linux needs wl-paste/xclip | Planner specifies: snapshot-test the no-vision notice + attachment indicator with a stubbed clipboard reader; manual smoke for true OS clipboard image on each platform |

*Planner may move rows here/automated as the Validation Architecture dictates.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < target
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
