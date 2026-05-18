---
phase: T8
slug: input-bar-ergonomics-v0-2
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-17
---

# Phase T8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Per-Task Verification Map filled by gsd-planner against T8-RESEARCH.md `## Validation Architecture`.
> See T8-RESEARCH.md `## Validation Architecture` for the per-behavior verification design (Textual snapshot states, recorder-event assertions, hermetic episodic seeding, stub-provider pattern).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23 (`asyncio_mode = "auto"`) + pytest-textual-snapshot 1.1.0 (Plan T8-01 installs into `[project.optional-dependencies] dev`) + Pillow (Plan T8-05 adds to `dev`) |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]`); snapshot baselines committed under `tests/harness/tui/snapshots/` via `--snapshot-update` (per behavior plan) |
| **Quick run command** | `pytest tests/harness/tui/ -q -x` |
| **Full suite command** | `pytest tests/harness/ -q` |
| **Phase-gate command** | `pytest tests/ -q --ignore=tests/e2e` |
| **Estimated runtime** | seconds — hermetic snapshot + stub provider, no network, no live creds (T7 precedent) |

---

## Sampling Rate

- **After every task commit:** `pytest tests/harness/tui/ -q -x`
- **After every plan wave:** `pytest tests/harness/ -q` (full harness suite)
- **Before `/gsd:verify-work`:** `pytest tests/ -q --ignore=tests/e2e` green
- **Max feedback latency:** target < 30s (hermetic snapshot + stub provider, no network)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T8-01-T1 | 01 | 0 | INPUT-01..05 | T-T8-01, T-T8-SC | Dev-only verified pkg install (audit APPROVED) | Install/import | `python -c "import pytest_textual_snapshot"` | ⬜ Wave 0 creates | ⬜ pending |
| T8-01-T2 | 01 | 0 | INPUT-01..05 | T-T8-02 | Hermetic stub provider, no creds | Unit | `pytest tests/harness/tui/test_slash_palette.py tests/harness/tui/test_full_flow_pilot.py -q -x` | ✅ exists (migrated) | ⬜ pending |
| T8-01-T3 | 01 | 0 | INPUT-01..05 | — | Red-scaffold xfail landing zone | Collect | `pytest tests/harness/tui/test_input_bar_textarea.py tests/harness/tui/test_prefix_dispatch.py tests/harness/tui/test_reverse_search.py tests/harness/tui/test_paste_image.py -q --co` | ⬜ Wave 0 creates | ⬜ pending |
| T8-02-T1 | 02 | 1 | INPUT-01 | T-T8-03, T-T8-04, T-T8-05 | Additive keymap; child TextArea strips ctrl+f/u | Unit (pilot) | `pytest tests/harness/tui/test_input_bar_textarea.py tests/harness/tui/test_keymap_baseline.py tests/harness/tui/test_slash_palette.py -q -x` | ⬜ T8-01-T3 | ⬜ pending |
| T8-02-T2 | 02 | 1 | INPUT-01 | T-T8-03 | Palette hex unchanged; 1-line tcss diff | Snapshot (anchors 1-4) | `pytest tests/harness/tui/test_input_bar_textarea.py -q -x` | ⬜ T8-01-T3 | ⬜ pending |
| T8-03-T1 | 03 | 2 | INPUT-02, INPUT-03 | T-T8-07, T-T8-09 | voss_md human-section append (not write_fence_body); M9-04 recorder zero-change | Unit (round-trip) | `pytest tests/harness/tui/test_prefix_dispatch.py -q -x -k "local_block or notes_helper or emit"` | ⬜ T8-01-T3 | ⬜ pending |
| T8-03-T2 | 03 | 2 | INPUT-02, INPUT-03 | T-T8-06, T-T8-08 | `!cmd` via sandbox.shell_allowed gate ONLY; local blocks never in model history | Unit + Snapshot (5-7) + Recorder (R1/R2) | `pytest tests/harness/tui/test_prefix_dispatch.py -q -x` | ⬜ T8-01-T3 | ⬜ pending |
| T8-04-T1 | 04 | 2 | INPUT-01..05 | T-T8-10, T-T8-12 | Reuse register_turn_task (no new concurrency surface); T1-06 interrupt intact | Unit (pilot) | `pytest tests/harness/tui/test_app_shell.py tests/harness/tui/test_app_interrupt.py tests/harness/tui/test_full_flow_pilot.py -q -x` | ✅ exists (extended) | ⬜ pending |
| T8-04-T2 | 04 | 2 | INPUT-01..05 | T-T8-11 | input() loop + slash + job-reap finally byte-unchanged (additive TUI branch) | Integration (pilot) | `pytest tests/harness/tui/test_full_flow_pilot.py tests/harness/tui/test_cli_integration.py -q -x` | ✅ exists (extended) | ⬜ pending |
| T8-05-T1 | 05 | 3 | INPUT-04, INPUT-05 | T-T8-13, T-T8-SC | Pillow dev-only APPROVED; probe graceful on all 4 documented errors | Unit (pure-logic) | `pytest tests/harness/tui/test_reverse_search.py tests/harness/tui/test_paste_image.py -q -x -k "corpus or probe or vision or build"` | ⬜ T8-01-T3 | ⬜ pending |
| T8-05-T2 | 05 | 3 | INPUT-04 | T-T8-14 | Corpus = current-project live EpisodicMemory only; !cmd/#note/palette excluded | Unit (pilot) + Snapshot (8-9) | `pytest tests/harness/tui/test_reverse_search.py -q -x` | ⬜ T8-01-T3 | ⬜ pending |
| T8-05-T3 | 05 | 3 | INPUT-05 | T-T8-15, T-T8-16 | Notice never in model history; transient; image opaque vision-only | Unit (pilot) + Snapshot (10-11) | `pytest tests/harness/tui/test_paste_image.py -q -x` | ⬜ T8-01-T3 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Snapshot anchor → task coverage (UI-SPEC 11 anchors + R1/R2):** anchors 1-4 → T8-02-T2; anchors 5-7 + R1/R2 → T8-03-T2; anchors 8-9 → T8-05-T2; anchors 10-11 → T8-05-T3. No anchor or recorder assertion unmapped.

**Nyquist continuity:** every behavior task carries `tdd="true"` + a `<behavior>` block and an `<automated>` verify. No 3 consecutive tasks lack an automated check. Snapshot tasks generate their own baseline via `--snapshot-update` (Pitfall 8) — they are NOT MISSING; Wave 0 (T8-01-T3) establishes the collectable xfail scaffold so every later task has a concrete pre-existing target file.

---

## Wave 0 Requirements (Plan T8-01)

- [x] Add `pytest-textual-snapshot>=1.1.0` to `pyproject.toml [project.optional-dependencies] dev` (T8-01-T1)
- [x] Hermetic episodic-history seed fixture (`seeded_history`, INPUT-04 corpus) + stub-provider fixture (T7 precedent) + `mock_recorder_bridge` for R1/R2 — `tests/harness/tui/conftest.py` (T8-01-T2)
- [x] Migrate the two existing tests reading `InputBar.value` (`test_slash_palette.py`, `test_full_flow_pilot.py`) to a `.text`-tolerant accessor — backward-compatible, survives the TextArea swap (Pitfall 3, T8-01-T2)
- [x] Four T8 test modules created as collectable xfail scaffolds + `tests/harness/tui/snapshots/__init__.py` package (T8-01-T3)
- [ ] Baseline snapshot SVGs: generated per behavior plan via `--snapshot-update` for that plan's anchors (Pitfall 8 — NOT all in Wave 0; each plan owns its anchors so baselines track the implementation that produces them)

*Note: Pillow (`dev`) is added by Plan T8-05-T1 (only INPUT-05 needs it) — not a Wave 0 blocker for Waves 1-2.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| True OS-clipboard image paste on real macOS / Linux / Windows | INPUT-05 | Real OS clipboard + terminal can't be driven fully headlessly; PIL.ImageGrab Linux needs wl-paste/xclip | Automated coverage: `_probe_clipboard_image` monkeypatched (Image / list / None / each raising exception), `_model_supports_vision` truth table, no-vision notice + attach indicator snapshots (anchors 10-11). Manual smoke (post-merge, one-time per platform): copy a real screenshot, paste in `voss` TUI, confirm `[image attached · 1 image]` on a vision model and the transient notice on a non-vision model. Not a phase-gate blocker. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (scaffold + fixtures + migrated tests; per-plan snapshot baselines per Pitfall 8)
- [x] No watch-mode flags
- [x] Feedback latency < target (hermetic, no network)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned (filled by gsd-planner; gsd-plan-checker may amend)
